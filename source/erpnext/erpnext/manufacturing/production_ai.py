import frappe

from erpnext.manufacturing.doctype.bom.bom import validate_quantity_input


REPORT_FIELDS = {"good_quantity", "bad_quantity", "from_time", "to_time", "shutdown_seconds", "overtime_seconds"}


@frappe.whitelist()
def get_production_ai_context(work_order):
	order = frappe.get_doc("Work Order", work_order)
	order.check_permission("read")
	return {
		"source": {"doctype": "Work Order", "name": order.name, "modified": str(order.modified)},
		"status": order.status, "approval_state": order.workflow_state, "docstatus": order.docstatus,
		"quantity": order.qty, "unit": order.stock_uom, "bom": order.bom_no,
		"tasks": [{"name": row.name, "idx": row.idx, "operation": row.operation,
			"plan": order.get_operation_plan_quantity(row), "good": row.completed_qty, "bad": row.process_loss_qty}
			for row in order.operations],
	}


def _suggestion_values(suggestion):
	from erpnext.manufacturing.doctype.job_card.job_card import _report_datetime, _whole_non_negative

	data = frappe.parse_json(suggestion) if isinstance(suggestion, str) else suggestion
	if not isinstance(data, dict) or set(data) - REPORT_FIELDS:
		frappe.throw("建议草稿只能包含良品、不良、实际起止时间、停工秒数和加班秒数")
	values = {key:value for key,value in data.items() if value is not None and value != ""}
	for key, label in (("good_quantity", "良品数量"), ("bad_quantity", "不良数量")):
		if key in values:
			values[key] = validate_quantity_input(values[key], label, allow_zero=True)
	for key, label in (("shutdown_seconds", "停工秒数"), ("overtime_seconds", "加班秒数")):
		if key in values:
			values[key] = _whole_non_negative(values[key], label)
	for key, label in (("from_time", "开始时间"), ("to_time", "结束时间")):
		if key in values:
			_report_datetime(values[key], label)
	return values


@frappe.whitelist()
def prepare_production_report_draft(work_order, operation_id, suggestion):
	from erpnext.manufacturing.doctype.job_card.job_card import _report_task

	order, operation, _ = _report_task(work_order, operation_id)
	values = _suggestion_values(suggestion)
	return {
		"work_order": order.name, "operation_id": operation.name, "values": values,
		"missing": [field for field in ("good_quantity", "bad_quantity", "from_time", "to_time") if field not in values],
		"basis": {"mode": "structured-suggestion", "work_order": order.name, "operation_id": operation.name,
			"modified": str(order.modified), "suggestion": values},
	}


def validate_report_draft_basis(basis, work_order, operation_id):
	from erpnext.manufacturing.doctype.job_card.job_card import _report_datetime

	data = frappe.parse_json(basis) if isinstance(basis, str) else basis
	if (not isinstance(data, dict) or set(data) != {"mode", "work_order", "operation_id", "modified", "suggestion"}
		or data["mode"] != "structured-suggestion" or data["work_order"] != work_order or data["operation_id"] != operation_id):
		frappe.throw("建议草稿来源与当前工单或工序不一致，请重新导入并核对")
	_report_datetime(data["modified"], "建议来源版本")
	return {**data, "suggestion": _suggestion_values(data["suggestion"])}


FIELD_SUGGESTION_LABELS = {
	"bom_no": "BOM", "source_warehouse": "原料来源仓库", "wip_warehouse": "在制仓库",
	"fg_warehouse": "成品仓库", "expected_delivery_date": "预计交付日期",
}


