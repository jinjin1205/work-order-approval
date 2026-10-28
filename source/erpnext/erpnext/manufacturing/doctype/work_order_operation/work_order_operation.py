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
		# Parent saves validate and freeze these terms together; direct child saves do not.
		before = self.get_doc_before_save()
		fields = ("report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency")
		terms = any(record.get(field) not in (None, "") for record in (before, self) if record for field in fields)
		if not terms:
			return
		protected = fields + ("parent", "parenttype", "parentfield", "operation")
		if not before or any(self.get(field) != before.get(field) for field in protected):
			frappe.throw("计价和标准效率依据必须从工单工序表修改，并遵守送审冻结；不能直接保存工序子行", frappe.PermissionError)
