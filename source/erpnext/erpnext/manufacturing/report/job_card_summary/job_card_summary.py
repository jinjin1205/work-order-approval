# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import getdate, cint

from erpnext.stock.report.stock_analytics.stock_analytics import get_period, get_period_date_ranges


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if cint(filters.production_reports):
		return get_production_report_columns(), get_production_reports(filters), None, None, None, True
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	chart_data = get_chart_data(data, filters)
	return columns, data, None, chart_data


def get_data(filters):
	query_filters = {
		"docstatus": ("<", 2),
		"posting_date": ("between", [filters.from_date, filters.to_date]),
	}

	fields = [
		"name",
		"status",
		"work_order",
		"production_item",
		"item_name",
		"posting_date",
		"total_completed_qty",
		"workstation",
		"operation",
		"total_time_in_mins",
	]

	for field in ["work_order", "production_item"]:
		if filters.get(field):
			query_filters[field] = ("in", filters.get(field))

	for field in ["workstation", "operation", "status", "company"]:
		if filters.get(field):
			query_filters[field] = filters.get(field)

	data = frappe.get_list("Job Card", fields=fields, filters=query_filters, limit_page_length=0)

	if not data:
		return []

	job_cards = [d.name for d in data]

	job_card_time_filter = {
		"docstatus": ("<", 2),
		"parent": ("in", job_cards),
	}

	job_card_time_details = {}
	for job_card_data in frappe.get_all(
		"Job Card Time Log",
		fields=["min(from_time) as from_time", "max(to_time) as to_time", "parent"],
		filters=job_card_time_filter,
		group_by="parent",
	):
		job_card_time_details[job_card_data.parent] = job_card_data

	res = []
	for d in data:
		if job_card_time_details.get(d.name):
			d.from_time = job_card_time_details.get(d.name).from_time
			d.to_time = job_card_time_details.get(d.name).to_time

		res.append(d)

	return res


def get_chart_data(job_card_details, filters):
	labels, periodic_data = prepare_chart_data(job_card_details, filters)

	open_job_cards, completed = [], []
	datasets = []

	for d in labels:
		open_job_cards.append(periodic_data.get("Open").get(d))
		completed.append(periodic_data.get("Completed").get(d))

	datasets.append({"name": _("Open"), "values": open_job_cards})
	datasets.append({"name": _("Completed"), "values": completed})

	chart = {"data": {"labels": labels, "datasets": datasets}, "type": "bar"}

	return chart


def prepare_chart_data(job_card_details, filters):
	labels = []

	periodic_data = {"Open": {}, "Completed": {}}

	filters.range = "Monthly"

	ranges = get_period_date_ranges(filters)
	for from_date, end_date in ranges:
		period = get_period(end_date, filters)
		if period not in labels:
			labels.append(period)
			for status in periodic_data:
				periodic_data[status][period] = 0

		for d in job_card_details:
			if from_date <= getdate(d.posting_date) <= end_date:
				status = "Completed" if d.status == "Completed" else "Open"

				periodic_data[status][period] += 1

	return labels, periodic_data


