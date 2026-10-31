# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import hashlib
import json
from datetime import date

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Case
from frappe.query_builder.functions import CombineDatetime, Max, Min, Sum
from frappe.utils import (
	cint,
	date_diff,
	flt,
	get_datetime,
	get_link_to_form,
	getdate,
	now,
	nowdate,
	time_diff_in_hours,
)
from pypika import functions as fn

from erpnext.manufacturing.doctype.bom.bom import (
	get_bom_item_rate,
	get_bom_items_as_dict,
	validate_bom_no,
	validate_child_table_identity,
	validate_quantity_input,
)
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_mins_between_operations,
)
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.batch.batch import make_batch
from erpnext.stock.doctype.item.item import get_item_defaults, validate_end_of_life
from erpnext.stock.doctype.serial_no.serial_no import get_available_serial_nos, get_serial_nos
from erpnext.stock.stock_balance import get_planned_qty, update_bin_qty
from erpnext.stock.utils import get_bin, get_latest_stock_qty, validate_warehouse_company
from erpnext.utilities.transaction_base import validate_uom_is_integer


class OverProductionError(frappe.ValidationError):
	pass


class CapacityError(frappe.ValidationError):
	pass


class StockOverProductionError(frappe.ValidationError):
	pass


class OperationTooLongError(frappe.ValidationError):
	pass


class ItemHasVariantError(frappe.ValidationError):
	pass


class SerialNoQtyError(frappe.ValidationError):
	pass


PRODUCTION_APPROVAL_WORKFLOW = "生产工单两级审批"


def _check_production_approval_scope(doc, *, team_required):
	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	permissions = get_user_permissions()
	for doctype, value in (("Company", doc.company), ("Department", doc.get("production_team"))):
		if doctype == "Department" and not team_required:
			continue
		if not value or not any(
			p.doc == value and p.applicable_for in (None, "", "Work Order")
			for p in permissions.get(doctype, [])
		):
			frappe.throw("没有此公司或班组的工单审批授权", frappe.PermissionError)


def check_production_execution(work_order, *, require_team=False, material_return=False, for_update=False):
	"""Read the actual parent and reuse the approval policy; no new quantity or lock framework."""
	order = frappe.get_doc("Work Order", work_order, for_update=for_update)
	if not order.get("approval_requested_by") and not frappe.db.exists("Workflow", PRODUCTION_APPROVAL_WORKFLOW):
		return None

	order.check_permission("read")
	_check_production_approval_scope(order, team_required=require_team)
	return validate_production_execution_state(order, material_return=material_return)


def validate_production_execution_state(order, *, material_return=False, finishing_execution=False):
	"""Internal state check for an already read/authorized production order."""
	from frappe.model.workflow import get_workflow_name

	if (
		order.docstatus != 1
		or order.get("workflow_state") != "已批准"
		or not order.get("approval_requested_by")
		or not order.get("approval_reviewed_by")
	):
		frappe.throw("工单尚未完成审核和签批，不能新增执行记录", frappe.PermissionError)
	if finishing_execution and order.status == "Closed":
		frappe.throw("工单已经结束，不能重复处理或改写原结束记录")
	if not material_return and not finishing_execution:
		if get_workflow_name("Work Order") != PRODUCTION_APPROVAL_WORKFLOW:
			frappe.throw("生产工单审批流程未启用，不能新增执行记录", frappe.PermissionError)
		if order.status in ("Stopped", "Closed"):
			frappe.throw("工单已停止或关闭，不能新增执行记录", frappe.PermissionError)
	return order


def _has_production_execution(work_order):
	"""A reversal does not erase the original execution history."""
	cards = frappe.get_all("Job Card", filters={"work_order": work_order}, pluck="name")
	if cards and (frappe.db.exists("Job Card", {"name": ["in", cards], "docstatus": [">", 0]})
		or frappe.db.exists("Job Card Time Log", {"parent": ["in", cards]})):
		return True
	return bool(frappe.get_all("Stock Entry", filters={"docstatus": [">", 0]},
		or_filters={"work_order": work_order, **({"job_card": ["in", cards]} if cards else {})}, limit=1))


def protect_production_approval_history(doc, method):
	"""Keep native audit rows and their parent once this production order has entered approval."""
	if method == "validate" and doc.is_new():
		return

	link_fields = {
		"Comment": ("reference_doctype", "reference_name"),
		"Version": ("ref_doctype", "docname"),
	}.get(doc.doctype)
	orders = set()
	# Use the stored reference as well: changing the parent must not detach protected history.
	for record in (doc.get_doc_before_save(), doc):
		if not record:
			continue
		if doc.doctype == "Work Order":
			orders.add(record.name)
		elif record.get(link_fields[0]) == "Work Order" and record.get(link_fields[1]):
			orders.add(record.get(link_fields[1]))

	for name in orders:
		order = frappe.get_doc("Work Order", name)
		if order.get("approval_requested_by") and frappe.db.exists("Comment", {
			"reference_doctype": "Work Order", "reference_name": name, "comment_type": "Workflow",
		}):
			frappe.throw("工单已进入审批，原单及历史记录不能改写、删除或改挂；请追加说明并保留原记录", frappe.PermissionError)


@frappe.whitelist()
def apply_production_approval(work_order: str, action: str, expected_modified: str, reason: str | None = None):
	"""Bind a viewed revision and three separate actors to the native Workflow transaction."""
	from html import escape

	from frappe.model.workflow import apply_workflow, get_transitions, get_workflow_name

	if get_workflow_name("Work Order") != PRODUCTION_APPROVAL_WORKFLOW:
		frappe.throw("生产工单审批流程未启用", frappe.PermissionError)
	if not expected_modified:
		frappe.throw("请刷新工单并查看最新依据后再处理", frappe.TimestampMismatchError)

	doc = frappe.get_doc("Work Order", work_order)
	doc.check_permission("write")
	# One existing work-order lock; full stock/report lock ordering remains a separate gate.
	doc = frappe.get_doc("Work Order", work_order, for_update=True)
	doc.check_permission("write")
	if get_datetime(doc.modified) != get_datetime(expected_modified):
		frappe.throw("工单已变化，请刷新并查看最新依据后再处理", frappe.TimestampMismatchError)
	if not doc.get("approval_requested_by"):
		frappe.throw("存量工单尚未确认审批依据，不能作为新单送审", frappe.PermissionError)
	if action == "送审" and (not doc.operations or not doc.required_items):
		frappe.throw("请先预览并确认生成工序任务和用料计划，再送审")

	stopping = action == "停止执行"
	if stopping:
		if "生产工单签批" not in frappe.get_roles() or doc.docstatus != 1 or doc.workflow_state != "已批准" or doc.status in ("Stopped", "Closed"):
			frappe.throw("仅生产厂长可停止已批准且尚未停止的工单", frappe.PermissionError)
		_check_production_approval_scope(doc, team_required=False)
		next_state = doc.workflow_state
	else:
		transition = next((t for t in get_transitions(doc) if t.action == action), None)
		if not transition:
			frappe.throw("当前岗位或状态不允许此审批动作", frappe.PermissionError)
		_check_production_approval_scope(doc, team_required=transition.allowed != "生产工单签批")
		next_state = transition.next_state
	user = frappe.session.user
	if action in ("送审", "撤回", "终止"):
		if user != doc.approval_requested_by:
			frappe.throw("只能由发起人处理此申请", frappe.PermissionError)
	elif action in ("审核通过", "签批通过", "退回") and user == doc.approval_requested_by:
		frappe.throw("发起人不能审核或签批自己的工单", frappe.PermissionError)
	if action == "签批通过" and (not doc.approval_reviewed_by or user == doc.approval_reviewed_by):
		frappe.throw("审核人与最终签批人必须为不同账号", frappe.PermissionError)
	reason = (reason or "").strip()
	if action in ("退回", "撤回", "终止", "取消修订", "停止执行") and not reason:
		frappe.throw("请填写本次退回、撤回、终止、取消或停止的原因")

	viewed_modified, previous_state = str(doc.modified), doc.workflow_state
	previous_context = getattr(frappe.local, "production_approval_context", None)
	frappe.local.production_approval_context = frappe._dict(
		name=doc.name, state=doc.workflow_state, next_state=next_state,
		action=action, user=user, reason=reason,
	)
	try:
		if stopping:
			stop_unstop(doc.name, "Stopped")
			result = doc.reload()
		else:
			result = apply_workflow(doc, action)
		result.add_comment("Comment", "审批动作：{0}；依据版本：{1}；{2} → {3}；原因：{4}".format(
			escape(action), escape(viewed_modified), escape(previous_state),
			escape(result.workflow_state), escape(reason or "无"),
		))
		return result
	finally:
		# Request-local authority never comes from a client Document.flags value.
		frappe.local.production_approval_context = previous_context


_DETAIL_OPERATION_FIELDS = ("operation", "description", "workstation", "workstation_type", "bom", "sequence_id", "report_plan_qty")
_DETAIL_OPERATION_NUMBERS = ("time_in_mins", "hour_rate", "batch_size", "fixed_time")
_DETAIL_ITEM_FIELDS = ("item_code", "stock_uom", "source_warehouse", "operation")
_DETAIL_ITEM_NUMBERS = ("required_qty", "include_item_in_manufacturing", "allow_alternative_item")


def _production_detail_rows(order):
	def rows(table, fields, numbers):
		return [dict(
			**{field: row.get(field) or None for field in fields},
			**{field: flt(row.get(field)) for field in numbers},
		) for row in order.get(table)]
	return {
		"operations": rows("operations", _DETAIL_OPERATION_FIELDS, _DETAIL_OPERATION_NUMBERS),
		"items": rows("required_items", _DETAIL_ITEM_FIELDS, _DETAIL_ITEM_NUMBERS),
	}


def _check_production_draft_editor(order):
	if order.docstatus != 0 or order.get("workflow_state") not in ("草稿", "退回") or order.get("approval_requested_by") != frappe.session.user:
		frappe.throw("送审后的依据已冻结，请退回或撤回后由发起人修改", frappe.PermissionError)
	if "生产工单发起" not in frappe.get_roles():
		frappe.throw("当前工单发起授权已撤销，不能调整工单明细", frappe.PermissionError)
	_check_production_approval_scope(order, team_required=True)


def _production_order_for_details(work_order, *, for_update=False):
	from frappe.model.workflow import get_workflow_name

	order = frappe.get_doc("Work Order", work_order, for_update=for_update)
	order.check_permission("read")
	order.check_permission("write")
	if get_workflow_name("Work Order") != PRODUCTION_APPROVAL_WORKFLOW:
		frappe.throw("生产工单审批流程未启用，不能调整工单明细", frappe.PermissionError)
	_check_production_draft_editor(order)
	return order


def _production_order_detail_plan(order):
	if not order.bom_no:
		frappe.throw("请先选择有效BOM并保存工单")
	bom = frappe.get_doc("BOM", order.bom_no)
	bom.check_permission("read")
	validate_bom_no(order.production_item, order.bom_no)
	plan = frappe.copy_doc(order)
	plan.approval_requested_by = order.approval_requested_by
	# Establish the same normalized operation context used by native saving first.
	plan.set_work_order_operations()
	plan.validate_operations()
	plan.validate_operations_sequence()
	plan.set_required_items()
	if not plan.operations:
		frappe.throw("BOM未维护工序路线，请先补齐BOM工序后再预览")
	if not plan.required_items:
		frappe.throw("BOM未维护生产用料，请先补齐BOM用料后再预览")
	data = _production_detail_rows(plan)
	basis = {field: order.get(field) for field in (
		"production_item", "bom_no", "qty", "company", "source_warehouse", "wip_warehouse",
		"fg_warehouse", "use_multi_level_bom", "project", "transfer_material_against",
	)}
	data["fingerprint"] = hashlib.sha256(frappe.as_json({
		"basis": basis, "bom_modified": str(bom.modified), "details": data,
	}).encode()).hexdigest()
	return plan, data


@frappe.whitelist()
def preview_production_order_details(work_order, expected_modified):
	order = _production_order_for_details(work_order)
	if not expected_modified or get_datetime(order.modified) != get_datetime(expected_modified):
		frappe.throw("工单已变化，请保存并刷新后重新预览", frappe.TimestampMismatchError)
	_, data = _production_order_detail_plan(order)
	return data


