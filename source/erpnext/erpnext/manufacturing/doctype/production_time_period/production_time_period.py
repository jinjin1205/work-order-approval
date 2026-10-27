# Copyright (c) 2026, Contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProductionTimePeriod(Document):
	def before_validate(self):
		frappe.throw("请通过所属报工时段规则保存时段。", frappe.PermissionError)

	def on_trash(self):
		frappe.throw("请通过所属报工时段规则删除时段。", frappe.PermissionError)
