# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class JobCardTimeLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		completed_qty: DF.Float
		employee: DF.Link | None
		from_time: DF.Datetime | None
		operation: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		time_in_mins: DF.Float
		to_time: DF.Datetime | None
	# end: auto-generated types

	def validate_report_parent(self):
		previous = frappe.db.get_value(self.doctype, self.name, "parent") if not self.is_new() else None
		for parent in {previous, self.parent} - {None, ""}:
			if frappe.db.get_value("Job Card", parent, "report_request_id"):
				frappe.throw("报工时间和数量属于原记录，不能单独新增、改写或删除", frappe.PermissionError)

	before_validate = validate_report_parent
	before_update_after_submit = validate_report_parent
	on_trash = validate_report_parent