@frappe.whitelist()
def confirm_production_order_details(work_order, expected_modified, fingerprint):
	# Authorize before taking the parent lock; re-read state and scope after locking.
	_production_order_for_details(work_order)
	order = _production_order_for_details(work_order, for_update=True)
	plan, data = _production_order_detail_plan(order)
	if not fingerprint or fingerprint != data["fingerprint"]:
		frappe.throw("工单或BOM路线依据已变化，请重新预览后确认", frappe.TimestampMismatchError)
	if order.operations or order.required_items:
		if _production_detail_rows(order) != {key: data[key] for key in ("operations", "items")}:
			frappe.throw("已有明细与本次预览不同，请先核对草稿明细；不会自动覆盖")
		return {"work_order": order.name, "modified": str(order.modified)}
	if not expected_modified or get_datetime(order.modified) != get_datetime(expected_modified):
		frappe.throw("工单已变化，请刷新并重新预览后确认", frappe.TimestampMismatchError)
	for table in ("operations", "required_items"):
		order.set(table, [])
		for row in plan.get(table):
			order.append(table, {key: value for key, value in row.as_dict().items()
				if key not in ("name", "parent", "parenttype", "parentfield")})
	order.save()
	return {"work_order": order.name, "modified": str(order.modified)}


@frappe.whitelist()
def get_production_material_summary(work_order):
	from decimal import Decimal

	order = frappe.get_doc("Work Order", work_order)
	order.check_permission("read")
	items = [{"name": row.name, "item_code": row.item_code, "item_name": row.item_name,
		"unit": row.stock_uom, "required": row.required_qty, "issued": row.transferred_qty,
		"returned": row.returned_qty, "net": Decimal(str(row.transferred_qty)) - Decimal(str(row.returned_qty)),
		"consumed": row.consumed_qty, "pending_issue": None, "pending_return": None} for row in order.required_items]
	bom = frappe.get_doc("BOM", order.bom_no) if order.bom_no else None
	can_read = bool(bom and frappe.has_permission("BOM", "read", doc=bom, throw=False))
	return {"work_order": order.name, "modified": str(order.modified), "bom_no": order.bom_no,
		"can_read_bom": can_read, "can_write_bom": bool(can_read and frappe.has_permission("BOM", "write", doc=bom, throw=False)), "items": items,
		"pending_source": "库存待审批状态来源未接入，不能由全部草稿推定待审批量；未接入不等于0。",
		"effective_source": "累计领/退仅含已提交库存单据，净领为两者之差；实际消耗独立读取，不用净领替代。"}


