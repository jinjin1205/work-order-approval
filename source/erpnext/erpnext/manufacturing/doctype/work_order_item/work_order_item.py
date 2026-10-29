# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class WorkOrderItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_alternative_item: DF.Check
		amount: DF.Currency
		available_qty_at_source_warehouse: DF.Float
		available_qty_at_wip_warehouse: DF.Float
		consumed_qty: DF.Float
		description: DF.Text | None
		include_item_in_manufacturing: DF.Check
		item_code: DF.Link | None
		item_name: DF.Data | None
		operation: DF.Link | None
		operation_row_id: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Currency
		required_qty: DF.Float
		returned_qty: DF.Float
		source_warehouse: DF.Link | None
		stock_uom: DF.Link | None
		transferred_qty: DF.Float
	# end: auto-generated types

	def validate_direct_material_edit(self):
		stored_parent = frappe.db.get_value("Work Order Item", self.name, "parent") if not self.is_new() else None
		for parent in {stored_parent, self.parent} - {None, ""}:
			if frappe.db.exists("Stock Entry", {"work_order": parent, "docstatus": [">", 0]}):
				frappe.throw("工单已有领退等库存单据历史，净额归零或取消后仍不能改写、删除或改挂用料行", frappe.PermissionError)
			if frappe.db.get_value("Work Order", parent, "approval_requested_by"):
				from erpnext.manufacturing.doctype.work_order.work_order import _production_order_for_details
				_production_order_for_details(parent, for_update=True)
				frappe.throw("请通过本工单用料表修改并保存，不能直接改写或删除用料子行", frappe.PermissionError)

	before_validate = validate_direct_material_edit
	before_update_after_submit = validate_direct_material_edit
	on_trash = validate_direct_material_edit


def on_doctype_update():
	frappe.db.add_index("Work Order Item", ["item_code", "source_warehouse"])