def get_columns(filters):
	columns = [
		{
			"label": _("Id"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Job Card",
			"width": 100,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
	]

	if not filters.get("status"):
		columns.append(
			{"label": _("Status"), "fieldname": "status", "width": 100},
		)

	columns.extend(
		[
			{
				"label": _("Work Order"),
				"fieldname": "work_order",
				"fieldtype": "Link",
				"options": "Work Order",
				"width": 100,
			},
			{
				"label": _("Production Item"),
				"fieldname": "production_item",
				"fieldtype": "Link",
				"options": "Item",
				"width": 110,
			},
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 100},
			{
				"label": _("Workstation"),
				"fieldname": "workstation",
				"fieldtype": "Link",
				"options": "Workstation",
				"width": 110,
			},
			{
				"label": _("Operation"),
				"fieldname": "operation",
				"fieldtype": "Link",
				"options": "Operation",
				"width": 110,
			},
			{
				"label": _("Total Completed Qty"),
				"fieldname": "total_completed_qty",
				"fieldtype": "Float",
				"width": 120,
			},
			{"label": _("From Time"), "fieldname": "from_time", "fieldtype": "Datetime", "width": 120},
			{"label": _("To Time"), "fieldname": "to_time", "fieldtype": "Datetime", "width": 120},
			{
				"label": _("Time Required (In Mins)"),
				"fieldname": "total_time_in_mins",
				"fieldtype": "Float",
				"width": 100,
			},
		]
	)

	return columns


def get_production_reports(filters):
	from erpnext.manufacturing.doctype.job_card.job_card import calculate_report_metrics, _saved_report_metrics

	if not filters.from_date or not filters.to_date or getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw("请填写有效起止日期，开始不能晚于结束")
	state = filters.report_state or "生效"
	if state not in ("生效", "已取消"):
		frappe.throw("请选择生效或已取消报工")
	query = {"docstatus": 1 if state == "生效" else 2, "report_request_id": ["is", "set"],
		"posting_date": ["between", [filters.from_date, filters.to_date]]}
	for name in filters.work_order or []:
		frappe.get_doc("Work Order", name).check_permission("read")
	for field in ("work_order", "production_item"):
		if filters.get(field):
			query[field] = ["in", filters[field]]
	for field in ("company", "operation", "workstation", "status"):
		if filters.get(field):
			query[field] = filters[field]
	cards = frappe.get_list("Job Card", filters=query, fields=["name"], order_by="posting_date, name", limit_page_length=0)
	orders, rows = {}, []
	for item in cards:
		card = frappe.get_doc("Job Card", item.name)
		card.check_permission("read")
		if card.work_order not in orders:
			order = frappe.get_doc("Work Order", card.work_order)
			order.check_permission("read")
			orders[card.work_order] = order
		order = orders[card.work_order]
		metrics = calculate_report_metrics(good_quantity=card.total_completed_qty, bad_quantity=card.process_loss_qty,
			effective_seconds=card.report_effective_seconds)
		saved = _saved_report_metrics(card)
		context = saved["source"] if saved else None
		result = saved["result"] if saved else {}
		rows.append({"name": card.name, "posting_date": card.posting_date, "work_order": card.work_order,
			"operation": card.operation, "operation_id": card.operation_id, "production_item": card.production_item,
			"unit": context["unit"] if context else order.stock_uom, "record_state": state,
			"good_qty": card.total_completed_qty, "bad_qty": card.process_loss_qty,
			"effective_seconds": card.report_effective_seconds, "quality_percent": metrics["quality_percent"] if metrics["quality_percent"] is not None else "—",
			"actual_efficiency": result.get("actual_efficiency") if result.get("actual_efficiency") is not None else "—", "efficiency_percent": result.get("efficiency_percent") if result.get("efficiency_percent") is not None else "—",
			"estimated_wage": card.report_estimated_wage if context and context.get("wage_mode") else "—", "currency": context.get("currency") if context else None,
			"amended_from": card.amended_from, "correction_reason": card.correction_reason,
			"confirmed_by": card.owner, "confirmed_at": card.creation,
			"basis_status": "历史快照" if saved else "缺少历史指标快照"})
	return rows


def get_production_report_columns():
	return [{"fieldname": field, "label": label, "fieldtype": kind, "options": options, "width": 140}
		for field, label, kind, options in [
			("name", "报工原单", "Link", "Job Card"), ("posting_date", "过账日期", "Date", None),
			("record_state", "生效状态", "Data", None), ("work_order", "工单", "Link", "Work Order"),
			("operation", "工序", "Link", "Operation"), ("operation_id", "工单任务行", "Data", None),
			("production_item", "成品", "Link", "Item"), ("unit", "库存单位", "Data", None),
			("good_qty", "良品数量", "Float", None), ("bad_qty", "不良数量", "Float", None),
			("effective_seconds", "有效工时秒数", "Float", None), ("quality_percent", "良品率百分比", "Data", None),
			("actual_efficiency", "每小时实际产量", "Data", None), ("efficiency_percent", "效率百分比", "Data", None),
			("estimated_wage", "预计工资", "Data", None), ("currency", "币种", "Data", None),
			("basis_status", "指标依据", "Data", None), ("amended_from", "更正原单", "Link", "Job Card"),
			("correction_reason", "更正原因", "Data", None), ("confirmed_by", "确认人", "Data", None),
			("confirmed_at", "确认记录时间", "Datetime", None),
		]]