class WorkOrder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.work_order_item.work_order_item import WorkOrderItem
		from erpnext.manufacturing.doctype.work_order_operation.work_order_operation import (
			WorkOrderOperation,
		)

		actual_end_date: DF.Datetime | None
		actual_operating_cost: DF.Currency
		actual_start_date: DF.Datetime | None
		additional_operating_cost: DF.Currency
		allow_alternative_item: DF.Check
		amended_from: DF.Link | None
		batch_size: DF.Float
		bom_no: DF.Link
		company: DF.Link
		corrective_operation_cost: DF.Currency
		description: DF.SmallText | None
		disassembled_qty: DF.Float
		expected_delivery_date: DF.Date | None
		fg_warehouse: DF.Link
		from_wip_warehouse: DF.Check
		has_batch_no: DF.Check
		has_serial_no: DF.Check
		image: DF.AttachImage | None
		item_name: DF.Data | None
		lead_time: DF.Float
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		material_transferred_for_manufacturing: DF.Float
		naming_series: DF.Literal["MFG-WO-.YYYY.-"]
		operations: DF.Table[WorkOrderOperation]
		planned_end_date: DF.Datetime | None
		planned_operating_cost: DF.Currency
		planned_start_date: DF.Datetime
		process_loss_qty: DF.Float
		produced_qty: DF.Float
		product_bundle_item: DF.Link | None
		production_item: DF.Link
		production_plan: DF.Link | None
		production_plan_item: DF.Data | None
		production_plan_sub_assembly_item: DF.Data | None
		project: DF.Link | None
		qty: DF.Float
		required_items: DF.Table[WorkOrderItem]
		sales_order: DF.Link | None
		sales_order_item: DF.Data | None
		scrap_warehouse: DF.Link | None
		skip_transfer: DF.Check
		source_warehouse: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"Submitted",
			"Not Started",
			"In Process",
			"Completed",
			"Stopped",
			"Closed",
			"Cancelled",
		]
		stock_uom: DF.Link | None
		total_operating_cost: DF.Currency
		transfer_material_against: DF.Literal["", "Work Order", "Job Card"]
		update_consumed_material_cost_in_project: DF.Check
		use_multi_level_bom: DF.Check
		wip_warehouse: DF.Link | None
	# end: auto-generated types

	def onload(self):
		ms = frappe.get_doc("Manufacturing Settings")
		self.set_onload("allow_editing_items", ms.allow_editing_of_items_and_quantities_in_work_order)
		self.set_onload("material_consumption", ms.material_consumption)
		self.set_onload("backflush_raw_materials_based_on", ms.backflush_raw_materials_based_on)
		self.set_onload("overproduction_percentage", ms.overproduction_percentage_for_work_order)

	def before_validate(self):
		self.qty = validate_quantity_input(self.qty, "工单计划量")

	def validate(self):
		self.validate_production_approval()
		before = self.get_doc_before_save()
		if (self.get("approval_requested_by") and before and self.docstatus == 0
			and (before.operations or before.required_items) and (self.operations or self.required_items)):
			basis_fields = ("production_item", "bom_no", "qty", "company", "use_multi_level_bom",
				"source_warehouse", "wip_warehouse", "fg_warehouse", "project", "transfer_material_against")
			if any((self.get(field) or None) != (before.get(field) or None) for field in basis_fields):
				frappe.throw("已有任务和用料计划时不能直接改变展开依据；请先核对并清空草稿明细，再重新预览确认")
		self.validate_report_pricing()
		self.validate_production_item()
		if self.bom_no:
			validate_bom_no(self.production_item, self.bom_no)

		self.validate_sales_order()
		self.set_default_warehouse()
		self.validate_warehouse_belongs_to_company()
		self.check_wip_warehouse_skip()
		self.calculate_operating_cost()
		self.validate_qty()
		self.validate_dates()
		self.validate_transfer_against()
		self.validate_operations()
		self.status = self.get_status()
		self.validate_workstation_type()
		self.reset_use_multi_level_bom()

		if self.source_warehouse:
			self.set_warehouses()

		validate_uom_is_integer(self, "stock_uom", ["required_qty"])

		# Approval drafts prepare their plan only after an explicit human confirmation.
		if not self.get("approval_requested_by") and (
			not len(self.get("required_items")) or not frappe.db.get_single_value(
				"Manufacturing Settings", "allow_editing_of_items_and_quantities_in_work_order"
			)
		):
			self.set_required_items(reset_only_qty=len(self.get("required_items")))

		self.validate_operations_sequence()

	def validate_report_pricing(self):
		from decimal import Decimal

		editable = self.docstatus == 0 and self.get("workflow_state") in (None, "", "草稿", "退回")
		for row in self.operations:
			mode, rate = row.get("report_wage_mode"), row.get("report_wage_rate")
			if mode not in (None, "", "hourly", "piece"):
				frappe.throw("报工计价方式必须为计时或计件")
			if bool(mode) != (rate not in (None, "")):
				frappe.throw("计价方式和工资单价必须同时填写；未知单价请保持两项为空")
			for field, label in (("report_wage_rate", "工资单价"), ("report_standard_efficiency", "标准效率")):
				value = row.get(field)
				if value not in (None, ""):
					validate_quantity_input(value, label, allow_zero=True)
					row.set(field, format(Decimal(str(value)).normalize(), "f"))
			if editable:
				row.report_wage_currency = frappe.db.get_value("Company", self.company, "default_currency") if mode else None
			if mode and not row.get("report_wage_currency"):
				frappe.throw("缺少工序计价币种，请在草稿中核对公司币种并保存")

	def validate_production_approval(self):
		from frappe.model.workflow import get_workflow_name

		active = get_workflow_name("Work Order") == PRODUCTION_APPROVAL_WORKFLOW
		before = self.get_doc_before_save()
		was_approval_order = before and before.get("approval_requested_by")
		if not active and not (was_approval_order or self.get("approval_requested_by")):
			return
		if not active:
			frappe.throw("生产工单审批流程未启用，不能修改审批工单", frappe.PermissionError)
		user = frappe.session.user
		if self.is_new():
			if "生产工单发起" not in frappe.get_roles():
				frappe.throw("只有已授权的操作工可以发起工单", frappe.PermissionError)
			_check_production_approval_scope(self, team_required=True)
		if self.is_new() or any(self.get(f) != before.get(f) for f in ("amended_from", "previous_work_order", "company")):
			references = [self.get(f) for f in ("amended_from", "previous_work_order") if self.get(f)]
			if len(references) > 1:
				frappe.throw("取消修订和剩余需求关联不能同时指定")
			if references:
				previous = frappe.get_doc("Work Order", references[0])
				previous.check_permission("read")
				_check_production_approval_scope(previous, team_required=True)
				if not previous.get("approval_requested_by") or previous.company != self.company:
					frappe.throw("只能关联本公司已确认审批依据的原工单", frappe.PermissionError)
				if self.get("previous_work_order") and (
					previous.docstatus != 1 or previous.status != "Stopped" or not _has_production_execution(previous.name)
				):
					frappe.throw("剩余需求只能关联已有执行历史且已停止的原工单", frappe.PermissionError)
				if not self.is_new() and self.get("amended_from") and previous.docstatus != 2:
					frappe.throw("只有已取消工单可以作为取消修订来源", frappe.PermissionError)
		if self.is_new():
			team = frappe.get_cached_value("Department", self.production_team, ["company", "is_group", "disabled"], as_dict=True)
			if not team or team.company != self.company or team.is_group or team.disabled:
				frappe.throw("请选择本公司有效的执行班组")
			if any(self.get(f) for f in ("approval_requested_by", "approval_reviewed_by", "approval_note")) or self.get("workflow_state") not in (None, "", "草稿") or self.docstatus != 0:
				frappe.throw("不能在创建工单时指定审批结果或处理人", frappe.PermissionError)
			actual_quantities = (("produced_qty", "成品入库数量"),
				("material_transferred_for_manufacturing", "已领料数量"),
				("process_loss_qty", "实际损耗数量"), ("disassembled_qty", "已拆解数量"))
			if self.actual_start_date or self.actual_end_date or any(
				validate_quantity_input(self.get(field), label, allow_zero=True)
				for field, label in actual_quantities if self.get(field) not in (None, "")
			):
				frappe.throw("新工单不能填写实际生产日期或数量，请通过正常报工和库存入口形成事实", frappe.PermissionError)
			for row in self.operations:
				if row.actual_start_time or row.actual_end_time or row.status not in (None, "", "Pending") or any(
					validate_quantity_input(row.get(field), label, allow_zero=True)
					for field, label in (("completed_qty", "工序良品数量"), ("process_loss_qty", "工序不良数量"),
						("actual_operation_time", "实际工序用时")) if row.get(field) not in (None, "")
				):
					frappe.throw("新工单工序不能填写实际生产日期、数量或执行状态，请通过正常报工形成事实", frappe.PermissionError)
			if self.operations or self.required_items:
				frappe.throw("新工单请先保存空草稿，再预览确认生成任务和用料计划", frappe.PermissionError)
			self.validate_production_header()
			self.approval_requested_by = user
			self.workflow_state = "草稿"
			return

		if not before.get("approval_requested_by"):
			frappe.throw("存量工单尚未确认审批依据，不能作为新单处理", frappe.PermissionError)
		context = getattr(frappe.local, "production_approval_context", None)
		if context and context.name == self.name and context.user == user and context.state == before.workflow_state and context.next_state == self.workflow_state:
			if context.action == "送审":
				self.validate_production_header(for_review=True)
			self.approval_note = context.reason
			if context.action == "审核通过":
				self.approval_reviewed_by = user
			elif context.action in ("送审", "退回", "撤回", "终止"):
				self.approval_reviewed_by = None
			return

		context = getattr(frappe.local, "production_report_context", None)
		if context and context.order is self and context.user == user and context.card.work_order == self.name:
			self.validate_report_derivation(before, context.operation_id)
			return

		protected = ("workflow_state", "approval_requested_by", "approval_reviewed_by", "approval_note", "docstatus")
		if any(self.get(f) != before.get(f) for f in protected):
			frappe.throw("请通过工单审批动作处理，不能直接改审批字段或提交", frappe.PermissionError)
		_check_production_draft_editor(self)
		self.validate_production_header()

	def validate_production_header(self, *, for_review=False):
		# Apply to preparation and sending only; other transitions and old approved facts stay valid.
		if not self.expected_delivery_date:
			if for_review:
				frappe.throw("送审前请填写预计交付日期；草稿可以暂不填写")
			return
		if not isinstance(self.expected_delivery_date, (str, date)):
			frappe.throw("预计交付日期无效，请填写有效日期")
		delivery = getdate(self.expected_delivery_date)
		if delivery is None:
			frappe.throw("预计交付日期无效，请填写有效日期")
		if self.planned_start_date:
			start = getdate(self.planned_start_date)
			if start is None:
				frappe.throw("计划开始日期无效，请填写有效日期")
			if delivery < start:
				frappe.msgprint("预计交付日期早于计划开始日期，可能逾期；请核对安排，系统保留原交期。", indicator="orange", alert=True)
		self.expected_delivery_date = delivery

	def validate_report_derivation(self, before, operation_id):
		parent_fields = {"actual_operating_cost", "total_operating_cost", "actual_start_date", "actual_end_date", "lead_time", "status", "modified", "modified_by"}
		operation_fields = {"completed_qty", "process_loss_qty", "actual_operation_time", "actual_start_time", "actual_end_time", "status", "actual_operating_cost", "modified", "modified_by"}
		old, new = before.as_dict(), self.as_dict()
		for field in set(old) | set(new):
			if field == "operations":
				continue
			left_value, right_value = old.get(field), new.get(field)
			if self.meta.get_field(field) and self.meta.get_field(field).fieldtype in ("Table", "Table MultiSelect"):
				left_value, right_value = [
					[{k: v for k, v in row.items() if k not in ("modified", "modified_by")} for row in rows]
					for rows in (left_value or [], right_value or [])
				]
			if field not in parent_fields and left_value != right_value:
				frappe.throw("报工不能修改工单字段：" + field, frappe.PermissionError)
		if [r.name for r in before.operations] != [r.name for r in self.operations]:
			frappe.throw("报工不能修改任务清单", frappe.PermissionError)
		for left, right in zip(before.operations, self.operations):
			allowed = operation_fields if right.name == operation_id else {"modified", "modified_by"}
			for field in set(left.as_dict()) | set(right.as_dict()):
				if field not in allowed and left.get(field) != right.get(field):
					frappe.throw("报工不能修改任务字段：" + field, frappe.PermissionError)

	def before_update_after_submit(self):
		self.validate_production_approval()

	def before_cancel(self):
		self.validate_production_approval()
		if self.get("approval_requested_by") and _has_production_execution(self.name):
			frappe.throw("工单已有领料、计时或报工历史，不能取消修订；请停止执行并关联新单", frappe.PermissionError)

	def validate_dates(self):
		if self.planned_start_date and self.planned_end_date:
			if get_datetime(self.planned_end_date) < get_datetime(self.planned_start_date):
				frappe.throw(_("Planned End Date cannot be before Planned Start Date"))

	def validate_operations_sequence(self):
		if all([not op.sequence_id for op in self.operations]):
			for op in self.operations:
				op.sequence_id = op.idx
		else:
			sequence_id = 1
			for op in self.operations:
				if op.idx == 1 and op.sequence_id != 1:
					frappe.throw(
						_("Row #1: Sequence ID must be 1 for Operation {0}.").format(
							frappe.bold(op.operation)
						)
					)
				elif op.sequence_id != sequence_id and op.sequence_id != sequence_id + 1:
					frappe.throw(
						_("Row #{0}: Sequence ID must be {1} or {2} for Operation {3}.").format(
							op.idx,
							frappe.bold(sequence_id),
							frappe.bold(sequence_id + 1),
							frappe.bold(op.operation),
						)
					)
				sequence_id = op.sequence_id

	def set_warehouses(self):
		for row in self.required_items:
			if not row.source_warehouse:
				row.source_warehouse = self.source_warehouse

	def reset_use_multi_level_bom(self):
		if self.is_new() or self.get("approval_requested_by"):
			return

		before_save_obj = self.get_doc_before_save()
		if before_save_obj.use_multi_level_bom != self.use_multi_level_bom:
			self.get_items_and_operations_from_bom()

	def validate_workstation_type(self):
		if not self.docstatus.is_submitted():
			return

		for row in self.operations:
			if not row.workstation and not row.workstation_type:
				frappe.throw(
					_("Row {0}: Workstation or Workstation Type is mandatory for an operation {1}").format(
						row.idx, row.operation
					)
				)

	def validate_sales_order(self):
		if self.production_plan_sub_assembly_item:
			return

		production_item = self.production_item

		if self.material_request_item and (
			mr_plan_item := frappe.get_value(
				"Material Request Item", self.material_request_item, "material_request_plan_item"
			)
		):
			if main_item_code := frappe.get_value(
				"Material Request Plan Item", mr_plan_item, "main_item_code"
			):
				production_item = main_item_code

		if self.sales_order:
			self.check_sales_order_on_hold_or_close()

			SalesOrder = frappe.qb.DocType("Sales Order")
			SalesOrderItem = frappe.qb.DocType("Sales Order Item")
			PackedItem = frappe.qb.DocType("Packed Item")
			ProductBundleItem = frappe.qb.DocType("Product Bundle Item")

			so_query = (
				frappe.qb.from_(SalesOrder)
				.inner_join(SalesOrderItem)
				.on(SalesOrderItem.parent == SalesOrder.name)
				.left_join(ProductBundleItem)
				.on(ProductBundleItem.parent == SalesOrderItem.item_code)
				.select(SalesOrder.name, SalesOrder.project, SalesOrderItem.delivery_date)
				.where(
					(SalesOrder.skip_delivery_note == 0)
					& (SalesOrder.docstatus == 1)
					& (SalesOrder.name == self.sales_order)
					& (
						(SalesOrderItem.item_code == production_item)
						| (ProductBundleItem.item_code == production_item)
					)
				)
			)

			if self.sales_order_item:
				so_query = so_query.where(SalesOrderItem.name == self.sales_order_item)

			so = so_query.run(as_dict=1)

			if not so:
				packed_so_query = (
					frappe.qb.from_(SalesOrder)
					.inner_join(SalesOrderItem)
					.on(SalesOrderItem.parent == SalesOrder.name)
					.inner_join(PackedItem)
					.on(
						(PackedItem.parent == SalesOrder.name)
						& (PackedItem.parent_detail_docname == SalesOrderItem.name)
					)
					.select(SalesOrder.name, SalesOrder.project, SalesOrderItem.delivery_date)
					.where(
						(SalesOrder.name == self.sales_order)
						& (SalesOrder.skip_delivery_note == 0)
						& (SalesOrderItem.item_code == PackedItem.parent_item)
						& (SalesOrder.docstatus == 1)
						& (PackedItem.item_code == production_item)
					)
				)

				if self.sales_order_item:
					packed_so_query = packed_so_query.where(
						(PackedItem.name == self.sales_order_item)
						| (SalesOrderItem.name == self.sales_order_item)
					)

				so = packed_so_query.run(as_dict=1)

			if len(so):
				if not self.expected_delivery_date:
					self.expected_delivery_date = so[0].delivery_date

				if so[0].project:
					self.project = so[0].project

				if not self.material_request:
					self.validate_work_order_against_so()
			else:
				frappe.throw(_("Sales Order {0} is not valid").format(self.sales_order))

	def check_sales_order_on_hold_or_close(self):
		status = frappe.db.get_value("Sales Order", self.sales_order, "status")
		if status in ("Closed", "On Hold"):
			frappe.throw(_("Sales Order {0} is {1}").format(self.sales_order, status))

	def set_default_warehouse(self):
		if not self.wip_warehouse and not self.skip_transfer:
			self.wip_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_wip_warehouse")
		if not self.fg_warehouse:
			self.fg_warehouse = self.get_default_fg_warehouse()

	def get_default_fg_warehouse(self):
		return (
			frappe.db.get_single_value("Manufacturing Settings", "default_fg_warehouse")
			or self.get_production_item_warehouse()
		)

	def get_production_item_warehouse(self):
		if not self.production_item:
			return None

		return get_item_defaults(self.production_item, self.company).get(
			"default_warehouse"
		) or get_item_group_defaults(self.production_item, self.company).get("default_warehouse")

	def check_wip_warehouse_skip(self):
		if self.skip_transfer and not self.from_wip_warehouse:
			self.wip_warehouse = None

	def validate_warehouse_belongs_to_company(self):
		warehouses = [self.fg_warehouse, self.wip_warehouse]
		for d in self.get("required_items"):
			if d.source_warehouse not in warehouses:
				warehouses.append(d.source_warehouse)

		for wh in warehouses:
			validate_warehouse_company(wh, self.company)

	def calculate_operating_cost(self):
		self.planned_operating_cost, self.actual_operating_cost = 0.0, 0.0
		for d in self.get("operations"):
			if not d.hour_rate:
				if d.workstation:
					d.hour_rate = get_hour_rate(d.workstation)

			d.planned_operating_cost = flt(
				flt(d.hour_rate) * (flt(d.time_in_mins) / 60.0), d.precision("planned_operating_cost")
			)
			d.actual_operating_cost = flt(
				flt(d.hour_rate) * (flt(d.actual_operation_time) / 60.0), d.precision("actual_operating_cost")
			)

			self.planned_operating_cost += flt(d.planned_operating_cost)
			self.actual_operating_cost += flt(d.actual_operating_cost)

		variable_cost = (
			self.actual_operating_cost if self.actual_operating_cost else self.planned_operating_cost
		)

		self.total_operating_cost = (
			flt(self.additional_operating_cost) + flt(variable_cost) + flt(self.corrective_operation_cost)
		)

	def validate_work_order_against_so(self):
		# already ordered qty
		ordered_qty_against_so = frappe.db.sql(
			"""select sum(qty - process_loss_qty) from `tabWork Order`
			where production_item = %s and sales_order = %s and docstatus < 2 and status != 'Closed' and name != %s""",
			(self.production_item, self.sales_order, self.name),
		)[0][0]

		total_qty = flt(ordered_qty_against_so) + flt(self.qty)

		# get qty from Sales Order Item table
		so_item_qty = frappe.db.sql(
			"""select sum(stock_qty) from `tabSales Order Item`
			where parent = %s and item_code = %s""",
			(self.sales_order, self.production_item),
		)[0][0]
		# get qty from Packing Item table
		dnpi_qty = frappe.db.sql(
			"""select sum(qty) from `tabPacked Item`
			where parent = %s and parenttype = 'Sales Order' and item_code = %s""",
			(self.sales_order, self.production_item),
		)[0][0]
		# total qty in SO
		so_qty = flt(so_item_qty) + flt(dnpi_qty)

		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_sales_order")
		)

		if total_qty > so_qty + (allowance_percentage / 100 * so_qty):
			frappe.throw(
				_("Cannot produce more Item {0} than Sales Order quantity {1}").format(
					self.production_item, so_qty
				),
				OverProductionError,
			)

	def update_status(self, status=None):
		"""Update status of work order if unknown"""
		if self.status != "Closed":
			if status not in ["Stopped", "Closed"]:
				status = self.get_status(status)

			if status != self.status:
				self.db_set("status", status)

		self.update_required_items()

		return status or self.status

	def get_status(self, status=None):
		"""Return the status based on stock entries against this work order"""
		if not status:
			status = self.status

		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			if status not in ["Closed", "Stopped"]:
				status = "Not Started"
				if flt(self.material_transferred_for_manufacturing) > 0 or self.has_transferred_material():
					status = "In Process"

				if self.get("approval_requested_by") and frappe.db.exists("Job Card", {"work_order": self.name, "docstatus": 1, "report_request_id": ["is", "set"]}):
					status = "In Process"

				precision = frappe.get_precision("Work Order", "produced_qty")
				total_qty = flt(self.produced_qty, precision) + flt(self.process_loss_qty, precision)
				if flt(total_qty, precision) >= flt(self.qty, precision):
					status = "Completed"
		else:
			status = "Cancelled"

		if self.skip_transfer and self.produced_qty and status not in ("Stopped", "Closed"):
			precision = frappe.get_precision("Work Order", "produced_qty")
			total_qty = flt(self.produced_qty, precision) + flt(self.process_loss_qty, precision)
			if flt(self.qty, precision) > flt(total_qty, precision):
				status = "In Process"

		return status

	def has_transferred_material(self):
		"""True if any raw material was transferred against this work order via a pick list
		(these leave material_transferred_for_manufacturing at 0 via the min-fraction rule)."""
		ste = frappe.qb.DocType("Stock Entry")
		ste_child = frappe.qb.DocType("Stock Entry Detail")
		qty = (
			frappe.qb.from_(ste)
			.inner_join(ste_child)
			.on(ste_child.parent == ste.name)
			.select(Sum(ste_child.transfer_qty))
			.where(
				(ste.work_order == self.name)
				& (ste.docstatus == 1)
				& (ste.purpose == "Material Transfer for Manufacture")
				& (ste.is_return == 0)
				& (ste.pick_list.isnotnull())
			)
		).run()[0][0]
		return flt(qty) > 0

	def update_work_order_qty(self):
		"""Update **Manufactured Qty** and **Material Transferred for Qty** in Work Order
		based on Stock Entry"""

		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)

		for purpose, fieldname in (
			("Manufacture", "produced_qty"),
			("Material Transfer for Manufacture", "material_transferred_for_manufacturing"),
		):
			if (
				purpose == "Material Transfer for Manufacture"
				and self.operations
				and self.transfer_material_against == "Job Card"
			):
				continue

			qty = self.get_transferred_or_manufactured_qty(purpose)

			completed_qty = self.qty + (allowance_percentage / 100 * self.qty)
			if qty > completed_qty:
				frappe.throw(
					_("{0} ({1}) cannot be greater than planned quantity ({2}) in Work Order {3}").format(
						_(self.meta.get_label(fieldname)), qty, completed_qty, self.name
					),
					StockOverProductionError,
				)

			self.db_set(fieldname, qty)
			self.set_process_loss_qty()

			from erpnext.selling.doctype.sales_order.sales_order import update_produced_qty_in_so_item

			if self.sales_order and self.sales_order_item and not self.production_plan_sub_assembly_item:
				update_produced_qty_in_so_item(self.sales_order, self.sales_order_item)

		if self.production_plan:
			self.set_produced_qty_for_sub_assembly_item()
			self.update_production_plan_status()

	def update_disassembled_qty(self, qty, is_cancel=False):
		precision = self.precision("disassembled_qty")
		if is_cancel:
			self.disassembled_qty = max(0, flt(self.disassembled_qty - qty, precision))
		else:
			if self.docstatus == 1:
				self.disassembled_qty = flt(self.disassembled_qty + qty, precision)

		if not is_cancel and self.disassembled_qty > self.produced_qty:
			frappe.throw(_("Cannot disassemble more than produced quantity."))

		self.db_set("disassembled_qty", self.disassembled_qty)

	def get_transferred_or_manufactured_qty(self, purpose):
		table = frappe.qb.DocType("Stock Entry")
		query = frappe.qb.from_(table).where(
			(table.work_order == self.name) & (table.docstatus == 1) & (table.purpose == purpose)
		)

		if purpose == "Manufacture":
			query = query.select(Sum(table.fg_completed_qty) - Sum(table.process_loss_qty))
		else:
			query = query.select(Sum(table.fg_completed_qty))

		return flt(query.run()[0][0])

	def set_process_loss_qty(self):
		table = frappe.qb.DocType("Stock Entry")
		process_loss_qty = (
			frappe.qb.from_(table)
			.select(Sum(table.process_loss_qty))
			.where(
				(table.work_order == self.name) & (table.purpose == "Manufacture") & (table.docstatus == 1)
			)
		).run()[0][0]

		self.db_set("process_loss_qty", flt(process_loss_qty))

	def update_production_plan_status(self):
		production_plan = frappe.get_doc("Production Plan", self.production_plan)
		production_plan.flags.ignore_permissions = True
		produced_qty = 0
		if self.production_plan_item:
			total_qty = frappe.get_all(
				"Work Order",
				fields="sum(produced_qty) as produced_qty",
				filters={
					"docstatus": 1,
					"production_plan": self.production_plan,
					"production_plan_item": self.production_plan_item,
				},
				as_list=1,
			)

			produced_qty = total_qty[0][0] if total_qty else 0

		self.update_status()
		production_plan.run_method("update_produced_pending_qty", produced_qty, self.production_plan_item)

	def before_submit(self):
		self.create_serial_no_batch_no()

	def on_submit(self):
		if not self.wip_warehouse and not self.skip_transfer:
			frappe.throw(_("Work-in-Progress Warehouse is required before Submit"))
		if not self.fg_warehouse:
			frappe.throw(_("For Warehouse is required before Submit"))

		if self.production_plan and frappe.db.exists(
			"Production Plan Item Reference", {"parent": self.production_plan}
		):
			self.update_work_order_qty_in_combined_so()
		else:
			self.update_work_order_qty_in_so()

		self.update_ordered_qty()
		self.update_reserved_qty_for_production()
		self.update_completed_qty_in_material_request()
		self.update_planned_qty()
		self.create_job_card()

	def on_cancel(self):
		self.validate_cancel()
		self.db_set("status", "Cancelled")

		self.on_close_or_cancel()

	def on_close_or_cancel(self):
		if self.production_plan and frappe.db.exists(
			"Production Plan Item Reference", {"parent": self.production_plan}
		):
			self.update_work_order_qty_in_combined_so()
		else:
			self.update_work_order_qty_in_so()

		self.update_completed_qty_in_material_request()
		self.update_planned_qty()
		self.update_ordered_qty()
		self.update_reserved_qty_for_production()

	def create_serial_no_batch_no(self):
		if not (self.has_serial_no or self.has_batch_no):
			return

		if not cint(
			frappe.db.get_single_value("Manufacturing Settings", "make_serial_no_batch_from_work_order")
		):
			return

		if self.has_batch_no:
			self.create_batch_for_finished_good()

		args = {"item_code": self.production_item, "work_order": self.name}

		if self.has_serial_no:
			self.make_serial_nos(args)

	def create_batch_for_finished_good(self):
		total_qty = self.qty
		if not self.batch_size:
			self.batch_size = total_qty

		batch_auto_creation = frappe.get_cached_value("Item", self.production_item, "create_new_batch")
		if not batch_auto_creation:
			frappe.msgprint(
				_("Batch not created for item {} since it does not have a batch series.").format(
					frappe.bold(self.production_item)
				),
				alert=True,
				indicator="orange",
			)
			return

		while total_qty > 0:
			qty = self.batch_size
			if self.batch_size >= total_qty:
				qty = total_qty

			if total_qty > self.batch_size:
				total_qty -= self.batch_size
			else:
				qty = total_qty
				total_qty = 0

			make_batch(
				frappe._dict(
					{
						"item": self.production_item,
						"qty_to_produce": qty,
						"reference_doctype": self.doctype,
						"reference_name": self.name,
					}
				)
			)

	def make_serial_nos(self, args):
		item_details = frappe.get_cached_value(
			"Item", self.production_item, ["serial_no_series", "item_name", "description"], as_dict=1
		)

		batches = []
		if self.has_batch_no:
			batches = frappe.get_all(
				"Batch", filters={"reference_name": self.name}, order_by="creation", pluck="name"
			)

		serial_nos = []
		if item_details.serial_no_series:
			serial_nos = get_available_serial_nos(item_details.serial_no_series, self.qty)

		if not serial_nos:
			return

		fields = [
			"name",
			"serial_no",
			"creation",
			"modified",
			"owner",
			"modified_by",
			"company",
			"item_code",
			"item_name",
			"description",
			"status",
			"work_order",
			"batch_no",
		]

		serial_nos_details = []
		index = 0
		for serial_no in serial_nos:
			index += 1
			batch_no = None
			if batches and self.batch_size:
				batch_no = batches[0]

				if index % self.batch_size == 0:
					batches.remove(batch_no)

			serial_nos_details.append(
				(
					serial_no,
					serial_no,
					now(),
					now(),
					frappe.session.user,
					frappe.session.user,
					self.company,
					self.production_item,
					item_details.item_name,
					item_details.description,
					"Inactive",
					self.name,
					batch_no,
				)
			)

		frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

	def create_job_card(self):
		manufacturing_settings_doc = frappe.get_doc("Manufacturing Settings")

		enable_capacity_planning = not cint(manufacturing_settings_doc.disable_capacity_planning)
		plan_days = cint(manufacturing_settings_doc.capacity_planning_for_days) or 30

		for idx, row in enumerate(self.operations):
			qty = self.get_operation_plan_quantity(row)
			while qty > 0:
				qty = split_qty_based_on_batch_size(self, row, qty)
				if row.job_card_qty > 0:
					self.prepare_data_for_job_card(row, idx, plan_days, enable_capacity_planning)

		planned_end_date = self.operations and self.operations[-1].planned_end_time
		if planned_end_date:
			self.db_set("planned_end_date", planned_end_date)

	def prepare_data_for_job_card(self, row, idx, plan_days, enable_capacity_planning):
		self.set_operation_start_end_time(row, idx)

		job_card_doc = create_job_card(
			self, row, auto_create=True, enable_capacity_planning=enable_capacity_planning
		)

		if enable_capacity_planning and job_card_doc:
			row.planned_start_time = job_card_doc.scheduled_time_logs[-1].from_time
			row.planned_end_time = job_card_doc.scheduled_time_logs[-1].to_time

			if date_diff(row.planned_end_time, self.planned_start_date) > plan_days:
				frappe.message_log.pop()
				frappe.throw(
					_(
						"Unable to find the time slot in the next {0} days for the operation {1}. Please increase the 'Capacity Planning For (Days)' in the {2}."
					).format(
						plan_days,
						row.operation,
						get_link_to_form("Manufacturing Settings", "Manufacturing Settings"),
					),
					CapacityError,
				)

			row.db_update()

	def set_operation_start_end_time(self, row, idx):
		"""Set start and end time for given operation. If first operation, set start as
		`planned_start_date`, else add time diff to end time of earlier operation."""
		if idx == 0:
			# first operation at planned_start date
			row.planned_start_time = self.planned_start_date
		elif self.operations[idx - 1].sequence_id:
			if self.operations[idx - 1].sequence_id == row.sequence_id:
				row.planned_start_time = self.operations[idx - 1].planned_start_time
			else:
				last_ops_with_same_sequence_ids = sorted(
					[op for op in self.operations if op.sequence_id == self.operations[idx - 1].sequence_id],
					key=lambda op: get_datetime(op.planned_end_time),
				)
				row.planned_start_time = (
					get_datetime(last_ops_with_same_sequence_ids[-1].planned_end_time)
					+ get_mins_between_operations()
				)
		else:
			row.planned_start_time = (
				get_datetime(self.operations[idx - 1].planned_end_time) + get_mins_between_operations()
			)

		row.planned_end_time = get_datetime(row.planned_start_time) + relativedelta(minutes=row.time_in_mins)

		if row.planned_start_time == row.planned_end_time:
			frappe.throw(_("Capacity Planning Error, planned start time can not be same as end time"))

	def validate_cancel(self):
		# Approval cancellation already checks the controlled action and all execution history in before_cancel.
		if self.status == "Stopped" and not self.get("approval_requested_by"):
			frappe.throw(_("Stopped Work Order cannot be cancelled, Unstop it first to cancel"))

		# Check whether any stock entry exists against this Work Order
		stock_entry = frappe.db.sql(
			"""select name from `tabStock Entry`
			where work_order = %s and docstatus = 1""",
			self.name,
		)
		if stock_entry:
			frappe.throw(
				_("Cannot cancel because submitted Stock Entry {0} exists").format(
					frappe.utils.get_link_to_form("Stock Entry", stock_entry[0][0])
				)
			)

	def update_planned_qty(self):
		from erpnext.manufacturing.doctype.production_plan.production_plan import (
			get_reserved_qty_for_sub_assembly,
		)

		qty_dict = {"planned_qty": get_planned_qty(self.production_item, self.fg_warehouse)}

		if self.production_plan_sub_assembly_item and self.production_plan:
			qty_dict["reserved_qty_for_production_plan"] = get_reserved_qty_for_sub_assembly(
				self.production_item, self.fg_warehouse
			)

		update_bin_qty(
			self.production_item,
			self.fg_warehouse,
			qty_dict,
		)

		if self.material_request:
			mr_obj = frappe.get_doc("Material Request", self.material_request)
			mr_obj.update_requested_qty([self.material_request_item])

	def set_produced_qty_for_sub_assembly_item(self):
		table = frappe.qb.DocType("Work Order")

		query = (
			frappe.qb.from_(table)
			.select(Sum(table.produced_qty))
			.where(
				(table.production_plan == self.production_plan)
				& (table.production_plan_sub_assembly_item == self.production_plan_sub_assembly_item)
				& (table.docstatus == 1)
			)
		).run()

		produced_qty = flt(query[0][0]) if query else 0

		frappe.db.set_value(
			"Production Plan Sub Assembly Item",
			self.production_plan_sub_assembly_item,
			"wo_produced_qty",
			produced_qty,
		)

	def update_ordered_qty(self):
		if self.production_plan and (self.production_plan_item or self.production_plan_sub_assembly_item):
			table = frappe.qb.DocType("Work Order")

			query = (
				frappe.qb.from_(table)
				.select(Sum(table.qty))
				.where((table.production_plan == self.production_plan) & (table.docstatus == 1))
			)

			if self.production_plan_item:
				query = query.where(table.production_plan_item == self.production_plan_item)
			elif self.production_plan_sub_assembly_item:
				query = query.where(
					table.production_plan_sub_assembly_item == self.production_plan_sub_assembly_item
				)

			query = query.run()
			qty = flt(query[0][0]) if query else 0

			doc = frappe.get_doc("Production Plan", self.production_plan)
			had_unordered_items = doc.has_unordered_items

			if self.production_plan_item:
				frappe.db.set_value("Production Plan Item", self.production_plan_item, "ordered_qty", qty)
			elif self.production_plan_sub_assembly_item:
				frappe.db.set_value(
					"Production Plan Sub Assembly Item",
					self.production_plan_sub_assembly_item,
					"ordered_qty",
					qty,
				)

			doc.reload()
			doc.flags.ignore_permissions = True
			doc.update_status_and_bin_qty()
			if had_unordered_items != doc.has_unordered_items:
				doc.update_raw_material_bin_qty()
			else:
				doc.update_raw_material_bin_qty({d.item_code for d in self.required_items})

	def update_work_order_qty_in_so(self):
		if (not self.sales_order and not self.sales_order_item) or self.production_plan_sub_assembly_item:
			return

		total_bundle_qty = 1
		if self.product_bundle_item:
			total_bundle_qty = frappe.db.sql(
				""" select sum(qty) from
				`tabProduct Bundle Item` where parent = %s""",
				(frappe.db.escape(self.product_bundle_item)),
			)[0][0]

			if not total_bundle_qty:
				# product bundle is 0 (product bundle allows 0 qty for items)
				total_bundle_qty = 1

		cond = "product_bundle_item = %s" if self.product_bundle_item else "production_item = %s"

		qty = frappe.db.sql(
			f""" select sum(qty) from
			`tabWork Order` where sales_order = %s and docstatus = 1 and status <> 'Closed' and {cond}
			""",
			(self.sales_order, (self.product_bundle_item or self.production_item)),
			as_list=1,
		)

		work_order_qty = qty[0][0] if qty and qty[0][0] else 0
		frappe.db.set_value(
			"Sales Order Item",
			self.sales_order_item,
			"work_order_qty",
			flt(work_order_qty / total_bundle_qty, 2),
		)

	def update_work_order_qty_in_combined_so(self):
		total_bundle_qty = 1
		if self.product_bundle_item:
			total_bundle_qty = frappe.db.sql(
				""" select sum(qty) from
				`tabProduct Bundle Item` where parent = %s""",
				(frappe.db.escape(self.product_bundle_item)),
			)[0][0]

			if not total_bundle_qty:
				# product bundle is 0 (product bundle allows 0 qty for items)
				total_bundle_qty = 1

		prod_plan = frappe.get_doc("Production Plan", self.production_plan)
		item_reference = frappe.get_value(
			"Production Plan Item", self.production_plan_item, "sales_order_item"
		)

		for plan_reference in prod_plan.prod_plan_references:
			work_order_qty = 0.0
			if plan_reference.item_reference == item_reference:
				if self.docstatus == 1:
					work_order_qty = flt(plan_reference.qty) / total_bundle_qty
				frappe.db.set_value(
					"Sales Order Item", plan_reference.sales_order_item, "work_order_qty", work_order_qty
				)

	def update_completed_qty_in_material_request(self):
		if self.material_request and self.material_request_item:
			frappe.get_doc("Material Request", self.material_request).update_completed_qty(
				[self.material_request_item]
			)

	def set_work_order_operations(self):
		"""Fetch operations from BOM and set in 'Work Order'"""

		def _get_operations(bom_no, qty=1):
			data = frappe.get_all(
				"BOM Operation",
				filters={"parent": bom_no},
				fields=[
					"operation",
					"description",
					"workstation",
					"idx",
					"workstation_type",
					"base_hour_rate as hour_rate",
					"time_in_mins",
					"parent as bom",
					"batch_size",
					"sequence_id",
					"fixed_time",
				],
				order_by="idx",
			)

			for d in data:
				if not d.fixed_time:
					d.time_in_mins = flt(d.time_in_mins) * flt(qty)
				d.status = "Pending"

			return data

		self.set("operations", [])
		if not self.bom_no or not frappe.get_cached_value("BOM", self.bom_no, "with_operations"):
			return

		operations = []

		if self.use_multi_level_bom:
			bom_tree = frappe.get_doc("BOM", self.bom_no).get_tree_representation()
			bom_traversal = reversed(bom_tree.level_order_traversal())

			for node in bom_traversal:
				if node.is_bom:
					operations.extend(_get_operations(node.name, qty=node.exploded_qty / node.bom_qty))

		bom_qty = frappe.get_cached_value("BOM", self.bom_no, "quantity")
		operations.extend(_get_operations(self.bom_no, qty=1.0 / bom_qty))

		for correct_index, operation in enumerate(operations, start=1):
			operation.idx = correct_index

		self.set("operations", operations)
		self.calculate_time()

	def calculate_time(self):
		for d in self.get("operations"):
			if not d.fixed_time:
				d.time_in_mins = flt(d.time_in_mins) * (flt(self.qty) / flt(d.batch_size))

		self.calculate_operating_cost()

	def get_holidays(self, workstation):
		holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")

		holidays = {}

		if holiday_list not in holidays:
			holiday_list_days = [
				getdate(d[0])
				for d in frappe.get_all(
					"Holiday",
					fields=["holiday_date"],
					filters={"parent": holiday_list},
					order_by="holiday_date",
					limit_page_length=0,
					as_list=1,
				)
			]

			holidays[holiday_list] = holiday_list_days

		return holidays[holiday_list]

	def update_operation_status(self, operation_id=None):
		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)
		for d in self.get("operations"):
			plan = flt(self.get_operation_plan_quantity(d))
			max_allowed_qty = plan + allowance_percentage / 100 * plan
			precision = d.precision("completed_qty")
			qty = flt(flt(d.completed_qty, precision) + flt(d.process_loss_qty, precision), precision)
			if not qty:
				d.status = "Pending"
			elif qty < flt(plan, precision):
				d.status = "Work in Progress"
			elif qty == flt(plan, precision):
				d.status = "Completed"
			elif qty <= flt(max_allowed_qty, precision) or d.name != operation_id:
				d.status = "Completed"
			else:
				frappe.throw(_("Completed Qty cannot be greater than 'Qty to Manufacture'"))

	def set_actual_dates(self):
		if self.get("operations"):
			actual_start_dates = [d.actual_start_time for d in self.get("operations") if d.actual_start_time]
			if actual_start_dates:
				self.actual_start_date = min(actual_start_dates)

			actual_end_dates = [d.actual_end_time for d in self.get("operations") if d.actual_end_time]
			if actual_end_dates:
				self.actual_end_date = max(actual_end_dates)
		else:
			stock_entry = frappe.qb.DocType("Stock Entry")
			posting_datetime = CombineDatetime(stock_entry.posting_date, stock_entry.posting_time)
			data = (
				frappe.qb.from_(stock_entry)
				.select(Min(posting_datetime).as_("start_date"), Max(posting_datetime).as_("end_date"))
				.where(
					(stock_entry.work_order == self.name)
					& (stock_entry.docstatus == 1)
					& (stock_entry.purpose.isin(["Material Transfer for Manufacture", "Manufacture"]))
				)
				.run(as_dict=True)
			)
			self.db_set(
				{
					"actual_start_date": data[0].start_date,
					"actual_end_date": data[0].end_date if self.status == "Completed" else None,
				}
			)

		self.set_lead_time()

	def set_lead_time(self):
		if self.actual_start_date and self.actual_end_date:
			self.lead_time = flt(time_diff_in_hours(self.actual_end_date, self.actual_start_date) * 60)

	def validate_production_item(self):
		if frappe.get_cached_value("Item", self.production_item, "has_variants"):
			frappe.throw(_("Work Order cannot be raised against a Item Template"), ItemHasVariantError)

		if self.production_item:
			validate_end_of_life(self.production_item)

	def validate_qty(self):
		if not self.qty > 0:
			frappe.throw(_("Quantity to Manufacture must be greater than 0."))

		if (
			self.stock_uom
			and frappe.get_cached_value("UOM", self.stock_uom, "must_be_whole_number")
			and abs(cint(self.qty) - flt(self.qty, self.precision("qty"))) > 0.0000001
		):
			frappe.throw(
				_(
					"Qty To Manufacture ({0}) cannot be a fraction for the UOM {2}. To allow this, disable '{1}' in the UOM {2}."
				).format(
					flt(self.qty, self.precision("qty")),
					frappe.bold(_("Must be Whole Number")),
					frappe.bold(self.stock_uom),
				),
			)

		if self.production_plan and self.production_plan_item and not self.production_plan_sub_assembly_item:
			qty_dict = frappe.db.get_value(
				"Production Plan Item", self.production_plan_item, ["planned_qty", "ordered_qty"], as_dict=1
			)

			if not qty_dict:
				return

			allowance_qty = (
				flt(
					frappe.db.get_single_value(
						"Manufacturing Settings", "overproduction_percentage_for_work_order"
					)
				)
				/ 100
				* qty_dict.get("planned_qty", 0)
			)

			max_qty = qty_dict.get("planned_qty", 0) + allowance_qty - qty_dict.get("ordered_qty", 0)

			if not max_qty > 0:
				frappe.throw(
					_("Cannot produce more item for {0}").format(self.production_item), OverProductionError
				)
			elif self.qty > max_qty:
				frappe.throw(
					_("Cannot produce more than {0} items for {1}").format(max_qty, self.production_item),
					OverProductionError,
				)

	def validate_transfer_against(self):
		if not self.docstatus == 1:
			# let user configure operations until they're ready to submit
			return
		if not self.operations:
			self.transfer_material_against = "Work Order"
		if not self.transfer_material_against:
			frappe.throw(
				_("Setting {0} is required").format(_(self.meta.get_label("transfer_material_against"))),
				title=_("Missing value"),
			)

	def get_operation_plan_quantity(self, row):
		if not self.get("approval_requested_by"):
			return self.qty
		# Only empty legacy values retain the approved parent plan; invalid input never falls back.
		value = row.get("report_plan_qty")
		return validate_quantity_input(self.qty if value in (None, "") else value, "任务计划数量")

	def validate_production_plan_rows(self):
		if self.get("approval_requested_by") and self.docstatus == 0 and self.get("workflow_state") in ("草稿", "退回"):
			for table in ("operations", "required_items"):
				validate_child_table_identity(self, table)
			for row in self.required_items:
				row.required_qty = validate_quantity_input(row.required_qty, "物料需求数量", allow_zero=True)
				unit = frappe.get_cached_value("Item", row.item_code, "stock_uom")
				if not unit or row.stock_uom not in (None, "", unit):
					frappe.throw("本单用料必须使用该物料的库存单位，请核对物料和单位")
				row.stock_uom = unit
				for field in ("transferred_qty", "returned_qty", "consumed_qty"):
					value = row.get(field)
					if value not in (None, "") and validate_quantity_input(value, "库存生效数量", allow_zero=True):
						frappe.throw("草稿用料不能填写已领、已退或实际消耗，请通过库存单据形成事实", frappe.PermissionError)

	def validate_operations(self):
		self.validate_production_plan_rows()
		for d in self.operations:
			if self.get("approval_requested_by"):
				editable = self.docstatus == 0 and self.get("workflow_state") in ("草稿", "退回")
				if editable and d.get("report_plan_qty") in (None, ""):
					d.report_plan_qty = str(self.qty)
				self.get_operation_plan_quantity(d)
				if editable and (d.status not in (None, "", "Pending") or d.actual_start_time or d.actual_end_time
					or any(d.get(f) for f in ("completed_qty", "process_loss_qty", "actual_operation_time", "actual_operating_cost"))):
					frappe.throw("草稿任务不能填写生产实绩，请通过正常报工形成事实", frappe.PermissionError)
			if not d.batch_size or d.batch_size <= 0:
				d.batch_size = 1

			if d.time_in_mins <= 0:
				frappe.throw(_("Operation Time must be greater than 0 for Operation {0}").format(d.operation))

	def update_required_items(self):
		"""
		update bin reserved_qty_for_production
		called from Stock Entry for production, after submit, cancel
		"""
		# calculate consumed qty based on submitted stock entries
		self.update_consumed_qty_for_required_items()

		if self.docstatus == 1:
			# calculate transferred qty based on submitted stock entries
			self.update_transferred_qty_for_required_items()
			self.update_returned_qty()

			# update in bin
			self.update_reserved_qty_for_production()

	def update_reserved_qty_for_production(self, items=None):
		"""update reserved_qty_for_production in bins"""
		for d in self.required_items:
			if d.source_warehouse:
				stock_bin = get_bin(d.item_code, d.source_warehouse)
				stock_bin.update_reserved_qty_for_production()

	@frappe.whitelist()
	def get_items_and_operations_from_bom(self):
		if not self.fg_warehouse:
			self.fg_warehouse = self.get_default_fg_warehouse()

		self.set_required_items()
		self.set_work_order_operations()

		return check_if_scrap_warehouse_mandatory(self.bom_no)

	def set_available_qty(self):
		for d in self.get("required_items"):
			if d.source_warehouse:
				d.available_qty_at_source_warehouse = get_latest_stock_qty(d.item_code, d.source_warehouse)

			if self.wip_warehouse:
				d.available_qty_at_wip_warehouse = get_latest_stock_qty(d.item_code, self.wip_warehouse)

	def set_required_items(self, reset_only_qty=False):
		"""set required_items for production to keep track of reserved qty"""
		if not reset_only_qty:
			self.required_items = []

		operation = None
		if self.get("operations") and len(self.operations) == 1:
			operation = self.operations[0].operation

		if self.bom_no and self.qty:
			item_dict = get_bom_items_as_dict(
				self.bom_no, self.company, qty=self.qty, fetch_exploded=self.use_multi_level_bom
			)

			if reset_only_qty:
				for d in self.get("required_items"):
					if item_dict.get(d.item_code):
						d.required_qty = item_dict.get(d.item_code).get("qty")

					if not d.operation:
						d.operation = operation
			else:
				for item in sorted(item_dict.values(), key=lambda d: d["idx"] or float("inf")):
					self.append(
						"required_items",
						{
							"rate": item.rate,
							"amount": item.rate * item.qty,
							"operation": item.operation or operation,
							"item_code": item.item_code,
							"item_name": item.item_name,
							"stock_uom": item.stock_uom,
							"description": item.description,
							"allow_alternative_item": item.allow_alternative_item,
							"required_qty": item.qty,
							"source_warehouse": item.source_warehouse
							or item.default_warehouse
							or self.source_warehouse
							or get_item_group_defaults(item.item_code, self.company).get("default_warehouse"),
							"include_item_in_manufacturing": item.include_item_in_manufacturing,
						},
					)

					if not self.project:
						self.project = item.get("project")

			self.set_available_qty()

	def update_transferred_qty_for_required_items(self):
		ste = frappe.qb.DocType("Stock Entry")
		ste_child = frappe.qb.DocType("Stock Entry Detail")

		query = (
			frappe.qb.from_(ste)
			.inner_join(ste_child)
			.on(ste_child.parent == ste.name)
			.select(
				ste_child.item_code,
				ste_child.original_item,
				fn.Sum(ste_child.transfer_qty).as_("qty"),
			)
			.where(
				(ste.docstatus == 1)
				& (ste.work_order == self.name)
				& (ste.purpose == "Material Transfer for Manufacture")
				& (ste.is_return == 0)
			)
			.groupby(ste_child.item_code, ste_child.original_item)
		)

		data = query.run(as_dict=1) or []
		# An item's own transfer and its substitutes both key to the original item, so sum them.
		transferred_items = frappe._dict()
		for d in data:
			key = d.original_item or d.item_code
			transferred_items[key] = flt(transferred_items.get(key)) + flt(d.qty)

		for row in self.required_items:
			row.db_set(
				"transferred_qty", (transferred_items.get(row.item_code) or 0.0), update_modified=False
			)

		self.recompute_material_transferred_for_manufacturing(transferred_items)

	def recompute_material_transferred_for_manufacturing(self, transferred_items):
		"""Set material_transferred_for_manufacturing based on actual item-level transfers, not fg_completed_qty."""
		# Job Card transfers use the minimum completed quantity across operations.
		if self.operations and self.transfer_material_against == "Job Card":
			return

		# When fg_completed_qty > 0 (direct stock entries, excess transfer), preserve the
		# SUM(fg_completed_qty) approach so excess-transfer tracking works correctly.
		sum_fg_completed_qty = self.get_transferred_or_manufactured_qty("Material Transfer for Manufacture")
		if sum_fg_completed_qty:
			self.db_set("material_transferred_for_manufacturing", sum_fg_completed_qty)
			return

		# Pick list flow sets fg_completed_qty=0; use min-fraction of actual item transfers
		# so partial availability does not prematurely mark the work order as fully transferred.
		required_by_item = {}
		for row in self.required_items:
			if not row.include_item_in_manufacturing or flt(row.required_qty) <= 0:
				continue
			required_by_item[row.item_code] = required_by_item.get(row.item_code, 0.0) + flt(row.required_qty)

		if not required_by_item:
			return

		min_fraction = min(
			flt(transferred_items.get(item_code) or 0) / required_qty
			for item_code, required_qty in required_by_item.items()
		)
		min_fraction = min(min_fraction, 1.0)
		material_transferred = min_fraction * flt(self.qty)
		self.db_set("material_transferred_for_manufacturing", material_transferred)

	def update_returned_qty(self):
		ste = frappe.qb.DocType("Stock Entry")
		ste_child = frappe.qb.DocType("Stock Entry Detail")

		query = (
			frappe.qb.from_(ste)
			.inner_join(ste_child)
			.on(ste_child.parent == ste.name)
			.select(
				ste_child.item_code,
				ste_child.original_item,
				fn.Sum(ste_child.transfer_qty).as_("qty"),
			)
			.where(
				(ste.docstatus == 1)
				& (ste.work_order == self.name)
				& (ste.purpose == "Material Transfer for Manufacture")
				& (ste.is_return == 1)
			)
			.groupby(ste_child.item_code)
		)

		data = query.run(as_dict=1) or []
		returned_dict = frappe._dict({d.original_item or d.item_code: d.qty for d in data})

		for row in self.required_items:
			row.db_set("returned_qty", (returned_dict.get(row.item_code) or 0.0), update_modified=False)

	def update_consumed_qty_for_required_items(self):
		"""
		Update consumed qty from submitted stock entries
		against a work order for each stock item
		"""

		for item in self.required_items:
			consumed_qty = frappe.db.sql(
				"""
				SELECT
					SUM(detail.transfer_qty)
				FROM
					`tabStock Entry` entry,
					`tabStock Entry Detail` detail
				WHERE
					entry.work_order = %(name)s
						AND (entry.purpose = "Material Consumption for Manufacture"
							OR entry.purpose = "Manufacture")
						AND entry.docstatus = 1
						AND detail.parent = entry.name
						AND detail.s_warehouse IS NOT null
						AND (detail.original_item = %(item)s
							OR (IFNULL(detail.original_item, '') = '' AND detail.item_code = %(item)s))
				""",
				{"name": self.name, "item": item.item_code},
			)[0][0]

			item.db_set("consumed_qty", flt(consumed_qty), update_modified=False)

	@frappe.whitelist()
	def make_bom(self):
		data = frappe.db.sql(
			""" select sed.item_code, sed.qty, sed.s_warehouse
			from `tabStock Entry Detail` sed, `tabStock Entry` se
			where se.name = sed.parent and se.purpose = 'Manufacture'
			and (sed.t_warehouse is null or sed.t_warehouse = '') and se.docstatus = 1
			and se.work_order = %s""",
			(self.name),
			as_dict=1,
		)

		bom = frappe.new_doc("BOM")
		bom.item = self.production_item
		bom.conversion_rate = 1

		for d in data:
			bom.append("items", {"item_code": d.item_code, "qty": d.qty, "source_warehouse": d.s_warehouse})

		if self.operations:
			bom.set("operations", self.operations)
			bom.with_operations = 1

		bom.set_bom_material_details()
		return bom


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bom_operations(doctype, txt, searchfield, start, page_len, filters):
	parent = filters.get("parent")
	parenttype = filters.get("parenttype") or "BOM"
	if not parent or not frappe.db.exists(parenttype, parent):
		return []

	ptype = "select" if frappe.only_has_select_perm(parenttype) else "read"
	frappe.has_permission(parenttype, ptype, doc=parent, throw=True)

	if txt:
		filters["operation"] = ("like", "%%%s%%" % txt)

	return frappe.get_all("BOM Operation", filters=filters, fields=["operation"], as_list=1)


