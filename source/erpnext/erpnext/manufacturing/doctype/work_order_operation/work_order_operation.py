# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class WorkOrderOperation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_end_time: DF.Datetime | None
		actual_operating_cost: DF.Currency
		actual_operation_time: DF.Float
		actual_start_time: DF.Datetime | None
		batch_size: DF.Float
		bom: DF.Link | None
		completed_qty: DF.Float
		description: DF.TextEditor | None
		hour_rate: DF.Float
		operation: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		planned_end_time: DF.Datetime | None
		planned_operating_cost: DF.Currency
		planned_start_time: DF.Datetime | None
		process_loss_qty: DF.Float
		sequence_id: DF.Int
		status: DF.Literal["Pending", "Work in Progress", "Completed"]
		time_in_mins: DF.Float
		workstation: DF.Link | None
		workstation_type: DF.Link | None
	# end: auto-generated types

	def before_validate(self):
		self.validate_report_history()
		self.validate_task_parent_edit()
		# Parent saves validate and freeze these terms together; direct child saves do not.
		before = self.get_doc_before_save()
		fields = ("report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency")
		terms = any(record.get(field) not in (None, "") for record in (before, self) if record for field in fields)
		if not terms:
			return
		protected = fields + ("parent", "parenttype", "parentfield", "operation")
		if not before or any(self.get(field) != before.get(field) for field in protected):
			frappe.throw("计价和标准效率依据必须从工单工序表修改，并遵守送审冻结；不能直接保存工序子行", frappe.PermissionError)

	def validate_report_history(self):
		# operation_id is Data, so native Link checks cannot preserve this history.
		# Use the persisted row identity, not the client-supplied parent. Cancelled
		# cards still belong to the task; native parent saves handle derived updates.
		if not self.is_new() and frappe.db.exists("Job Card", {
			"operation_id": self.name, "docstatus": [">", 0],
		}):
			frappe.throw("工序已有报工历史，不能直接改写、改挂或删除任务行", frappe.PermissionError)

	def validate_task_parent_edit(self, *, deleting=False):
		from erpnext.manufacturing.doctype.work_order.work_order import _production_order_for_details

		stored = frappe.db.get_value("Work Order Operation", self.name,
			["parent", "parenttype", "parentfield"], as_dict=True) if not self.is_new() else None
		parents = {self.parent, stored.parent if stored else None} - {None, ""}
		for parent in sorted(parents):
			if not frappe.db.get_value("Work Order", parent, "approval_requested_by"):
				continue
			order = _production_order_for_details(parent, for_update=True)
			if self.parenttype != "Work Order" or self.parentfield != "operations" or (stored and any(
				self.get(f) != stored.get(f) for f in ("parent", "parenttype", "parentfield")
			)):
				frappe.throw("任务行不能直接改挂，请从工单工序表调整", frappe.PermissionError)
			if deleting:
				if not order.operations or order.operations[-1].name != self.name:
					frappe.throw("中间或首道任务请从工单工序表删除并核对顺序后保存", frappe.PermissionError)
				order.set("operations", [r for r in order.operations if r.name != self.name])
				order.validate_operations_sequence()
				continue
			before = self.get_doc_before_save()
			fields = ("operation", "idx", "sequence_id", "report_plan_qty", "report_scope", "report_department", "report_employee",
				"completed_qty", "process_loss_qty", "actual_start_time", "actual_end_time", "actual_operation_time", "actual_operating_cost", "status")
			if not before or any(self.get(f) != before.get(f) for f in fields):
				frappe.throw("请通过工单工序表增加、复制或调整任务计划、顺序和授权后保存工单", frappe.PermissionError)

	def before_update_after_submit(self):
		self.validate_report_history()
		self.validate_task_parent_edit()

	def on_trash(self):
		self.validate_report_history()
		self.validate_task_parent_edit(deleting=True)