def _field_suggestion_context(production_item, company, missing_fields, bom_no):
	if "生产工单发起" not in frappe.get_roles() or not frappe.has_permission("Work Order", "create"):
		frappe.throw("没有生产工单发起权限", frappe.PermissionError)
	if (not all(isinstance(value, str) and value for value in (production_item, company))
		or bom_no is not None and not isinstance(bom_no, str)):
		frappe.throw("请选择明确的生产物料、公司和BOM编号，不能传入筛选条件")
	fields = frappe.parse_json(missing_fields) if isinstance(missing_fields, str) else missing_fields
	if not isinstance(fields, list) or any(not isinstance(field, str) or field not in FIELD_SUGGESTION_LABELS for field in fields):
		frappe.throw("字段建议仅支持BOM、原料/在制/成品仓库和预计交付日期")
	frappe.get_doc("Company", company).check_permission("read")
	item = frappe.get_doc("Item", production_item)
	item.check_permission("read")
	if item.disabled:
		frappe.throw("生产物料已停用，请重新选择")
	return item, list(dict.fromkeys(fields))


def _suggestion_bom(item, company, selected):
	name = selected or item.default_bom
	if not name:
		return None
	bom = frappe.get_doc("BOM", name)
	if selected:
		bom.check_permission("read")
	elif not bom.has_permission("read"):
		return None
	if bom.item != item.name or bom.company != company or bom.docstatus != 1 or not bom.is_active:
		if selected:
			frappe.throw("所选BOM与产品/公司不一致，或尚未提交启用，请重新核对")
		return None
	return bom


def _warehouse_suggestion(field, value, company, reason):
	if not value:
		return None
	warehouse = frappe.get_doc("Warehouse", value)
	if (not warehouse.has_permission("read") or warehouse.company != company
		or warehouse.is_group or warehouse.disabled):
		return None
	return {"fieldname": field, "label": FIELD_SUGGESTION_LABELS[field], "value": warehouse.name,
		"source": {"doctype": "Warehouse", "name": warehouse.name, "modified": str(warehouse.modified)},
		"reason": reason}


@frappe.whitelist()
def get_production_field_suggestions(production_item, company, missing_fields, bom_no=None):
	item, fields = _field_suggestion_context(production_item, company, missing_fields, bom_no)
	bom = _suggestion_bom(item, company, bom_no) if {"bom_no", "source_warehouse"}.intersection(fields) else None
	defaults = frappe.get_doc({"doctype": "Work Order", "production_item": item.name, "company": company})
	if {"fg_warehouse", "wip_warehouse"}.intersection(fields):
		defaults.set_default_warehouse()
	candidates, missing = [], []
	for field in fields:
		candidate = None
		if field == "bom_no" and bom:
			candidate = {"fieldname": field, "label": FIELD_SUGGESTION_LABELS[field], "value": bom.name,
				"source": {"doctype": "BOM", "name": bom.name, "modified": str(bom.modified)},
				"reason": "当前产品配置的默认BOM，已提交并启用" if not bom_no else "当前已选且可读取的有效BOM"}
		elif field in ("fg_warehouse", "wip_warehouse"):
			candidate = _warehouse_suggestion(field, defaults.get(field), company,
				"按工单仓库默认配置选取；候选仓库当前可读且属于所选公司")
		elif field == "source_warehouse" and bom:
			sources = {row.source_warehouse for row in bom.items}
			value = next(iter(sources)) if len(sources) == 1 else None
			candidate = _warehouse_suggestion(field, value, company,
				"已选/默认BOM的全部用料行具有同一非空来源仓库；BOM：" + bom.name)
		if candidate:
			candidates.append(candidate)
		else:
			reason = ("没有本单已确认交期，请本人填写；历史交期不代表本单承诺" if field == "expected_delivery_date"
				else "当前没有可读取且有效的默认BOM，请人工选择" if field == "bom_no"
				else "BOM来源仓库缺失、不唯一或无当前读取权限，请人工核对" if field == "source_warehouse"
				else "原生默认规则未给出同公司、启用且可读取的仓库，请人工选择")
			missing.append({"fieldname": field, "label": FIELD_SUGGESTION_LABELS[field], "reason": reason})
	return {"candidates": candidates, "missing": missing, "history_used": False,
		"context": {"production_item": production_item, "company": company, "bom_no": bom_no}}