@frappe.whitelist()
def get_item_details(item, project=None, skip_bom_info=False, throw=True):
	res = frappe.db.sql(
		"""
		select stock_uom, description, item_name, allow_alternative_item,
			include_item_in_manufacturing
		from `tabItem`
		where disabled=0
			and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %s)
			and name=%s
	""",
		(nowdate(), item),
		as_dict=1,
	)

	if not res:
		return {}

	res = res[0]
	if skip_bom_info:
		return res

	filters = {"item": item, "is_default": 1, "docstatus": 1}

	if project:
		filters = {"item": item, "project": project}

	res["bom_no"] = frappe.db.get_value("BOM", filters=filters)

	if not res["bom_no"]:
		variant_of = frappe.db.get_value("Item", item, "variant_of")

		if variant_of:
			res["bom_no"] = frappe.db.get_value("BOM", filters={"item": variant_of, "is_default": 1})

	if not res["bom_no"]:
		if project:
			res = get_item_details(item, throw=throw)
			frappe.msgprint(
				_("Default BOM not found for Item {0} and Project {1}").format(item, project), alert=1
			)
		else:
			msg = _("Default BOM for {0} not found").format(item)
			frappe.msgprint(msg, raise_exception=throw, indicator="yellow", alert=(not throw))

			return res

	bom_data = frappe.db.get_value(
		"BOM",
		res["bom_no"],
		["project", "allow_alternative_item", "transfer_material_against", "item_name"],
		as_dict=1,
	)

	res["project"] = project or bom_data.pop("project")
	res.update(bom_data)
	res.update(check_if_scrap_warehouse_mandatory(res["bom_no"]))

	return res


