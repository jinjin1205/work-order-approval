# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.document import Document


class BOMItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_alternative_item: DF.Check
		amount: DF.Currency
		base_amount: DF.Currency
		base_rate: DF.Currency
		bom_no: DF.Link | None
		conversion_factor: DF.Float
		description: DF.TextEditor | None
		do_not_explode: DF.Check
		has_variants: DF.Check
		image: DF.Attach | None
		include_item_in_manufacturing: DF.Check
		item_code: DF.Link
		item_name: DF.Data | None
		operation: DF.Link | None
		original_item: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		qty_consumed_per_unit: DF.Float
		rate: DF.Currency
		source_warehouse: DF.Link | None
		sourced_by_supplier: DF.Check
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		uom: DF.Link
	# end: auto-generated types

	def validate_parent_material_edit(self):
		frappe.throw("请通过产品BOM表单修改用料并保存，已提交版本请复制新版本；不能直接改删BOM子行", frappe.PermissionError)

	before_validate = validate_parent_material_edit
	before_update_after_submit = validate_parent_material_edit
	on_trash = validate_parent_material_edit
