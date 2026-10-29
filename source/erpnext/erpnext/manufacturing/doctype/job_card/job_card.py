# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import datetime
import hashlib
import json
import re
from collections import OrderedDict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull, Max, Min
from frappe.utils import (
	add_days,
	add_to_date,
	cint,
	flt,
	get_datetime,
	get_link_to_form,
	get_time,
	getdate,
	time_diff,
	time_diff_in_hours,
	time_diff_in_seconds,
)

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_mins_between_operations,
)
from erpnext.manufacturing.doctype.workstation_type.workstation_type import get_workstations


class OverlapError(frappe.ValidationError):
	pass


class OperationMismatchError(frappe.ValidationError):
	pass


class OperationSequenceError(frappe.ValidationError):
	pass


class JobCardCancelError(frappe.ValidationError):
	pass


class JobCardOverTransferError(frappe.ValidationError):
	pass


class JobCard(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.job_card_item.job_card_item import JobCardItem
		from erpnext.manufacturing.doctype.job_card_operation.job_card_operation import JobCardOperation
		from erpnext.manufacturing.doctype.job_card_scheduled_time.job_card_scheduled_time import (
			JobCardScheduledTime,
		)
		from erpnext.manufacturing.doctype.job_card_scrap_item.job_card_scrap_item import JobCardScrapItem
		from erpnext.manufacturing.doctype.job_card_time_log.job_card_time_log import JobCardTimeLog

		actual_end_date: DF.Datetime | None
		actual_start_date: DF.Datetime | None
		amended_from: DF.Link | None
		barcode: DF.Barcode | None
		batch_no: DF.Link | None
		bom_no: DF.Link | None
		company: DF.Link
		current_time: DF.Int
		employee: DF.TableMultiSelect[JobCardTimeLog]
		expected_end_date: DF.Datetime | None
		expected_start_date: DF.Datetime | None
		for_job_card: DF.Link | None
		for_operation: DF.Link | None
		for_quantity: DF.Float
		hour_rate: DF.Currency
		is_corrective_job_card: DF.Check
		item_name: DF.ReadOnly | None
		items: DF.Table[JobCardItem]
		job_started: DF.Check
		naming_series: DF.Literal["PO-JOB.#####"]
		operation: DF.Link
		operation_id: DF.Data | None
		operation_row_number: DF.Literal[None]
		posting_date: DF.Date | None
		process_loss_qty: DF.Float
		production_item: DF.Link | None
		project: DF.Link | None
		quality_inspection: DF.Link | None
		quality_inspection_template: DF.Link | None
		remarks: DF.SmallText | None
		requested_qty: DF.Float
		scheduled_time_logs: DF.Table[JobCardScheduledTime]
		scrap_items: DF.Table[JobCardScrapItem]
		sequence_id: DF.Int
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.SmallText | None
		started_time: DF.Datetime | None
		status: DF.Literal[
			"Open",
			"Work In Progress",
			"Partially Transferred",
			"Material Transferred",
			"On Hold",
			"Submitted",
			"Cancelled",
			"Completed",
		]
		sub_operations: DF.Table[JobCardOperation]
		time_logs: DF.Table[JobCardTimeLog]
		time_required: DF.Float
		total_completed_qty: DF.Float
		total_time_in_mins: DF.Float
		transferred_qty: DF.Float
		wip_warehouse: DF.Link
		work_order: DF.Link
		workstation: DF.Link
		workstation_type: DF.Link | None
	# end: auto-generated types

	def onload(self):
		if self.get("report_request_id"):
			self.set_onload("report_metrics", _saved_report_metrics(self))
		excess_transfer = frappe.db.get_single_value("Manufacturing Settings", "job_card_excess_transfer")
		self.set_onload("job_card_excess_transfer", excess_transfer)
		self.set_onload("work_order_closed", self.is_work_order_closed())
		self.set_onload("has_stock_entry", self.has_stock_entry())

	def has_stock_entry(self):
		return frappe.db.exists("Stock Entry", {"job_card": self.name, "docstatus": ["!=", 2]})

	def before_validate(self):
		self.validate_report_record()
		self.set_wip_warehouse()

	def validate_report_record(self):
		old_key = frappe.db.get_value("Job Card", self.name, "report_request_id") if not self.is_new() else None
		context = getattr(frappe.local, "production_report_context", None)
		trusted = context and context.card is self and context.user == frappe.session.user
		if (old_key or any(self.get(f) for f in ("report_request_id", "report_payload_hash", "report_time_context",
			"report_effective_seconds", "report_time_rule", "report_shutdown_seconds", "report_overtime_seconds",
			"report_metrics_context", "report_estimated_wage"))) and not trusted:
			frappe.throw("报工事实只能通过确认或关联更正保存，原记录不能改写", frappe.PermissionError)
		if not trusted and not self.get("report_request_id") and self.work_order:
			order = frappe.get_doc("Work Order", self.work_order)
			if order.get("approval_requested_by") and not frappe.has_permission("Work Order", "write", doc=order):
				frappe.throw("操作工不能修改计划卡，请通过逐笔报工确认实际数量", frappe.PermissionError)
		for row in self.get("time_logs") + self.get("employee"):
			if row.name:
				parent = frappe.db.get_value("Job Card Time Log", row.name, "parent")
				if parent and parent != self.name:
					frappe.throw("不能使用其他作业卡的时间或人员记录", frappe.PermissionError)

	def before_submit(self):
		self.validate_report_record()
		if self.work_order and frappe.db.get_value("Work Order", self.work_order, "approval_requested_by") and not self.get("report_request_id"):
			frappe.throw("计划卡不能作为报工提交，请使用确认报工入口", frappe.PermissionError)

	def before_update_after_submit(self):
		self.validate_report_record()

	def before_cancel(self):
		self.validate_report_record()

	def on_trash(self):
		if frappe.db.get_value("Job Card", self.name, "report_request_id"):
			frappe.throw("报工原记录必须保留，不能删除", frappe.PermissionError)

	def validate(self):
		self.validate_work_order()
		self.validate_time_logs()
		self.set_status()
		self.validate_operation_id()
		self.validate_sequence_id()
		self.set_sub_operations()
		self.update_sub_operation_status()

	def on_update(self):
		self.validate_job_card_qty()

	def validate_job_card_qty(self):
		if not (self.operation_id and self.work_order):
			return

		if frappe.db.get_value("Work Order", self.work_order, "approval_requested_by"):
			from erpnext.manufacturing.doctype.bom.bom import validate_quantity_input
			filters = {"work_order": self.work_order, "operation_id": self.operation_id, "name": ["!=", self.name]}
			if self.get("report_request_id"):
				filters.update(docstatus=1, report_request_id=["is", "set"])
			else:
				filters.update(docstatus=["!=", 2], report_request_id=["is", "not set"])
			quantities = [row[0] for row in frappe.db.get_values("Job Card", filters, "for_quantity", for_update=True)]
			total = sum((Decimal(str(q)) for q in quantities), Decimal(0)) + Decimal(str(validate_quantity_input(self.for_quantity, "本次数量")))
			order = frappe.get_doc("Work Order", self.work_order)
			operation = next((row for row in order.operations if row.name == self.operation_id), None)
			if not operation:
				frappe.throw("本道工序不属于当前工单", frappe.PermissionError)
			plan = Decimal(str(order.get_operation_plan_quantity(operation)))
			allowance = Decimal(str(frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order") or 0))
			if total > plan * (1 + allowance / 100):
				frappe.throw("本工序累计数量超过任务允许数量，请核对本次报工和已确认记录")
			return

		wo_qty = flt(frappe.get_cached_value("Work Order", self.work_order, "qty"))

		completed_qty = flt(frappe.db.get_value("Work Order Operation", self.operation_id, "completed_qty"))

		over_production_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)

		wo_qty = wo_qty + (wo_qty * over_production_percentage / 100)

		job_card_qty = frappe.get_all(
			"Job Card",
			fields=["sum(for_quantity)"],
			filters={
				"work_order": self.work_order,
				"operation_id": self.operation_id,
				"docstatus": ["!=", 2],
			},
			as_list=1,
		)

		job_card_qty = flt(job_card_qty[0][0]) if job_card_qty else 0

		if job_card_qty and ((job_card_qty - completed_qty) > wo_qty):
			form_link = get_link_to_form("Manufacturing Settings", "Manufacturing Settings")
			frappe.throw(
				_(
					"Qty To Manufacture in the job card cannot be greater than Qty To Manufacture in the work order for the operation {0}. <br><br><b>Solution: </b> Either you can reduce the Qty To Manufacture in the job card or set the 'Overproduction Percentage For Work Order' in the {1}."
				).format(bold(self.operation), form_link),
				title=_("Extra Job Card Quantity"),
			)

	def set_sub_operations(self):
		if not self.sub_operations and self.operation:
			self.sub_operations = []
			for row in frappe.get_all(
				"Sub Operation",
				filters={"parent": self.operation},
				fields=["operation", "idx"],
				order_by="idx",
			):
				row.status = "Pending"
				row.sub_operation = row.operation
				self.append("sub_operations", row)

	def validate_time_logs(self):
		self.total_time_in_mins = 0.0
		self.total_completed_qty = 0.0

		if self.get("time_logs"):
			for d in self.get("time_logs"):
				d.time_in_mins = 0
				if d.to_time and not d.from_time:
					frappe.throw("第{0}行：填写结束时间时必须填写开始时间。".format(d.idx))
				if d.to_time and get_datetime(d.from_time) > get_datetime(d.to_time):
					frappe.throw(_("Row {0}: From time must be less than to time").format(d.idx))

				open_job_cards = []
				if d.get("employee"):
					open_job_cards = self.get_open_job_cards(d.get("employee"), workstation=self.workstation)

				empty_report_interval = self.get("report_request_id") and d.from_time and d.to_time and get_datetime(d.from_time) == get_datetime(d.to_time)
				data = None if empty_report_interval else self.get_overlap_for(d, open_job_cards=open_job_cards)
				if data:
					frappe.throw(
						_("Row {0}: From Time and To Time of {1} is overlapping with {2}").format(
							d.idx, self.name, data.name
						),
						OverlapError,
					)

				if d.from_time and d.to_time:
					d.time_in_mins = time_diff_in_hours(d.to_time, d.from_time) * 60
					self.total_time_in_mins += d.time_in_mins

				if d.completed_qty and not self.sub_operations:
					self.total_completed_qty += d.completed_qty

			self.total_completed_qty = flt(self.total_completed_qty, self.precision("total_completed_qty"))

		for row in self.sub_operations:
			self.total_completed_qty += row.completed_qty

	def get_overlap_for(self, args, open_job_cards=None):
		time_logs = []

		time_logs.extend(self.get_time_logs(args, "Job Card Time Log"))

		time_logs.extend(self.get_time_logs(args, "Job Card Scheduled Time", open_job_cards=open_job_cards))

		if not time_logs:
			return {}

		time_logs = sorted(time_logs, key=lambda x: x.get("to_time"))

		production_capacity = 1
		if self.workstation:
			production_capacity = (
				frappe.get_cached_value("Workstation", self.workstation, "production_capacity") or 1
			)

		if self.get_open_job_cards(args.get("employee")):
			frappe.throw(
				_(
					"Employee {0} is currently working on another workstation. Please assign another employee."
				).format(args.get("employee")),
				OverlapError,
			)

		if not self.has_overlap(production_capacity, time_logs):
			return {}

		if not self.workstation and self.workstation_type and time_logs:
			if workstation_time := self.get_workstation_based_on_available_slot(time_logs):
				self.workstation = workstation_time.get("workstation")
				return workstation_time

		return time_logs[0]

	def has_overlap(self, production_capacity, time_logs):
		overlap = False
		if production_capacity == 1 and len(time_logs) >= 1:
			return True
		if not len(time_logs):
			return False

		# sorting overlapping job cards as per from_time
		time_logs = sorted(time_logs, key=lambda x: x.get("from_time"))
		# alloted_capacity has key number starting from 1. Key number will increment by 1 if non sequential job card found
		# if key number reaches/crosses to production_capacity means capacity is full and overlap error generated
		# this will store last to_time of sequential job cards
		alloted_capacity = {1: time_logs[0]["to_time"]}
		for i in range(1, len(time_logs)):
			sequential_job_card_found = False
			# scanning for all Existing keys
			for key in alloted_capacity.keys():
				# if current Job Card from time is greater than last to_time in that key means these job card are sequential
				if alloted_capacity[key] <= time_logs[i]["from_time"]:
					# So update key's value with last to_time
					alloted_capacity[key] = time_logs[i]["to_time"]
					# flag is true as we get sequential Job Card for that key
					sequential_job_card_found = True
					# Immediately break so that job card to time is not added with any other key except this
					break
			# if sequential job card not found above means it is overlapping  so increment key number to alloted_capacity
			if not sequential_job_card_found:
				# increment key number
				key = key + 1
				# for that key last to time is assigned.
				alloted_capacity[key] = time_logs[i]["to_time"]
		if len(alloted_capacity) >= production_capacity:
			# if number of keys greater or equal to production caoacity means full capacity is utilized and we should throw overlap error
			return True
		return overlap

	def get_time_logs(self, args, doctype, open_job_cards=None):
		if args.get("remaining_time_in_mins") and get_datetime(args.from_time) >= get_datetime(args.to_time):
			args.to_time = add_to_date(args.from_time, minutes=args.get("remaining_time_in_mins"))

		jc = frappe.qb.DocType("Job Card")
		jctl = frappe.qb.DocType(doctype)

		time_conditions = [
			((jctl.from_time < args.from_time) & (jctl.to_time > args.from_time)),
			((jctl.from_time < args.to_time) & (jctl.to_time > args.to_time)),
			((jctl.from_time >= args.from_time) & (jctl.to_time <= args.to_time)),
		]

		query = (
			frappe.qb.from_(jctl)
			.from_(jc)
			.select(
				jc.name.as_("name"),
				jctl.name.as_("row_name"),
				jctl.from_time,
				jctl.to_time,
				jc.workstation,
				jc.workstation_type,
			)
			.where(
				(jctl.parent == jc.name)
				& (Criterion.any(time_conditions))
				& (jctl.name != f"{args.name or 'No Name'}")
				& (jc.name != f"{args.parent or 'No Name'}")
				& (jc.docstatus < 2)
			)
			.orderby(jctl.to_time)
		)

		if self.workstation_type:
			query = query.where(jc.workstation_type == self.workstation_type)

		if self.workstation:
			query = query.where(jc.workstation == self.workstation)

		if args.get("employee"):
			if not open_job_cards and doctype == "Job Card Scheduled Time":
				return []

			if doctype == "Job Card Time Log":
				query = query.where(jctl.employee == args.get("employee"))
			else:
				query = query.where(jc.name.isin(open_job_cards))

		if doctype == "Job Card Time Log":
			query = query.where(jc.docstatus < 2)
		else:
			query = query.where((jc.docstatus == 0) & (jc.total_time_in_mins == 0))

		time_logs = query.run(as_dict=True)

		return time_logs

	def get_open_job_cards(self, employee, workstation=None):
		jc = frappe.qb.DocType("Job Card")
		jctl = frappe.qb.DocType("Job Card Time Log")

		query = (
			frappe.qb.from_(jc)
			.left_join(jctl)
			.on(jc.name == jctl.parent)
			.select(jc.name)
			.where(
				(jctl.parent == jc.name)
				& (jctl.employee == employee)
				& (jc.docstatus < 1)
				& (jc.name != self.name)
			)
		)

		if workstation:
			query = query.where(jc.workstation == workstation)

		jobs = query.run(as_dict=True)
		return [job.get("name") for job in jobs] if jobs else []

	def get_workstation_based_on_available_slot(self, existing_time_logs) -> dict:
		workstations = get_workstations(self.workstation_type)
		if workstations:
			busy_workstations = self.time_slot_wise_busy_workstations(existing_time_logs)
			for time_slot in busy_workstations:
				available_workstations = sorted(list(set(workstations) - set(busy_workstations[time_slot])))
				if available_workstations:
					return frappe._dict(
						{
							"workstation": available_workstations[0],
							"planned_start_time": get_datetime(time_slot[0]),
							"to_time": get_datetime(time_slot[1]),
						}
					)

		return frappe._dict({})

	@staticmethod
	def time_slot_wise_busy_workstations(existing_time_logs) -> dict:
		time_slot = OrderedDict()
		for row in existing_time_logs:
			from_time = get_datetime(row.from_time).strftime("%Y-%m-%d %H:%M")
			to_time = get_datetime(row.to_time).strftime("%Y-%m-%d %H:%M")
			time_slot.setdefault((from_time, to_time), []).append(row.workstation)

		return time_slot

	def schedule_time_logs(self, row):
		row.remaining_time_in_mins = row.time_in_mins
		while row.remaining_time_in_mins > 0:
			args = frappe._dict(
				{
					"from_time": row.planned_start_time,
					"to_time": row.planned_end_time,
					"remaining_time_in_mins": row.remaining_time_in_mins,
				}
			)

			self.validate_overlap_for_workstation(args, row)
			self.check_workstation_time(row)

	def validate_overlap_for_workstation(self, args, row):
		# get the last record based on the to time from the job card
		data = self.get_overlap_for(args)

		if not self.workstation:
			workstations = get_workstations(self.workstation_type)
			if workstations:
				# Get the first workstation
				self.workstation = workstations[0]

		if not data:
			row.planned_start_time = args.from_time
			return

		if data:
			if data.get("planned_start_time"):
				args.planned_start_time = get_datetime(data.planned_start_time)
			else:
				args.planned_start_time = get_datetime(data.to_time + get_mins_between_operations())

			args.from_time = args.planned_start_time
			args.to_time = add_to_date(args.planned_start_time, minutes=row.remaining_time_in_mins)

			self.validate_overlap_for_workstation(args, row)

	def check_workstation_time(self, row):
		workstation_doc = frappe.get_cached_doc("Workstation", self.workstation)
		if not workstation_doc.working_hours or cint(
			frappe.db.get_single_value("Manufacturing Settings", "allow_overtime")
		):
			if get_datetime(row.planned_end_time) <= get_datetime(row.planned_start_time):
				row.planned_end_time = add_to_date(row.planned_start_time, minutes=row.time_in_mins)
				row.remaining_time_in_mins = 0.0
			else:
				row.remaining_time_in_mins -= time_diff_in_minutes(
					row.planned_end_time, row.planned_start_time
				)

			self.update_time_logs(row)
			return

		start_date = getdate(row.planned_start_time)
		start_time = get_time(row.planned_start_time)

		new_start_date = workstation_doc.validate_workstation_holiday(start_date)

		if new_start_date != start_date:
			row.planned_start_time = datetime.datetime.combine(new_start_date, start_time)
			start_date = new_start_date

		total_idx = len(workstation_doc.working_hours)

		for i, time_slot in enumerate(workstation_doc.working_hours):
			workstation_start_time = datetime.datetime.combine(start_date, get_time(time_slot.start_time))
			workstation_end_time = datetime.datetime.combine(start_date, get_time(time_slot.end_time))

			if (
				get_datetime(row.planned_start_time) >= workstation_start_time
				and get_datetime(row.planned_start_time) <= workstation_end_time
			):
				time_in_mins = time_diff_in_minutes(workstation_end_time, row.planned_start_time)

				# If remaining time fit in workstation time logs else split hours as per workstation time
				if time_in_mins > row.remaining_time_in_mins:
					row.planned_end_time = add_to_date(
						row.planned_start_time, minutes=row.remaining_time_in_mins
					)
					row.remaining_time_in_mins = 0
				else:
					row.planned_end_time = add_to_date(row.planned_start_time, minutes=time_in_mins)
					row.remaining_time_in_mins -= time_in_mins

				self.update_time_logs(row)

				if total_idx != (i + 1) and row.remaining_time_in_mins > 0:
					row.planned_start_time = datetime.datetime.combine(
						start_date, get_time(workstation_doc.working_hours[i + 1].start_time)
					)

		if row.remaining_time_in_mins > 0:
			start_date = add_days(start_date, 1)
			row.planned_start_time = datetime.datetime.combine(
				start_date, get_time(workstation_doc.working_hours[0].start_time)
			)

	def add_time_log(self, args):
		self.validate_transfer_qty()

		last_row = []
		employees = args.employees
		if isinstance(employees, str):
			employees = json.loads(employees)

		if self.time_logs and len(self.time_logs) > 0:
			last_row = self.time_logs[-1]

		self.reset_timer_value(args)
		if last_row and args.get("complete_time"):
			for row in self.time_logs:
				if not row.to_time:
					row.update(
						{
							"to_time": get_datetime(args.get("complete_time")),
							"operation": args.get("sub_operation"),
							"completed_qty": (args.get("completed_qty") if last_row.idx == row.idx else 0.0),
						}
					)
		elif args.get("start_time"):
			new_args = frappe._dict(
				{
					"from_time": get_datetime(args.get("start_time")),
					"operation": args.get("sub_operation"),
					"completed_qty": 0.0,
				}
			)

			if employees:
				for name in employees:
					new_args.employee = name.get("employee")
					self.add_start_time_log(new_args)
			else:
				self.add_start_time_log(new_args)

		if not self.employee and employees:
			self.set_employees(employees)

		if self.status == "On Hold":
			self.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)

		self.save()

	def add_start_time_log(self, args):
		self.append("time_logs", args)

	def set_employees(self, employees):
		for name in employees:
			self.append("employee", {"employee": name.get("employee"), "completed_qty": 0.0})

	def reset_timer_value(self, args):
		self.started_time = None

		if args.get("status") in ["Work In Progress", "Complete"]:
			self.current_time = 0.0

			if args.get("status") == "Work In Progress":
				self.started_time = get_datetime(args.get("start_time"))

		if args.get("status") == "Resume Job":
			args["status"] = "Work In Progress"

		if args.get("status"):
			self.status = args.get("status")

	def update_sub_operation_status(self):
		if not (self.sub_operations and self.time_logs):
			return

		operation_wise_completed_time = {}
		for time_log in self.time_logs:
			if time_log.operation not in operation_wise_completed_time:
				operation_wise_completed_time.setdefault(
					time_log.operation,
					frappe._dict(
						{"status": "Pending", "completed_qty": 0.0, "completed_time": 0.0, "employee": []}
					),
				)

			op_row = operation_wise_completed_time[time_log.operation]
			op_row.status = "Work In Progress" if not time_log.time_in_mins else "Complete"
			if self.status == "On Hold":
				op_row.status = "Pause"

			op_row.employee.append(time_log.employee)
			if time_log.time_in_mins:
				op_row.completed_time += time_log.time_in_mins
				op_row.completed_qty += flt(time_log.completed_qty)

		for row in self.sub_operations:
			operation_deatils = operation_wise_completed_time.get(row.sub_operation)
			if operation_deatils:
				if row.status != "Complete":
					row.status = operation_deatils.status

				row.completed_time = operation_deatils.completed_time
				if operation_deatils.employee:
					row.completed_time = row.completed_time / len(set(operation_deatils.employee))

					if operation_deatils.completed_qty:
						row.completed_qty = operation_deatils.completed_qty / len(
							set(operation_deatils.employee)
						)
			else:
				row.status = "Pending"
				row.completed_time = 0.0
				row.completed_qty = 0.0

	def update_time_logs(self, row):
		self.append(
			"scheduled_time_logs",
			{
				"from_time": row.planned_start_time,
				"to_time": row.planned_end_time,
				"completed_qty": 0,
				"time_in_mins": time_diff_in_minutes(row.planned_end_time, row.planned_start_time),
			},
		)

	@frappe.whitelist()
	def get_required_items(self):
		if not self.get("work_order"):
			return

		doc = frappe.get_doc("Work Order", self.get("work_order"))
		if doc.transfer_material_against == "Work Order" or doc.skip_transfer:
			return

		for d in doc.required_items:
			if not d.operation:
				frappe.throw(
					_("Row {0} : Operation is required against the raw material item {1}").format(
						d.idx, d.item_code
					)
				)

			if self.get("operation") == d.operation or self.is_corrective_job_card:
				self.append(
					"items",
					{
						"item_code": d.item_code,
						"source_warehouse": d.source_warehouse,
						"uom": frappe.db.get_value("Item", d.item_code, "stock_uom"),
						"item_name": d.item_name,
						"description": d.description,
						"required_qty": (d.required_qty * flt(self.for_quantity)) / doc.qty,
						"rate": d.rate,
						"amount": d.amount,
					},
				)

	def before_save(self):
		self.set_expected_and_actual_time()
		self.set_process_loss()

	def on_submit(self):
		self.validate_transfer_qty()
		self.validate_job_card()
		self.update_work_order()
		self.set_transferred_qty()

	def on_cancel(self):
		self.update_work_order()
		self.set_transferred_qty()

	def validate_transfer_qty(self):
		if not self.is_corrective_job_card and self.items and self.transferred_qty < self.for_quantity:
			frappe.throw(
				_(
					"Materials needs to be transferred to the work in progress warehouse for the job card {0}"
				).format(self.name)
			)

	def validate_job_card(self):
		if self.work_order and frappe.get_cached_value("Work Order", self.work_order, "status") == "Stopped":
			frappe.throw(
				_("Transaction not allowed against stopped Work Order {0}").format(
					get_link_to_form("Work Order", self.work_order)
				)
			)

		if not self.time_logs:
			frappe.throw(
				_("Time logs are required for {0} {1}").format(
					bold("Job Card"), get_link_to_form("Job Card", self.name)
				)
			)
		elif frappe.db.get_single_value("Manufacturing Settings", "enforce_time_logs"):
			for row in self.time_logs:
				if not row.from_time or not row.to_time:
					frappe.throw(
						_("Row #{0}: From Time and To Time fields are required").format(row.idx),
					)

		precision = self.precision("total_completed_qty")
		total_completed_qty = flt(
			flt(self.total_completed_qty, precision) + flt(self.process_loss_qty, precision)
		)

		if self.for_quantity and flt(total_completed_qty, precision) != flt(self.for_quantity, precision):
			total_completed_qty_label = bold(_("Total Completed Qty"))
			qty_to_manufacture = bold(_("Qty to Manufacture"))

			frappe.throw(
				_("The {0} ({1}) must be equal to {2} ({3})").format(
					total_completed_qty_label,
					bold(flt(total_completed_qty, precision)),
					qty_to_manufacture,
					bold(self.for_quantity),
				)
			)

	def set_expected_and_actual_time(self):
		for child_table, start_field, end_field, time_required in [
			("scheduled_time_logs", "expected_start_date", "expected_end_date", "time_required"),
			("time_logs", "actual_start_date", "actual_end_date", "total_time_in_mins"),
		]:
			if not self.get(child_table):
				continue

			time_list = []
			time_in_mins = 0.0
			for row in self.get(child_table):
				time_in_mins += flt(row.get("time_in_mins"))
				for field in ["from_time", "to_time"]:
					if row.get(field):
						time_list.append(get_datetime(row.get(field)))

			if time_list:
				self.set(start_field, min(time_list))
				if end_field == "actual_end_date" and not self.time_logs[-1].to_time:
					self.set(end_field, "")
					return

				self.set(end_field, max(time_list))

			self.set(time_required, time_in_mins)

	def set_process_loss(self):
		if self.work_order and frappe.db.get_value("Work Order", self.work_order, "approval_requested_by"):
			if not self.get("report_request_id"):
				self.process_loss_qty = 0
			return
		precision = self.precision("total_completed_qty")
		should_set_process_loss = self.total_completed_qty or self.process_loss_qty

		self.process_loss_qty = 0.0
		if should_set_process_loss and self.for_quantity > self.total_completed_qty:
			self.process_loss_qty = flt(self.for_quantity, precision) - flt(
				self.total_completed_qty, precision
			)

	def update_work_order(self):
		if not self.work_order:
			return

		if self.is_corrective_job_card and not cint(
			frappe.db.get_single_value(
				"Manufacturing Settings", "add_corrective_operation_cost_in_finished_good_valuation"
			)
		):
			return

		for_quantity, time_in_mins, process_loss_qty = 0, 0, 0
		_from_time_list, _to_time_list = [], []

		data = self.get_current_operation_data()
		if data and len(data) > 0:
			for_quantity = flt(data[0].completed_qty)
			time_in_mins = flt(data[0].time_in_mins)
			process_loss_qty = flt(data[0].process_loss_qty)

		wo = frappe.get_doc("Work Order", self.work_order, for_update=bool(self.get("report_request_id")))

		if self.is_corrective_job_card:
			self.update_corrective_in_work_order(wo)

		elif self.operation_id:
			self.validate_produced_quantity(for_quantity, process_loss_qty, wo)
			self.update_work_order_data(for_quantity, process_loss_qty, time_in_mins, wo)

	def update_corrective_in_work_order(self, wo):
		wo.corrective_operation_cost = 0.0
		for row in frappe.get_all(
			"Job Card",
			fields=["total_time_in_mins", "hour_rate"],
			filters={"is_corrective_job_card": 1, "docstatus": 1, "work_order": self.work_order},
		):
			wo.corrective_operation_cost += (flt(row.total_time_in_mins) / 60) * flt(row.hour_rate)

		wo.calculate_operating_cost()
		wo.flags.ignore_validate_update_after_submit = True
		wo.save()

	def validate_produced_quantity(self, for_quantity, process_loss_qty, wo):
		if self.docstatus < 2:
			return

		if wo.produced_qty > for_quantity + process_loss_qty:
			first_part_msg = _(
				"The {0} {1} is used to calculate the valuation cost for the finished good {2}."
			).format(frappe.bold(_("Job Card")), frappe.bold(self.name), frappe.bold(self.production_item))

			second_part_msg = _(
				"Kindly cancel the Manufacturing Entries first against the work order {0}."
			).format(frappe.bold(get_link_to_form("Work Order", self.work_order)))

			frappe.throw(
				_("{0} {1}").format(first_part_msg, second_part_msg), JobCardCancelError, title=_("Error")
			)

	def update_work_order_data(self, for_quantity, process_loss_qty, time_in_mins, wo):
		workstation_hour_rate = frappe.get_value("Workstation", self.workstation, "hour_rate")
		jc = frappe.qb.DocType("Job Card")
		jctl = frappe.qb.DocType("Job Card Time Log")

		time_query = (
			frappe.qb.from_(jc)
			.from_(jctl)
			.select(Min(jctl.from_time).as_("start_time"), Max(jctl.to_time).as_("end_time"))
			.where(
				(jctl.parent == jc.name)
				& (jc.work_order == self.work_order)
				& (jc.operation_id == self.operation_id)
				& (jc.docstatus == 1)
				& (IfNull(jc.is_corrective_job_card, 0) == 0)
			)
		)
		time_data = (time_query.for_update() if self.get("report_request_id") else time_query).run(as_dict=True)

		for data in wo.operations:
			if data.get("name") == self.operation_id:
				data.completed_qty = for_quantity
				data.process_loss_qty = process_loss_qty
				data.actual_operation_time = time_in_mins
				data.actual_start_time = time_data[0].start_time if time_data else None
				data.actual_end_time = time_data[0].end_time if time_data else None
				if data.get("workstation") != self.workstation:
					# workstations can change in a job card
					data.workstation = self.workstation
					data.hour_rate = flt(workstation_hour_rate)

		wo.flags.ignore_validate_update_after_submit = True
		wo.update_operation_status(self.operation_id)
		wo.calculate_operating_cost()
		wo.set_actual_dates()
		context = getattr(frappe.local, "production_report_context", None)
		if context and context.card is self and context.user == frappe.session.user:
			context.order = wo
			old_permission = wo.flags.ignore_permissions
			try:
				wo.status = wo.get_status()
				wo.save(ignore_permissions=True)
			finally:
				wo.flags.ignore_permissions = old_permission
				context.order = None
		else:
			wo.save()

	def get_current_operation_data(self):
		if self.get("report_request_id"):
			return frappe.db.get_values("Job Card", {"docstatus": 1, "work_order": self.work_order,
				"operation_id": self.operation_id, "is_corrective_job_card": 0},
				["sum(total_time_in_mins) as time_in_mins", "sum(total_completed_qty) as completed_qty", "sum(process_loss_qty) as process_loss_qty"],
				as_dict=True, for_update=True)
		return frappe.get_all(
			"Job Card",
			fields=[
				"sum(total_time_in_mins) as time_in_mins",
				"sum(total_completed_qty) as completed_qty",
				"sum(process_loss_qty) as process_loss_qty",
			],
			filters={
				"docstatus": 1,
				"work_order": self.work_order,
				"operation_id": self.operation_id,
				"is_corrective_job_card": 0,
			},
		)

	def set_transferred_qty_in_job_card_item(self, ste_doc):
		def _get_job_card_items_transferred_qty(ste_doc):
			from frappe.query_builder.functions import Sum

			job_card_items_transferred_qty = {}
			job_card_items = [x.get("job_card_item") for x in ste_doc.get("items") if x.get("job_card_item")]

			if job_card_items:
				se = frappe.qb.DocType("Stock Entry")
				sed = frappe.qb.DocType("Stock Entry Detail")

				query = (
					frappe.qb.from_(sed)
					.join(se)
					.on(sed.parent == se.name)
					.select(sed.job_card_item, Sum(sed.qty))
					.where(
						(sed.job_card_item.isin(job_card_items))
						& (se.docstatus == 1)
						& (se.purpose == "Material Transfer for Manufacture")
					)
					.groupby(sed.job_card_item)
				)

				job_card_items_transferred_qty = frappe._dict(query.run(as_list=True))

			return job_card_items_transferred_qty

		def _validate_over_transfer(row, transferred_qty):
			"Block over transfer of items if not allowed in settings."
			required_qty = frappe.db.get_value("Job Card Item", row.job_card_item, "required_qty")
			is_excess = flt(transferred_qty) > flt(required_qty)
			if is_excess:
				frappe.throw(
					_(
						"Row #{0}: Cannot transfer more than Required Qty {1} for Item {2} against Job Card {3}"
					).format(
						row.idx, frappe.bold(required_qty), frappe.bold(row.item_code), ste_doc.job_card
					),
					title=_("Excess Transfer"),
					exc=JobCardOverTransferError,
				)

		job_card_items_transferred_qty = _get_job_card_items_transferred_qty(ste_doc) or {}
		allow_excess = frappe.db.get_single_value("Manufacturing Settings", "job_card_excess_transfer")

		for row in ste_doc.items:
			if not row.job_card_item:
				continue

			transferred_qty = flt(job_card_items_transferred_qty.get(row.job_card_item, 0.0))

			if not allow_excess:
				_validate_over_transfer(row, transferred_qty)

			frappe.db.set_value("Job Card Item", row.job_card_item, "transferred_qty", flt(transferred_qty))

		self.set_status(update_status=True)

	def set_transferred_qty(self, update_status=False):
		"Set total FG Qty in Job Card for which RM was transferred."
		if not self.items:
			self.transferred_qty = self.for_quantity if self.docstatus == 1 else 0

		doc = frappe.get_doc("Work Order", self.get("work_order"))
		if doc.transfer_material_against == "Work Order" or doc.skip_transfer:
			return

		if self.items:
			# sum of 'For Quantity' of Stock Entries against JC
			self.transferred_qty = (
				frappe.db.get_value(
					"Stock Entry",
					{
						"job_card": self.name,
						"work_order": self.work_order,
						"docstatus": 1,
						"purpose": "Material Transfer for Manufacture",
					},
					"sum(fg_completed_qty)",
				)
				or 0
			)

		self.db_set("transferred_qty", self.transferred_qty)

		qty = 0
		if self.work_order:
			if doc.transfer_material_against == "Job Card" and not doc.skip_transfer:
				min_qty = []
				for d in doc.operations:
					completed_qty = flt(d.completed_qty) + flt(d.process_loss_qty)
					if completed_qty:
						min_qty.append(completed_qty)
					else:
						min_qty = []
						break

				if min_qty:
					qty = min(min_qty)

				doc.db_set("material_transferred_for_manufacturing", qty)

		self.set_status(update_status)

	def set_status(self, update_status=False):
		if self.status == "On Hold" and self.docstatus == 0:
			return

		self.status = {0: "Open", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]

		if self.docstatus < 2:
			if self.items:
				item_data = frappe.get_all(
					"Job Card Item",
					filters={"parent": self.name},
					fields=["transferred_qty", "required_qty"],
				)
				all_transferred = item_data and all(
					flt(d.transferred_qty) >= flt(d.required_qty) for d in item_data
				)
				any_transferred = any(flt(d.transferred_qty) > 0 for d in item_data)

				if all_transferred:
					self.status = "Material Transferred"
				elif any_transferred:
					self.status = "Partially Transferred"
			elif flt(self.for_quantity) <= flt(self.transferred_qty):
				self.status = "Material Transferred"

			if self.time_logs:
				self.status = "Work In Progress"

			completed_qty = flt(
				flt(self.total_completed_qty) + flt(self.process_loss_qty),
				self.precision("total_completed_qty"),
			)
			if self.docstatus == 1 and (self.for_quantity <= completed_qty or not self.items):
				self.status = "Completed"

		if update_status:
			self.db_set("status", self.status)

		if self.status in ["Completed", "Work In Progress"]:
			status = {
				"Completed": "Off",
				"Work In Progress": "Production",
			}.get(self.status)

			self.update_status_in_workstation(status)

	def set_wip_warehouse(self):
		if not self.wip_warehouse:
			self.wip_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_wip_warehouse")

	def validate_operation_id(self):
		if (
			self.get("operation_id")
			and self.get("operation_row_number")
			and self.operation
			and self.work_order
			and frappe.get_cached_value("Work Order Operation", self.operation_row_number, "name")
			!= self.operation_id
		):
			work_order = bold(get_link_to_form("Work Order", self.work_order))
			frappe.throw(
				_("Operation {0} does not belong to the work order {1}").format(
					bold(self.operation), work_order
				),
				OperationMismatchError,
			)

	def validate_sequence_id(self):
		if self.is_corrective_job_card:
			return

		if not (self.work_order and self.sequence_id):
			return

		current_operation_qty = 0.0
		data = self.get_current_operation_data()
		if data and len(data) > 0:
			current_operation_qty = flt(data[0].completed_qty)

		current_operation_qty = flt(
			current_operation_qty + flt(self.total_completed_qty), self.precision("total_completed_qty")
		)

		data = frappe.get_all(
			"Work Order Operation",
			fields=["operation", "status", "completed_qty", "sequence_id"],
			filters={"docstatus": 1, "parent": self.work_order, "sequence_id": ("<", self.sequence_id)},
			order_by="sequence_id, idx",
		)

		message = "Job Card {}: As per the sequence of the operations in the work order {}".format(
			bold(self.name), bold(get_link_to_form("Work Order", self.work_order))
		)

		for row in data:
			if row.status != "Completed" and row.completed_qty < current_operation_qty:
				frappe.throw(
					_("{0}, complete the operation {1} before the operation {2}.").format(
						message, bold(row.operation), bold(self.operation)
					),
					OperationSequenceError,
				)

			if row.completed_qty < current_operation_qty and not (
				row.status == "Completed" and frappe.db.get_value("Work Order", self.work_order, "approval_requested_by")
			):
				frappe.throw(
					_(
						"The completed quantity {0} of an operation {1} cannot be greater than the completed quantity {2} of a previous operation {3}."
					).format(
						bold(current_operation_qty),
						bold(self.operation),
						bold(row.completed_qty),
						bold(row.operation),
					)
				)

	def validate_work_order(self):
		from erpnext.manufacturing.doctype.work_order.work_order import check_production_execution

		before = self.get_doc_before_save()
		if before and before.work_order and before.work_order != self.work_order:
			if check_production_execution(before.work_order, require_team=True):
				frappe.throw("审批工单的任务不能改挂到其他工单", frappe.PermissionError)

		finish = getattr(frappe.local, "production_timer_finish_context", None)
		if finish and finish.card is self and finish.work_order == self.work_order and finish.user == frappe.session.user:
			# The bound server entry has locked/authorized this card and changes only existing open time.
			return

		if self.work_order:
			context = getattr(frappe.local, "production_approval_context", None)
			approval_creating_task = (
				self.is_new() and self.docstatus == 0 and not self.time_logs
				and context and context.name == self.work_order and context.action == "签批通过"
			)
			check_production_execution(self.work_order, require_team=not approval_creating_task)
		if self.is_work_order_closed():
			frappe.throw(_("You can't make any changes to Job Card since Work Order is closed."))

	def is_work_order_closed(self):
		if self.work_order:
			status = frappe.get_value("Work Order", self.work_order, "status")

			if status in ["Closed", "Stopped"]:
				return True

		return False

	def update_status_in_workstation(self, status):
		if not self.workstation:
			return

		frappe.db.set_value("Workstation", self.workstation, "status", status)


@frappe.whitelist()
def make_time_log(args):
	if isinstance(args, str):
		args = json.loads(args)

	args = frappe._dict(args)
	from erpnext.manufacturing.doctype.work_order.work_order import check_production_execution

	work_order = frappe.db.get_value("Job Card", args.job_card_id, "work_order")
	if work_order:
		check_production_execution(work_order, require_team=True, for_update=True)
	doc = frappe.get_doc("Job Card", args.job_card_id, for_update=True)
	if doc.work_order != work_order:
		frappe.throw("作业卡工单关联已变化，请刷新重试", frappe.TimestampMismatchError)
	doc.validate_sequence_id()
	doc.add_time_log(args)


@frappe.whitelist()
def get_operation_details(work_order, operation):
	if work_order and operation:
		frappe.get_doc("Work Order", work_order).check_permission("read")
		return frappe.get_all(
			"Work Order Operation",
			fields=["name", "idx"],
			filters={"parent": work_order, "operation": operation},
		)


@frappe.whitelist()
def get_operations(doctype, txt, searchfield, start, page_len, filters=None):
	filters = frappe.parse_json(filters)
	if filters is not None and not isinstance(filters, dict):
		frappe.throw(_("工单筛选条件必须是对象。"))
	if not filters or not filters.get("work_order"):
		frappe.msgprint(_("Please select a Work Order first."))
		return []
	frappe.get_doc("Work Order", filters["work_order"]).check_permission("read")
	args = {"parent": filters.get("work_order")}
	if txt:
		args["operation"] = ("like", f"%{txt}%")

	return frappe.get_all(
		"Work Order Operation",
		filters=args,
		fields=["distinct operation as operation"],
		limit_start=start,
		limit_page_length=page_len,
		order_by="idx asc",
		as_list=1,
	)


@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.warehouse = source_parent.wip_warehouse

	def set_missing_values(source, target):
		target.material_request_type = "Material Transfer"

	doclist = get_mapped_doc(
		"Job Card",
		source_name,
		{
			"Job Card": {
				"doctype": "Material Request",
				"field_map": {
					"name": "job_card",
				},
			},
			"Job Card Item": {
				"doctype": "Material Request Item",
				"field_map": {"required_qty": "qty", "uom": "stock_uom", "name": "job_card_item"},
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_stock_entry(source_name: str, target_doc: Document | str | None = None):
	def update_item(source, target, source_parent):
		target.t_warehouse = source_parent.wip_warehouse

		if not target.conversion_factor:
			target.conversion_factor = 1

		pending_rm_qty = flt(source.required_qty) - flt(source.transferred_qty)
		if pending_rm_qty > 0:
			target.qty = pending_rm_qty

	def set_missing_values(source, target):
		if not source.items:
			frappe.throw(_("This Job Card has no raw materials to transfer."))

		target.purpose = "Material Transfer for Manufacture"
		target.from_bom = 1

		# avoid negative 'For Quantity'
		pending_fg_qty = flt(source.get("for_quantity", 0)) - flt(source.get("transferred_qty", 0))
		target.fg_completed_qty = pending_fg_qty if pending_fg_qty > 0 else 0

		target.set_missing_values()
		target.set_stock_entry_type()

		wo_allows_alternate_item = frappe.db.get_value(
			"Work Order", target.work_order, "allow_alternative_item"
		)
		for item in target.items:
			item.allow_alternative_item = int(
				wo_allows_alternate_item
				and frappe.get_cached_value("Item", item.item_code, "allow_alternative_item")
			)

	doclist = get_mapped_doc(
		"Job Card",
		source_name,
		{
			"Job Card": {
				"doctype": "Stock Entry",
				"field_map": {"name": "job_card", "for_quantity": "fg_completed_qty"},
			},
			"Job Card Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"source_warehouse": "s_warehouse",
					"required_qty": "qty",
					"name": "job_card_item",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.required_qty > 0,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


def time_diff_in_minutes(string_ed_date, string_st_date):
	return time_diff(string_ed_date, string_st_date).total_seconds() / 60


@frappe.whitelist()
def get_job_details(start: str, end: str, filters: str | None = None):
	events = []

	event_color = {
		"Completed": "#cdf5a6",
		"Material Transferred": "#ffdd9e",
		"Partially Transferred": "#ffe5b4",
		"Work In Progress": "#D3D3D3",
	}

	from frappe.desk.reportview import get_filters_cond

	frappe.has_permission("Job Card", "read", throw=True)
	conditions = get_filters_cond("Job Card", filters, [])
	# List access can grant select without read; confirm actual document reads.
	readable_names = [
		card.name
		for card in frappe.get_list("Job Card", fields=["name"], limit_page_length=0)
		if frappe.has_permission("Job Card", "read", doc=card.name)
	]
	if not readable_names:
		return []
	conditions += get_filters_cond("Job Card", {"name": ["in", readable_names]}, [])

	job_cards = frappe.db.sql(
		f""" SELECT `tabJob Card`.name, `tabJob Card`.work_order,
			`tabJob Card`.status, ifnull(`tabJob Card`.remarks, ''),
			min(`tabJob Card Time Log`.from_time) as from_time,
			max(`tabJob Card Time Log`.to_time) as to_time
		FROM `tabJob Card` , `tabJob Card Time Log`
		WHERE
			`tabJob Card`.name = `tabJob Card Time Log`.parent {conditions}
			group by `tabJob Card`.name""",
		as_dict=1,
	)

	for d in job_cards:
		subject_data = []
		for field in ["name", "work_order", "remarks"]:
			if not d.get(field):
				continue

			subject_data.append(d.get(field))

		color = event_color.get(d.status)
		job_card_data = {
			"from_time": d.from_time,
			"to_time": d.to_time,
			"name": d.name,
			"subject": "\n".join(subject_data),
			"color": color if color else "#89bcde",
		}

		events.append(job_card_data)

	return events


@frappe.whitelist()
def make_corrective_job_card(source_name, operation=None, for_operation=None, target_doc=None):
	def set_missing_values(source, target):
		target.is_corrective_job_card = 1
		target.operation = operation
		target.for_operation = for_operation

		target.set("time_logs", [])
		target.set("employee", [])
		target.set("items", [])
		target.set("sub_operations", [])
		target.set_sub_operations()
		target.get_required_items()
		target.validate_time_logs()

	doclist = get_mapped_doc(
		"Job Card",
		source_name,
		{
			"Job Card": {
				"doctype": "Job Card",
				"field_map": {
					"name": "for_job_card",
				},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist


def _non_negative_number(value, label):
	try:
		number = Decimal(str(value))
	except InvalidOperation:
		frappe.throw(f"{label}必须是有效数字。")
	if not number.is_finite() or number < 0:
		frappe.throw(f"{label}必须是有限的非负数字。")
	return number


def _whole_non_negative(value, label):
	number = _non_negative_number(value, label)
	if number != number.to_integral_value():
		frappe.throw(f"{label}必须是非负整数。")
	return int(number)


def _report_datetime(value, label):
	if not isinstance(value, (str, datetime.datetime)) or not value:
		frappe.throw(f"{label}必须填写日期和时间。")
	try:
		parsed = get_datetime(value)
	except (TypeError, ValueError):
		frappe.throw(f"{label}不是有效的日期时间。")
	if not isinstance(parsed, datetime.datetime):
		frappe.throw(f"{label}不是有效的日期时间。")
	zone = ZoneInfo("Asia/Shanghai")
	return parsed.replace(tzinfo=zone) if parsed.tzinfo is None else parsed.astimezone(zone)


def _daily_overlap(start, end, periods):
	"""Union and clip daily intervals, preserving fractions for rule matching."""
	if not isinstance(periods, list):
		frappe.throw("时段规则必须提供时段列表。")
	intervals = []
	for period in periods:
		if not isinstance(period, (list, tuple)) or len(period) != 2:
			frappe.throw("每个规则时段必须包含开始和结束时刻。")
		if any(not isinstance(v, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", v) for v in period):
			frappe.throw("规则时刻必须使用有效的HH:mm格式。")
		left, right = [int(v[:2]) * 3600 + int(v[3:]) * 60 for v in period]
		if left < right:
			intervals.append((left, right))
		elif left > right:
			intervals.extend(((left, 86400), (0, right)))
	merged = []
	for left, right in sorted(intervals):
		if merged and left <= merged[-1][1]:
			merged[-1][1] = max(merged[-1][1], right)
		else:
			merged.append([left, right])
	total = datetime.timedelta()
	day = start.replace(hour=0, minute=0, second=0, microsecond=0)
	while day < end:
		for left, right in merged:
			clip_start = max(start, day + datetime.timedelta(seconds=left))
			clip_end = min(end, day + datetime.timedelta(seconds=right))
			if clip_end > clip_start:
				total += clip_end - clip_start
		day += datetime.timedelta(days=1)
	return total


def calculate_report_time(start, end, *, rules, operation=None, shutdown_seconds=0, overtime_seconds=0):
	"""Internal calculation only. B14 supplies authorized rules; B08 owns confirmation."""
	start, end = _report_datetime(start, "开始时间"), _report_datetime(end, "结束时间")
	if end < start:
		frappe.throw("结束时间不能早于开始时间，请明确填写日期。")
	if not isinstance(rules, list):
		frappe.throw("缺少有效时段规则上下文；确认无规则时请明确提供空列表。")
	reported = (end - start) // datetime.timedelta(seconds=1)
	shutdown = _whole_non_negative(shutdown_seconds, "停工秒数")
	overtime = _whole_non_negative(overtime_seconds, "加班秒数")
	candidates = []
	for rule in rules:
		if not isinstance(rule, dict) or not {"name", "priority", "enabled", "operation", "rest_periods", "overtime_periods"} <= rule.keys():
			frappe.throw("时段规则字段不完整，不能按无规则处理。")
		if not isinstance(rule["name"], str) or not rule["name"].strip() or rule["enabled"] not in (0, 1):
			frappe.throw("时段规则名称或启用状态无效。")
		if rule["operation"] is not None and not isinstance(rule["operation"], str):
			frappe.throw("规则适用工序必须是明确的工序标识。")
		priority = _whole_non_negative(rule["priority"], "规则优先级")
		if not rule["enabled"]:
			continue
		rest = _daily_overlap(start, end, rule["rest_periods"])
		allowed = _daily_overlap(start, end, rule["overtime_periods"])
		if (rule["operation"] is None or rule["operation"] == operation) and (rest or allowed):
			second = datetime.timedelta(seconds=1)
			candidates.append((priority, rule["name"], rest // second, allowed // second))
	matched, rest, allowed = None, 0, reported
	if candidates:
		_, matched, rest, allowed = min(candidates)
	shutdown_limit = reported - rest
	for value, limit, label in ((shutdown, shutdown_limit, "停工"), (overtime, allowed, "加班")):
		if value > limit:
			frappe.throw(f"{label}时长不能超过{limit // 3600}小时{limit % 3600 // 60}分钟{limit % 60}秒。")
	return {"reported_seconds": reported, "rest_seconds": rest, "shutdown_seconds": shutdown,
		"overtime_seconds": overtime, "shutdown_limit_seconds": shutdown_limit,
		"overtime_limit_seconds": allowed, "effective_seconds": reported - rest - shutdown + overtime,
		"matched_rule": matched, "timezone": "Asia/Shanghai",
		"rule_message": "已匹配时段规则。" if matched else "未匹配时段规则：休息为0，加班上限为报工时长。"}


def calculate_report_metrics(*, plan_quantity=None, good_quantity, bad_quantity, effective_seconds,
	completed_tasks=None, total_tasks=None, issued_quantity=None, required_quantity=None, rework_quantity=0,
	standard_efficiency=None, wage_mode=None, wage_rate=None):
	"""Calculate from authorized effective facts; never infer defects or post wages."""
	from erpnext.manufacturing.doctype.bom.bom import validate_quantity_input

	quantities = {}
	for key, value, label in (("good", good_quantity, "良品数量"),
		("bad", bad_quantity, "不良数量"), ("rework", rework_quantity, "返工数量")):
		quantities[key] = Decimal(str(validate_quantity_input(value, label, allow_zero=True)))
	plan = None if plan_quantity is None else Decimal(str(validate_quantity_input(plan_quantity, "计划数量", allow_zero=True)))
	seconds = _whole_non_negative(effective_seconds, "有效工时秒数")
	completion = material = None
	if (completed_tasks is None) != (total_tasks is None) or (issued_quantity is None) != (required_quantity is None):
		frappe.throw("任务或领料指标的分子与分母必须同时提供。")
	if total_tasks is not None:
		done = _whole_non_negative(completed_tasks, "已完成任务数")
		total = _whole_non_negative(total_tasks, "任务总数")
		if done > total:
			frappe.throw("已完成任务数不能超过任务总数。")
		completion = Decimal(done) * 100 / total if total else None
	if required_quantity is not None:
		issued = Decimal(str(validate_quantity_input(issued_quantity, "生效累计领料", allow_zero=True)))
		required = Decimal(str(validate_quantity_input(required_quantity, "需求数量", allow_zero=True)))
		material = issued * 100 / required if required else None
	standard = None if standard_efficiency is None else _non_negative_number(standard_efficiency, "标准效率")
	actual = quantities["good"] + quantities["bad"]
	efficiency = actual * 3600 / seconds if seconds else None
	estimated_wage = None
	if wage_mode is not None:
		if wage_mode not in ("hourly", "piece"):
			frappe.throw("计价方式必须明确为计时或计件。")
		rate = _non_negative_number(wage_rate, "工资单价")
		estimated_wage = Decimal(seconds) * rate / 3600 if wage_mode == "hourly" else quantities["good"] * rate
	elif wage_rate is not None:
		frappe.throw("填写工资单价时必须明确计价方式。")
	return {"quality_percent": quantities["good"] * 100 / actual if actual else None,
		"quality_numerator": quantities["good"], "quality_denominator": actual,
		"unfinished_quantity": max(Decimal(0), plan - actual) if plan is not None else None,
		"task_completion_percent": completion,
		"material_issue_percent": material,
		"actual_efficiency": efficiency,
		"efficiency_percent": efficiency * 100 / standard if efficiency is not None and standard else None,
		"estimated_wage": estimated_wage}


def _report_metrics_source(order, operation):
	from frappe.model.meta import get_field_precision
	from erpnext.manufacturing.doctype.bom.bom import validate_quantity_input

	mode = operation.get("report_wage_mode") or None
	rate, standard = operation.get("report_wage_rate"), operation.get("report_standard_efficiency")
	if mode not in (None, "hourly", "piece") or bool(mode) != (rate not in (None, "")):
		frappe.throw("工序计价配置不完整，请核对已批准的工单依据")
	values = []
	for value, label in ((rate, "工资单价"), (standard, "标准效率")):
		if value in (None, ""):
			values.append(None)
		else:
			validate_quantity_input(value, label, allow_zero=True)
			values.append(format(Decimal(str(value)).normalize(), "f"))
	currency = operation.get("report_wage_currency") if mode else None
	if mode and not currency:
		frappe.throw("缺少工序计价币种，不能用当前公司设置替代已批准依据")
	return {"calculation_version": "B08-metrics-v1", "work_order": order.name,
		"operation_id": operation.name, "operation": operation.operation, "unit": order.stock_uom,
		"wage_mode": mode, "wage_rate": values[0], "currency": currency,
		"currency_precision": get_field_precision(frappe._dict(fieldtype="Currency"), currency=currency),
		"standard_efficiency": values[1]}


def _report_metrics(source, good, bad, seconds):
	# Only this report's metrics are requested; no fabricated task or material totals.
	result = calculate_report_metrics(good_quantity=good,
		bad_quantity=bad, effective_seconds=seconds, standard_efficiency=source["standard_efficiency"],
		wage_mode=source["wage_mode"], wage_rate=source["wage_rate"])
	wage = result["estimated_wage"]
	result = {key: None if result[key] is None else format(result[key].quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP).normalize(), "f")
		for key in ("actual_efficiency", "efficiency_percent")}
	result["estimated_wage"] = None if wage is None else format(wage.quantize(Decimal(1).scaleb(-source["currency_precision"]), rounding=ROUND_HALF_UP), "f")
	return {"source": source, "result": result}


def _saved_report_metrics(doc):
	if not doc.get("report_metrics_context"):
		return None
	metrics = _report_metrics(frappe.parse_json(doc.report_metrics_context), Decimal(str(doc.total_completed_qty or 0)),
		Decimal(str(doc.process_loss_qty or 0)), doc.report_effective_seconds)
	# Reopening displays the saved amount. Derived percentages use saved facts and basis only.
	metrics["result"]["estimated_wage"] = doc.get("report_estimated_wage") or None
	return metrics


def _report_scope_allows(operation, employee):
	scope = operation.get("report_scope")
	return (scope == "ALL" or scope == "PERSON" and operation.report_employee == employee.name
		or scope == "DEPT" and operation.report_department and operation.report_department == employee.department)


def _report_context(work_order, *, history=False, for_update=False):
	from erpnext.manufacturing.doctype.work_order.work_order import check_production_execution, _check_production_approval_scope

	if "生产报工" not in frappe.get_roles():
		frappe.throw("没有生产报工权限", frappe.PermissionError)
	if history:
		order = frappe.get_doc("Work Order", work_order, for_update=for_update)
		order.check_permission("read")
		_check_production_approval_scope(order, team_required=True)
	else:
		order = check_production_execution(work_order, require_team=True, for_update=for_update)
	if not order or not order.get("approval_requested_by"):
		frappe.throw("存量工单未确认审批依据，不能报工", frappe.PermissionError)
	employees = frappe.get_all("Employee", filters={"user_id": frappe.session.user, "status": "Active", "company": order.company}, fields=["name", "department"])
	if len(employees) != 1:
		frappe.throw("缺少唯一有效员工，不能报工", frappe.PermissionError)
	return order, employees[0]


def _report_task(work_order, operation_id, *, history=False, for_update=False):
	order, employee = _report_context(work_order, history=history, for_update=for_update)
	operation = next((row for row in order.operations if row.name == operation_id), None)
	if not operation or not _report_scope_allows(operation, employee):
		frappe.throw("没有本道工序的报工授权", frappe.PermissionError)
	return order, operation, employee


@frappe.whitelist()
def get_production_report_tasks(work_order):
	order, employee = _report_context(work_order, history=True)
	tasks = []
	for row in order.operations:
		if _report_scope_allows(row, employee):
			plan = order.get_operation_plan_quantity(row)
			tasks.append({"name": row.name, "operation": row.operation, "plan": plan, "good": row.completed_qty,
				"bad": row.process_loss_qty, "unfinished": max(Decimal(0), Decimal(str(plan)) - Decimal(str(row.completed_qty or 0)) - Decimal(str(row.process_loss_qty or 0))),
				"status": row.status})
	reports = frappe.get_list("Job Card", filters={"work_order": work_order, "operation_id": ["in", [t["name"] for t in tasks]],
		"report_request_id": ["is", "set"]}, fields=["name", "operation_id", "total_completed_qty", "process_loss_qty", "report_effective_seconds", "docstatus", "amended_from"],
		order_by="creation desc", limit_page_length=50) if tasks else []
	return {"tasks": tasks, "reports": reports, "unit": order.stock_uom, "employee": employee.name}


@frappe.whitelist()
def get_production_report_result(request_id):
	name = frappe.db.get_value("Job Card", {"report_request_id": request_id}, "name")
	if not name:
		return None
	doc = frappe.get_doc("Job Card", name)
	if doc.owner != frappe.session.user:
		frappe.throw("不能查询他人的报工请求", frappe.PermissionError)
	# Existing evidence follows current object visibility, not new-work task assignment.
	_report_context(doc.work_order, history=True)
	doc.check_permission("read")
	return {"name": doc.name, "docstatus": doc.docstatus, "good": doc.total_completed_qty, "bad": doc.process_loss_qty,
		"time_context": frappe.parse_json(doc.report_time_context), "metrics": _saved_report_metrics(doc)}


def _report_time_context(order, operation, from_time, to_time, shutdown_seconds, overtime_seconds):
	from erpnext.manufacturing.doctype.production_time_rule.production_time_rule import load_report_time_rules

	if frappe.db.exists("Sub Operation", {"parent": operation.operation, "parenttype": "Operation"}):
		frappe.throw("该任务含子工序，本轮逐笔报工暂不支持，请先核对任务配置")
	rules = load_report_time_rules(order.company, operation.operation)
	result = calculate_report_time(from_time, to_time, rules=rules, operation=operation.operation,
		shutdown_seconds=shutdown_seconds, overtime_seconds=overtime_seconds)
	context = {"calculation_version": "B04-time-v1", "company": order.company, "operation": operation.operation,
		"rule": next((r for r in rules if r["name"] == result["matched_rule"]), None), "result": result}
	fingerprint = hashlib.sha256(frappe.as_json(context).encode()).hexdigest()
	return context, fingerprint


@frappe.whitelist()
def preview_production_report_time(work_order, operation_id, from_time, to_time, shutdown_seconds=0, overtime_seconds=0,
	good_quantity=None, bad_quantity=None):
	from erpnext.manufacturing.doctype.bom.bom import validate_quantity_input

	order, operation, employee = _report_task(work_order, operation_id)
	context, fingerprint = _report_time_context(order, operation, from_time, to_time, shutdown_seconds, overtime_seconds)
	source = _report_metrics_source(order, operation)
	fingerprint = hashlib.sha256(frappe.as_json({"time":context,"metrics_source":source}).encode()).hexdigest()
	metrics = None
	if good_quantity is not None or bad_quantity is not None:
		good = Decimal(str(validate_quantity_input(good_quantity, "良品数量", allow_zero=True)))
		bad = Decimal(str(validate_quantity_input(bad_quantity, "不良数量", allow_zero=True)))
		metrics = _report_metrics(source, good, bad, context["result"]["effective_seconds"])
	return {"context_fingerprint": fingerprint, "metrics": metrics, **context["result"]}


@frappe.whitelist()
def confirm_production_report(work_order, operation_id, request_id, good_quantity, bad_quantity,
	from_time, to_time, context_fingerprint, shutdown_seconds=0, overtime_seconds=0):
	return _confirm_production_report(work_order, operation_id, request_id, good_quantity, bad_quantity,
		from_time, to_time, context_fingerprint, shutdown_seconds, overtime_seconds)


@frappe.whitelist()
def correct_production_report(original_job_card, request_id, good_quantity, bad_quantity, reason):
	original = frappe.get_doc("Job Card", original_job_card)
	original.check_permission("read")
	original.check_permission("cancel")
	if not original.get("report_request_id") or not isinstance(reason, str) or not reason.strip():
		frappe.throw("请选择原报工并填写更正原因")
	frappe.db.get_value("Work Order", original.work_order, "name", for_update=True)
	original = frappe.get_doc("Job Card", original.name, for_update=True)
	line = original.time_logs[0]
	return _confirm_production_report(original.work_order, original.operation_id, request_id, good_quantity,
		bad_quantity, line.from_time, line.to_time, None, original.report_shutdown_seconds,
		original.report_overtime_seconds, original=original, correction_reason=reason.strip())


def _confirm_production_report(work_order, operation_id, request_id, good_quantity, bad_quantity,
	from_time, to_time, context_fingerprint, shutdown_seconds=0, overtime_seconds=0, *, original=None, correction_reason=None):
	"""A single native Job Card in the request transaction; no internal commit."""
	from erpnext.manufacturing.doctype.bom.bom import validate_quantity_input

	if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", request_id):
		frappe.throw("报工请求编号无效，请重新打开报工页面")
	# Lock the existing parent before checking current scope and before native child/workstation writes.
	frappe.db.get_value("Work Order", work_order, "name", for_update=True)
	order, operation, employee = _report_task(work_order, operation_id, history=True, for_update=True)
	good = Decimal(str(validate_quantity_input(good_quantity, "良品数量", allow_zero=True)))
	bad = Decimal(str(validate_quantity_input(bad_quantity, "不良数量", allow_zero=True)))
	quantity = validate_quantity_input(good + bad, "本次数量")
	start, end = _report_datetime(from_time, "开始时间"), _report_datetime(to_time, "结束时间")
	payload = {"user": frappe.session.user, "work_order": work_order, "operation_id": operation_id,
		"good": format(good.normalize(), "f"), "bad": format(bad.normalize(), "f"), "from": start.isoformat(), "to": end.isoformat(),
		"shutdown": _whole_non_negative(shutdown_seconds, "停工秒数"), "overtime": _whole_non_negative(overtime_seconds, "加班秒数"),
		"context_fingerprint": context_fingerprint, "original": original.name if original else None, "correction_reason": correction_reason}
	payload_hash = hashlib.sha256(frappe.as_json(payload).encode()).hexdigest()
	existing = frappe.db.get_value("Job Card", {"report_request_id": request_id}, ["name", "report_payload_hash", "owner", "docstatus"], as_dict=True, for_update=True)
	if existing:
		if existing.owner != frappe.session.user or existing.report_payload_hash != payload_hash:
			frappe.throw("请求编号已用于其他报工内容，不能覆盖原记录", frappe.PermissionError)
		frappe.get_doc("Job Card", existing.name, for_update=True).check_permission("read")
		return {"name": existing.name, "docstatus": existing.docstatus}
	from erpnext.manufacturing.doctype.work_order.work_order import validate_production_execution_state
	validate_production_execution_state(order)
	if operation.status == "Completed" and not original:
		frappe.throw("本道工序已经完成，请核对已有报工")
	if original:
		if original.docstatus != 1:
			frappe.throw("原报工已被更正或取消，请核对当前记录", frappe.PermissionError)
		if frappe.db.exists("Stock Entry", {"work_order": work_order, "docstatus": 1}):
			frappe.throw("本轮只支持无库存后续单据的全冲更正，请先处理关联库存单据")
		downstream = [row.name for row in order.operations if row.idx > operation.idx]
		if downstream and frappe.db.get_values("Job Card", {"work_order": work_order, "docstatus": 1,
			"operation_id": ["in", downstream]}, "name", for_update=True):
			frappe.throw("已有后工序报工，请先处理后工序记录后再更正，原报工未改变")
		context = frappe.parse_json(original.report_time_context)
		context["original_report"] = original.name
		context["rule_basis"] = "沿用原报工时段依据，起止时间不变"
		source = frappe.parse_json(original.report_metrics_context) if original.get("report_metrics_context") else None
	else:
		context, fingerprint = _report_time_context(order, operation, from_time, to_time, shutdown_seconds, overtime_seconds)
		source = _report_metrics_source(order, operation)
		fingerprint = hashlib.sha256(frappe.as_json({"time":context,"metrics_source":source}).encode()).hexdigest()
		if fingerprint != context_fingerprint:
			frappe.throw("时段依据已变化，请重新核对工时后确认")
	context["confirmed_at"] = frappe.utils.now()
	metrics = _report_metrics(source, good, bad, context["result"]["effective_seconds"]) if source else None
	doc = frappe.get_doc({"doctype": "Job Card", "amended_from": original.name if original else None, "correction_reason": correction_reason,
		"work_order": work_order, "operation_id": operation_id,
		"operation": operation.operation, "sequence_id": operation.sequence_id, "workstation": operation.workstation,
		"workstation_type": operation.workstation_type, "company": order.company, "production_item": order.production_item,
		"bom_no": order.bom_no, "wip_warehouse": order.wip_warehouse, "for_quantity": quantity, "process_loss_qty": float(bad), "hour_rate": operation.hour_rate,
		"report_request_id": request_id, "report_payload_hash": payload_hash, "report_time_context": frappe.as_json(context),
		"report_shutdown_seconds": payload["shutdown"], "report_overtime_seconds": payload["overtime"],
		"report_effective_seconds": context["result"]["effective_seconds"], "report_time_rule": context["result"]["matched_rule"],
		"report_metrics_context": frappe.as_json(source) if source else None,
		"report_estimated_wage": metrics["result"]["estimated_wage"] if metrics else None,
		"time_logs": [{"from_time": start.replace(tzinfo=None), "to_time": end.replace(tzinfo=None),
			"completed_qty": float(good), "employee": employee.name}]})
	previous = getattr(frappe.local, "production_report_context", None)
	frappe.local.production_report_context = frappe._dict(card=doc, user=frappe.session.user, order=None, operation_id=operation_id)
	try:
		if original:
			frappe.local.production_report_context.card = original
			original.cancel()
			frappe.local.production_report_context.card = doc
		doc.insert()
		doc.submit()
	finally:
		frappe.local.production_report_context = previous
	return {"name": doc.name, "docstatus": doc.docstatus}