@frappe.whitelist()
def make_work_order(
	bom_no: str,
	item: str,
	qty: float = 0,
	company: str | None = None,
	project: str | None = None,
	variant_items: str | list | None = None,
	use_multi_level_bom: bool | None = None,
):
	from erpnext import get_default_company

	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	item_details = get_item_details(item, project)

	# selected BOM already belongs to this variant — keep it
	if frappe.db.get_value("Item", item, "variant_of") and frappe.db.get_value("BOM", bom_no, "item") != item:
		if variant_bom := frappe.db.get_value(
			"BOM",
			{"item": item, "is_default": 1, "docstatus": 1},
		):
			bom_no = variant_bom

	wo_doc = frappe.new_doc("Work Order")
	wo_doc.production_item = item
	wo_doc.company = company or get_default_company()
	wo_doc.update(item_details)
	wo_doc.bom_no = bom_no
	wo_doc.use_multi_level_bom = cint(use_multi_level_bom)

	if flt(qty) > 0:
		wo_doc.qty = flt(qty)
		wo_doc.get_items_and_operations_from_bom()

	if variant_items and not wo_doc.use_multi_level_bom:
		add_variant_item(variant_items, wo_doc, bom_no, "required_items")

	return wo_doc


def add_variant_item(variant_items, wo_doc, bom_no, table_name="items"):
	if isinstance(variant_items, str):
		variant_items = json.loads(variant_items)

	for item in variant_items:
		args = frappe._dict(
			{
				"item_code": item.get("variant_item_code"),
				"required_qty": item.get("qty"),
				"qty": item.get("qty"),  # for bom
				"source_warehouse": item.get("source_warehouse"),
				"operation": item.get("operation"),
			}
		)

		bom_doc = frappe.get_cached_doc("BOM", bom_no)
		item_data = get_item_details(args.item_code, skip_bom_info=True)
		args.update(item_data)

		args["rate"] = get_bom_item_rate(
			{
				"company": wo_doc.company,
				"item_code": args.get("item_code"),
				"qty": args.get("required_qty"),
				"uom": args.get("stock_uom"),
				"stock_uom": args.get("stock_uom"),
				"conversion_factor": 1,
			},
			bom_doc,
		)

		if not args.source_warehouse:
			args["source_warehouse"] = get_item_defaults(
				item.get("variant_item_code"), wo_doc.company
			).default_warehouse

		args["amount"] = flt(args.get("required_qty")) * flt(args.get("rate"))
		args["uom"] = item_data.stock_uom

		existing_row = (
			get_template_rm_item(wo_doc, item.get("item_code")) if table_name == "required_items" else None
		)
		if existing_row:
			existing_row.update(args)
		else:
			wo_doc.append(table_name, args)


