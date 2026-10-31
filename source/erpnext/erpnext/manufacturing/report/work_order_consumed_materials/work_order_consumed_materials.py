# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import add_days, getdate, cint


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_data(report_filters):
	from erpnext.manufacturing.doctype.work_order.work_order import get_production_material_summary
	from erpnext.manufacturing.doctype.job_card.job_card import calculate_report_metrics

	report_filters = frappe._dict(report_filters or {})
	if report_filters.name:
		frappe.get_doc("Work Order", report_filters.name).check_permission("read")
	work_orders = frappe.get_list("Work Order", filters=get_filter_condition(report_filters),
		fields=["name", "status", "workflow_state", "production_item", "qty", "produced_qty", "stock_uom"],
		order_by="name", limit_page_length=0)
	data = []
	for order in work_orders:
		summary = get_production_material_summary(order.name)
		# Only detect whether a real source exists; the authoritative consumed quantity stays on the order.
		entries = frappe.get_all("Stock Entry", filters={"work_order": order.name, "docstatus": 1,
			"purpose": ["in", ["Manufacture", "Material Consumption for Manufacture"]]}, pluck="name")
		consumed_items = set()
		if entries:
			for detail in frappe.get_all("Stock Entry Detail", filters={"parent": ["in", entries],
				"s_warehouse": ["is", "set"]}, fields=["item_code", "original_item"]):
				consumed_items.add(detail.original_item or detail.item_code)
		for item in summary["items"]:
			consumed = item["consumed"] if item["item_code"] in consumed_items else None
			if consumed is None and item["consumed"]:
				frappe.throw("工单实耗汇总与有效来源不一致，请核对原库存记录")
			extra = max(Decimal(str(consumed)) - Decimal(str(item["required"])), 0) if consumed is not None else None
			if cint(report_filters.show_extra_consumed_materials) and not extra:
				continue
			progress = calculate_report_metrics(good_quantity=0, bad_quantity=0, effective_seconds=0,
				issued_quantity=item["issued"], required_quantity=item["required"])["material_issue_percent"]
			data.append(dict(order, status=_(order.status), material_issue_percent=progress if progress is not None else "—", raw_material_item_code=item["item_code"], raw_material_name=item["item_name"],
				raw_material_uom=item["unit"], required_qty=item["required"], transferred_qty=item["issued"],
				returned_qty=item["returned"], net_qty=item["net"], consumed_qty=consumed,
				extra_consumed_qty=extra, consumption_status="已记录" if consumed is not None else "未记录"))
	return data


def get_filter_condition(report_filters):
	filters = {"docstatus": 1}
	if bool(report_filters.from_date) != bool(report_filters.to_date):
		frappe.throw("请同时填写开始和结束日期")
	if report_filters.from_date:
		if getdate(report_filters.from_date) > getdate(report_filters.to_date):
			frappe.throw("开始日期不能晚于结束日期")
		# Half-open range includes the entire final day without guessing a time precision.
		filters["creation"] = [">=", getdate(report_filters.from_date)]
		filters = [["Work Order", key, value[0], value[1]] if isinstance(value, list)
			else ["Work Order", key, "=", value] for key, value in filters.items()]
		filters.append(["Work Order", "creation", "<", add_days(report_filters.to_date, 1)])
	else:
		filters = [["Work Order", "docstatus", "=", 1]]
	for field in ("name", "production_item", "company", "status"):
		if report_filters.get(field):
			filters.append(["Work Order", field, "=", report_filters[field]])
	return filters


def get_columns():
	columns = [
		{
			"label": _("Id"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 80,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 80},
		{
			"label": _("Production Item"),
			"fieldname": "production_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 130,
		},
		{"label": _("Qty to Produce"), "fieldname": "qty", "fieldtype": "Float", "width": 120},
		{"label": _("Produced Qty"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 110},
		{
			"label": _("Raw Material Item"),
			"fieldname": "raw_material_item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("Item Name"), "fieldname": "raw_material_name", "width": 130},
		{"label": _("Required Qty"), "fieldname": "required_qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Transferred Qty"),
			"fieldname": "transferred_qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{"label": _("Consumed Qty"), "fieldname": "consumed_qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Extra Consumed Qty"),
			"fieldname": "extra_consumed_qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Returned Qty"),
			"fieldname": "returned_qty",
			"fieldtype": "Float",
			"width": 100,
		},
	]

	labels = {"name": "工单", "status": "执行状态", "production_item": "成品", "qty": "工单计划数量",
		"produced_qty": "成品入库数量", "raw_material_item_code": "原料", "raw_material_name": "原料名称",
		"required_qty": "本单需求数量", "transferred_qty": "累计领料数量", "returned_qty": "累计退料数量",
		"consumed_qty": "实际消耗数量", "extra_consumed_qty": "超需求消耗数量"}
	for column in columns:
		column["label"] = labels[column["fieldname"]]
	columns.extend([
		{"fieldname": "workflow_state", "label": "审批状态", "fieldtype": "Data", "width": 100},
		{"fieldname": "stock_uom", "label": "成品库存单位", "fieldtype": "Data", "width": 100},
		{"fieldname": "raw_material_uom", "label": "原料库存单位", "fieldtype": "Data", "width": 100},
		{"fieldname": "material_issue_percent", "label": "累计领料进度百分比", "fieldtype": "Data", "width": 160},
		{"fieldname": "net_qty", "label": "净领料数量", "fieldtype": "Float", "width": 110},
		{"fieldname": "consumption_status", "label": "实耗记录状态", "fieldtype": "Data", "width": 120},
	])
	return columns