def get_template_rm_item(wo_doc, item_code):
	for row in wo_doc.required_items:
		if row.item_code == item_code:
			return row


@frappe.whitelist()
def check_if_scrap_warehouse_mandatory(bom_no):
	res = {"set_scrap_wh_mandatory": False}
	if bom_no:
		bom = frappe.get_doc("BOM", bom_no)

		if len(bom.scrap_items) > 0:
			res["set_scrap_wh_mandatory"] = True

	return res


@frappe.whitelist()
def set_work_order_ops(name):
	po = frappe.get_doc("Work Order", name)
	po.set_work_order_operations()
	po.save()


@frappe.whitelist()
def make_stock_entry(
	work_order_id: str,
	purpose: str,
	qty: float | None = None,
	target_warehouse: str | None = None,
	source_stock_entry: str | None = None,
):
	work_order = frappe.get_doc("Work Order", work_order_id)
	work_order.check_permission("read")
	frappe.has_permission("Stock Entry", "create", throw=True)
	if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
		wip_warehouse = work_order.wip_warehouse
	else:
		wip_warehouse = None

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.work_order = work_order_id
	stock_entry.company = work_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = work_order.bom_no
	stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
	# accept 0 qty as well
	stock_entry.fg_completed_qty = (
		qty if qty is not None else (flt(work_order.qty) - flt(work_order.produced_qty))
	)

	if work_order.bom_no:
		stock_entry.inspection_required = frappe.db.get_value("BOM", work_order.bom_no, "inspection_required")

	if purpose == "Material Transfer for Manufacture":
		stock_entry.to_warehouse = wip_warehouse
		stock_entry.project = work_order.project
	else:
		stock_entry.from_warehouse = (
			work_order.source_warehouse
			if work_order.skip_transfer and not work_order.from_wip_warehouse
			else wip_warehouse
		)
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.project = work_order.project

	if purpose == "Disassemble":
		stock_entry.from_warehouse = work_order.fg_warehouse
		stock_entry.to_warehouse = target_warehouse or work_order.source_warehouse
		if source_stock_entry:
			stock_entry.source_stock_entry = source_stock_entry

	stock_entry.set_stock_entry_type()
	stock_entry.get_items()

	if purpose != "Disassemble":
		stock_entry.set_serial_no_batch_for_finished_good()

	return stock_entry.as_dict()


@frappe.whitelist()
def get_disassembly_available_qty(stock_entry_name: str, current_se_name: str | None = None) -> float:
	se = frappe.db.get_value("Stock Entry", stock_entry_name, ["fg_completed_qty"], as_dict=True)
	if not se:
		return 0.0

	filters = {
		"source_stock_entry": stock_entry_name,
		"purpose": "Disassemble",
		"docstatus": 1,
	}

	if current_se_name:
		filters["name"] = ("!=", current_se_name)

	already_disassembled = flt(
		frappe.db.get_value("Stock Entry", filters, "sum(fg_completed_qty)", order_by=None)
	)

	return flt(
		flt(se.fg_completed_qty) - already_disassembled,
		frappe.get_precision("Stock Entry", "fg_completed_qty"),
	)


@frappe.whitelist()
def get_default_warehouse():
	doc = frappe.get_cached_doc("Manufacturing Settings")

	return {
		"wip_warehouse": doc.default_wip_warehouse,
		"fg_warehouse": doc.default_fg_warehouse,
		"scrap_warehouse": doc.default_scrap_warehouse,
	}


@frappe.whitelist(methods=["POST"])
def stop_unstop(work_order, status):
	"""Called from client side on Stop/Unstop event"""

	frappe.has_permission("Work Order", "write", throw=True)

	# the check above is doctype level and never consults User Permissions, so on its own it lets
	# a caller restricted to one company stop another company's orders
	pro_order = frappe.get_doc("Work Order", work_order)
	pro_order.check_permission("write")
	if pro_order.get("approval_requested_by"):
		context = getattr(frappe.local, "production_approval_context", None)
		if not (context and context.name == pro_order.name and context.action == "停止执行"
			and context.user == frappe.session.user and status == "Stopped"):
			frappe.throw("审批工单必须由厂长通过带版本和原因的停止动作处理，不能直接停止或恢复", frappe.PermissionError)

	if pro_order.status == "Closed":
		frappe.throw(_("Closed Work Order can not be stopped or Re-opened"))

	pro_order.update_status(status)
	pro_order.update_planned_qty()
	frappe.msgprint("工单已停止新增执行" if pro_order.get("approval_requested_by") else _("Work Order has been {0}").format(status))
	pro_order.notify_update()

	return pro_order.status


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def query_sales_order(doctype, txt, searchfield, start, page_len, filters) -> list[str]:
	return frappe.get_list(
		"Sales Order",
		fields=["name"],
		filters=[
			["Sales Order", "docstatus", "=", 1],
		],
		or_filters=[
			["Sales Order Item", "item_code", "=", filters.get("production_item")],
			["Packed Item", "item_code", "=", filters.get("production_item")],
		],
		as_list=True,
		distinct=True,
	)


@frappe.whitelist()
def make_job_card(work_order, operations):
	if isinstance(operations, str):
		operations = json.loads(operations)

	work_order = frappe.get_doc("Work Order", work_order)
	for row in operations:
		row = frappe._dict(row)
		validate_operation_data(row)
		qty = row.get("qty")
		while qty > 0:
			qty = split_qty_based_on_batch_size(work_order, row, qty)
			if row.job_card_qty > 0:
				create_job_card(work_order, row, auto_create=True)


def _check_production_close(order, expected_modified):
	order.check_permission("read")
	order.check_permission("write")
	if not order.get("approval_requested_by") or "生产工单签批" not in frappe.get_roles():
		frappe.throw("仅有权厂长可收尾计时或人工结束审批工单", frappe.PermissionError)
	_check_production_approval_scope(order, team_required=False)
	validate_production_execution_state(order, finishing_execution=True)
	if order.status not in ("Not Started", "In Process", "Stopped", "Completed"):
		frappe.throw("当前工单状态不能人工结束")
	if not expected_modified or get_datetime(expected_modified) != get_datetime(order.modified):
		frappe.throw("工单已变化，请刷新并重新核对结束依据", frappe.TimestampMismatchError)


def _production_open_timers(order, *, for_update=False):
	# Object authorization belongs to the caller. A permission-filtered list must not hide activity.
	cards = frappe.db.get_values("Job Card", {"work_order": order.name, "docstatus": ["!=", 2]},
		["name", "modified", "docstatus", "report_request_id", "started_time"],
		as_dict=True, order_by="name", for_update=for_update)
	active = []
	for card in cards:
		logs = frappe.db.get_values("Job Card Time Log", {"parent": card.name, "parenttype": "Job Card"},
			["name", "from_time", "to_time", "operation", "employee", "completed_qty"],
			as_dict=True, order_by="idx", for_update=for_update)
		card.open_logs = [row for row in logs if row.from_time and not row.to_time]
		if card.started_time or card.open_logs:
			active.append(card)
	fingerprint = hashlib.sha256(frappe.as_json({"work_order": order.name, "timers": active}).encode()).hexdigest()
	return active, fingerprint


def _production_close_snapshot(order, timers, fingerprint):
	from erpnext.manufacturing.doctype.job_card.job_card import calculate_report_metrics

	operations = []
	for row in order.operations:
		plan = order.get_operation_plan_quantity(row)
		remaining = calculate_report_metrics(plan_quantity=plan, good_quantity=row.completed_qty,
			bad_quantity=row.process_loss_qty, effective_seconds=0)["unfinished_quantity"]
		operations.append({"operation_id": row.name, "operation": row.operation, "plan": plan,
			"good": row.completed_qty, "bad": row.process_loss_qty, "unfinished": remaining})
	stock_remaining = calculate_report_metrics(plan_quantity=order.qty, good_quantity=order.produced_qty,
		bad_quantity=0, effective_seconds=0)["unfinished_quantity"]
	return {"work_order": order.name, "modified": str(order.modified), "unit": order.stock_uom,
		"plan": order.qty, "produced": order.produced_qty, "stock_unfinished": stock_remaining,
		"operations": operations, "open_timers": timers, "timer_fingerprint": fingerprint}


@frappe.whitelist()
def preview_production_close(work_order, expected_modified):
	order = frappe.get_doc("Work Order", work_order)
	_check_production_close(order, expected_modified)
	timers, fingerprint = _production_open_timers(order)
	for card in timers:
		frappe.get_doc("Job Card", card.name).check_permission("read")
	return _production_close_snapshot(order, timers, fingerprint)


@frappe.whitelist(methods=["POST"])
def finish_production_timers(work_order, expected_modified, timer_fingerprint, end_time):
	from html import escape

	from erpnext.manufacturing.doctype.job_card.job_card import _report_datetime

	order = frappe.get_doc("Work Order", work_order, for_update=True)
	_check_production_close(order, expected_modified)
	timers, fingerprint = _production_open_timers(order, for_update=True)
	if not timer_fingerprint or timer_fingerprint != fingerprint:
		frappe.throw("活动计时已变化，请重新预览后收尾", frappe.TimestampMismatchError)
	if not timers:
		frappe.throw("没有需要收尾的活动计时，请刷新核对")
	end = _report_datetime(end_time, "实际结束时间").replace(tzinfo=None)
	if end > get_datetime(now()):
		frappe.throw("实际结束时间不能晚于当前时间")
	cards = []
	for timer in timers:
		card = frappe.get_doc("Job Card", timer.name, for_update=True)
		card.check_permission("read")
		card.check_permission("write")
		if card.work_order != order.name or card.docstatus != 0 or card.get("report_request_id"):
			frappe.throw("已提交或已生效报工的活动计时不能改写，请保留原记录处理异常")
		open_logs = [row for row in card.time_logs if row.from_time and not row.to_time]
		if not open_logs:
			frappe.throw("计时状态与原时段不一致，请先核对异常，不能推测开始时间")
		if any(end < get_datetime(row.from_time) for row in open_logs):
			frappe.throw("实际结束时间不能早于任何活动计时的开始时间")
		cards.append((card, open_logs))
	previous = getattr(frappe.local, "production_timer_finish_context", None)
	try:
		for card, open_logs in cards:
			for row in open_logs:
				row.to_time = end
			card.started_time = None
			card.current_time = (end - get_datetime(open_logs[-1].from_time)).total_seconds()
			card.status = "On Hold"
			# Only this already-authorized instance can finish existing time after a stop.
			frappe.local.production_timer_finish_context = frappe._dict(
				card=card, work_order=order.name, user=frappe.session.user)
			card.save()
	finally:
		frappe.local.production_timer_finish_context = previous
	order.add_comment("Comment", "活动计时人工收尾；操作者：{0}；实际结束时间：{1}；作业卡：{2}；未确认产量。".format(
		escape(frappe.session.user), escape(str(end)), escape("、".join(card.name for card, _ in cards))))
	timers, fingerprint = _production_open_timers(order, for_update=True)
	return _production_close_snapshot(order, timers, fingerprint)


@frappe.whitelist(methods=["POST"])
def close_work_order(work_order, status, expected_modified=None, reason=None):
	from html import escape

	frappe.has_permission("Work Order", "write", throw=True)
	work_order = frappe.get_doc("Work Order", work_order, for_update=True)
	work_order.check_permission("write")
	approval_order = bool(work_order.get("approval_requested_by"))
	if approval_order:
		if status != "Closed":
			frappe.throw("审批工单不能通过结束接口恢复执行，仅厂长可结束", frappe.PermissionError)
		_check_production_close(work_order, expected_modified)
		if not isinstance(reason, str) or not reason.strip():
			frappe.throw("人工结束必须填写原因")
		timers, fingerprint = _production_open_timers(work_order, for_update=True)
		if timers:
			frappe.throw("仍有活动计时，请先核对实际结束时间并收尾，不能自动确认产量")
		snapshot = _production_close_snapshot(work_order, timers, fingerprint)
		snapshot.update(user=frappe.session.user, closed_at=now(), reason=reason.strip())
	elif work_order.get("operations"):
		job_cards = frappe.get_list("Job Card", filters={"work_order": work_order.name,
			"status": "Work In Progress", "docstatus": 1}, pluck="name")
		if job_cards:
			frappe.throw(_("Can not close Work Order. Since {0} Job Cards are in Work In Progress state.").format(
				", ".join(job_cards)))
	work_order.update_status(status)
	work_order.on_close_or_cancel()
	if approval_order:
		record = {"工单": snapshot["work_order"], "依据版本": snapshot["modified"], "单位": snapshot["unit"],
			"操作者": snapshot["user"], "人工结束时间": snapshot["closed_at"], "结束原因": snapshot["reason"],
			"计划数量": snapshot["plan"], "成品入库数量": snapshot["produced"], "未入库差额": snapshot["stock_unfinished"],
			"工序差额": [{"工序行": row["operation_id"], "工序": row["operation"], "计划": row["plan"],
				"良品": row["good"], "不良": row["bad"], "未清数量": row["unfinished"]} for row in snapshot["operations"]]}
		comment = work_order.add_comment("Comment", "<p>人工结束工单：{0}</p><pre>{1}</pre>".format(
			escape(snapshot["reason"]), escape(frappe.as_json(record, ensure_ascii=False))))
		work_order.notify_update()
		return {"status": work_order.status, "comment": comment.name}
	frappe.msgprint(_("Work Order has been {0}").format(status))
	work_order.notify_update()
	return work_order.status


def split_qty_based_on_batch_size(wo_doc, row, qty):
	if not cint(frappe.db.get_value("Operation", row.operation, "create_job_card_based_on_batch_size")):
		row.batch_size = row.get("qty") or wo_doc.qty

	row.job_card_qty = row.batch_size
	if row.batch_size and qty >= row.batch_size:
		qty -= row.batch_size
	elif qty > 0:
		row.job_card_qty = qty
		qty = 0

	get_serial_nos_for_job_card(row, wo_doc)

	return qty


def get_serial_nos_for_job_card(row, wo_doc):
	if not wo_doc.has_serial_no:
		return

	serial_nos = get_serial_nos_for_work_order(wo_doc.name, wo_doc.production_item)
	used_serial_nos = []
	for d in frappe.get_all(
		"Job Card",
		fields=["serial_no"],
		filters={"docstatus": ("<", 2), "work_order": wo_doc.name, "operation_id": row.name},
	):
		used_serial_nos.extend(get_serial_nos(d.serial_no))

	serial_nos = sorted(list(set(serial_nos) - set(used_serial_nos)))
	row.serial_no = "\n".join(serial_nos[0 : cint(row.job_card_qty)])


def get_serial_nos_for_work_order(work_order, production_item):
	serial_nos = []
	for d in frappe.get_all(
		"Serial No",
		fields=["name"],
		filters={
			"work_order": work_order,
			"item_code": production_item,
		},
	):
		serial_nos.append(d.name)

	return serial_nos


def validate_operation_data(row):
	if flt(row.get("qty")) <= 0:
		frappe.throw(
			_("Quantity to Manufacture can not be zero for the operation {0}").format(
				frappe.bold(row.get("operation"))
			)
		)

	if flt(row.get("qty")) > flt(row.get("pending_qty")):
		frappe.throw(
			_("For operation {0}: Quantity ({1}) can not be greter than pending quantity({2})").format(
				frappe.bold(row.get("operation")),
				frappe.bold(row.get("qty")),
				frappe.bold(row.get("pending_qty")),
			)
		)


def create_job_card(work_order, row, enable_capacity_planning=False, auto_create=False):
	doc = frappe.new_doc("Job Card")
	doc.update(
		{
			"work_order": work_order.name,
			"workstation_type": row.get("workstation_type"),
			"operation": row.get("operation"),
			"workstation": row.get("workstation"),
			"posting_date": nowdate(),
			"for_quantity": row.job_card_qty or work_order.get_operation_plan_quantity(row),
			"operation_id": row.get("name"),
			"bom_no": row.get("bom") or work_order.bom_no,
			"project": work_order.project,
			"company": work_order.company,
			"sequence_id": row.get("sequence_id"),
			"wip_warehouse": work_order.wip_warehouse or row.get("wip_warehouse")
			if not work_order.skip_transfer or work_order.from_wip_warehouse
			else work_order.source_warehouse or row.get("source_warehouse"),
			"hour_rate": row.get("hour_rate"),
			"serial_no": row.get("serial_no"),
		}
	)

	if work_order.transfer_material_against == "Job Card" and not work_order.skip_transfer:
		doc.get_required_items()

	if auto_create:
		doc.flags.ignore_mandatory = True
		if enable_capacity_planning:
			doc.schedule_time_logs(row)

		doc.insert()
		frappe.msgprint(_("Job card {0} created").format(get_link_to_form("Job Card", doc.name)), alert=True)

	if enable_capacity_planning:
		# automatically added scheduling rows shouldn't change status to WIP
		doc.db_set("status", "Open")

	return doc


def get_work_order_operation_data(work_order, operation, workstation):
	for d in work_order.operations:
		if d.operation == operation and d.workstation == workstation:
			return d


@frappe.whitelist()
def create_pick_list(source_name, target_doc=None, for_qty=None):
	for_qty = for_qty or json.loads(target_doc).get("for_qty")
	max_finished_goods_qty = frappe.db.get_value("Work Order", source_name, "qty")

	def update_item_quantity(source, target, source_parent):
		pending_to_issue = flt(source.required_qty) - flt(source.transferred_qty)
		desire_to_transfer = flt(source.required_qty) / max_finished_goods_qty * flt(for_qty)

		qty = 0
		if desire_to_transfer <= pending_to_issue:
			qty = desire_to_transfer
		elif pending_to_issue > 0:
			qty = pending_to_issue

		if qty:
			target.qty = qty
			target.stock_qty = qty
			target.uom = frappe.get_value("Item", source.item_code, "stock_uom")
			target.stock_uom = target.uom
			target.conversion_factor = 1
		else:
			target.delete()

	doc = get_mapped_doc(
		"Work Order",
		source_name,
		{
			"Work Order": {"doctype": "Pick List", "validation": {"docstatus": ["=", 1]}},
			"Work Order Item": {
				"doctype": "Pick List Item",
				"postprocess": update_item_quantity,
				"condition": lambda doc: abs(doc.transferred_qty) < abs(doc.required_qty),
			},
		},
		target_doc,
	)

	doc.purpose = "Material Transfer for Manufacture"
	doc.for_qty = for_qty

	doc.set_item_locations()

	return doc


def get_reserved_qty_for_production(
	item_code: str,
	warehouse: str,
	non_completed_production_plans: list | None = None,
	check_production_plan: bool = False,
) -> float:
	"""Get total reserved quantity for any item in specified warehouse"""
	wo = frappe.qb.DocType("Work Order")
	wo_item = frappe.qb.DocType("Work Order Item")

	if check_production_plan:
		qty_field = wo_item.required_qty
	else:
		qty_field = Case()
		qty_field = qty_field.when(
			((wo.skip_transfer == 0) & (wo_item.transferred_qty > wo_item.required_qty)), 0.0
		)
		qty_field = qty_field.when(wo.skip_transfer == 0, wo_item.required_qty - wo_item.transferred_qty)
		qty_field = qty_field.else_(wo_item.required_qty - wo_item.consumed_qty)

	query = (
		frappe.qb.from_(wo)
		.from_(wo_item)
		.select(Sum(qty_field))
		.where(
			(wo_item.item_code == item_code)
			& (wo_item.parent == wo.name)
			& (wo.docstatus == 1)
			& (wo_item.source_warehouse == warehouse)
		)
	)

	if check_production_plan:
		query = query.where(wo.production_plan.isnotnull())
	else:
		query = query.where(
			(wo.status.notin(["Stopped", "Completed", "Closed"]))
			& (
				(wo_item.required_qty > wo_item.transferred_qty)
				| (wo_item.required_qty > wo_item.consumed_qty)
			)
		)

	if non_completed_production_plans:
		query = query.where(wo.production_plan.isin(non_completed_production_plans))

	return query.run()[0][0] or 0.0


@frappe.whitelist()
def make_stock_return_entry(work_order):
	wo_doc = frappe.get_doc("Work Order", work_order)
	wo_doc.check_permission("read")
	frappe.has_permission("Stock Entry", "create", throw=True)
	check_production_execution(work_order, material_return=True)

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.company = wo_doc.company
	stock_entry.from_bom = 1
	stock_entry.is_return = 1
	stock_entry.work_order = work_order
	stock_entry.purpose = "Material Transfer for Manufacture"
	stock_entry.bom_no = wo_doc.bom_no
	stock_entry.add_transfered_raw_materials_in_items()
	if not stock_entry.items:
		frappe.throw("本工单没有可退数量，请核对已领、已退和实际消耗")
	stock_entry.set_stock_entry_type()

	return stock_entry


@frappe.request_cache
def get_hour_rate(workstation):
	return frappe.get_cached_value("Workstation", workstation, "hour_rate") or 0.0
