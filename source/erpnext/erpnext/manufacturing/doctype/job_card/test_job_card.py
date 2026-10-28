# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from typing import Literal

import frappe
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import flt, random_string
from frappe.utils.data import add_to_date, now, today

from erpnext.manufacturing.doctype.job_card.job_card import (
	JobCardOverTransferError,
	OperationMismatchError,
	OverlapError,
	get_job_details,
	get_operation_details,
	get_operations,
	make_corrective_job_card,
	make_material_request,
)
from erpnext.manufacturing.doctype.job_card.job_card import (
	make_stock_entry as make_stock_entry_from_jc,
)
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder, make_job_card
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestJobCardExecutionApproval(FrappeTestCase):
	def setUp(self):
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_approval_execution_fixture
		self.f = make_approval_execution_fixture(self)

	def approve(self):
		self.f.act("operator", "送审")
		self.f.act("reviewer", "审核通过")
		with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
			self.f.act("director", "签批通过")
		return frappe.get_doc("Job Card", {"work_order": self.f.order.name, "operation": self.f.operations[0]})

	def start(self, card):
		from erpnext.manufacturing.doctype.job_card.job_card import make_time_log
		make_time_log({"job_card_id": card.name, "start_time": now(), "status": "Work In Progress", "employees": []})

	def test_execution_fixture_runnable(self):
		self.f.legacy_order.reload()
		self.assertEqual(self.f.legacy_order.workflow_state, "存量待核")
		self.assertEqual(self.f.legacy_card.docstatus, 0)
		self.assertFalse(self.f.legacy_card.time_logs)
		self.assertEqual(self.f.order.workflow_state, "草稿")

	def test_pending_manual_job_card_denied(self):
		from erpnext.manufacturing.doctype.work_order.work_order import create_job_card
		order = self.f.order
		card = create_job_card(order, order.operations[0].as_dict())
		card.for_quantity = 1
		with self.assertRaises(frappe.PermissionError):
			card.insert()
		self.assertFalse(frappe.db.exists("Job Card", {"work_order": order.name}))

	def test_pending_make_job_card_denied(self):
		order = self.f.order
		row = order.operations[0].as_dict()
		row.update(qty=1, pending_qty=10)
		with self.assertRaises(frappe.PermissionError):
			make_job_card(order.name, [row])
		self.assertFalse(frappe.db.exists("Job Card", {"work_order": order.name}))

	def test_unapproved_legacy_timer_denied(self):
		with self.assertRaises(frappe.PermissionError):
			self.start(self.f.legacy_card)
		self.f.legacy_card.reload()
		self.assertFalse(self.f.legacy_card.time_logs)

	def test_unapproved_legacy_report_denied(self):
		card = self.f.legacy_card
		card.append("time_logs", {"from_time": add_to_date(now(), minutes=-1), "to_time": now(), "completed_qty": card.for_quantity})
		with self.assertRaises(frappe.PermissionError):
			card.submit()
		card.reload()
		self.assertEqual(card.docstatus, 0)
		self.assertFalse(card.time_logs)

	def test_approved_task_and_timer_allowed(self):
		card = self.approve()
		frappe.set_user(self.f.users["operator"])
		self.start(card)
		card.reload()
		self.assertEqual(len(card.time_logs), 1)
		self.assertEqual(card.docstatus, 0)
		self.assertEqual(card.total_completed_qty, 0)

	def test_cross_team_timer_denied(self):
		card = self.approve()
		frappe.set_user(self.f.users["other"])
		with self.assertRaises(frappe.PermissionError):
			self.start(card)
		card.reload()
		self.assertFalse(card.time_logs)

	def test_disabled_workflow_timer_denied(self):
		card = self.approve()
		frappe.set_user("Administrator")
		self.f.workflow.is_active = 0
		self.f.workflow.save()
		frappe.set_user(self.f.users["operator"])
		with self.assertRaises(frappe.PermissionError):
			self.start(card)
		card.reload()
		self.assertFalse(card.time_logs)

	def test_clearing_work_order_cannot_detach_task(self):
		card = self.approve()
		frappe.set_user(self.f.users["operator"])
		card.work_order = None
		with self.assertRaises((frappe.PermissionError, frappe.MandatoryError)):
			card.save()
		card.reload()
		self.assertEqual(card.work_order, self.f.order.name)


	def test_task_cannot_borrow_another_approved_order(self):
		self.approve()
		frappe.set_user(self.f.users["operator"])
		card = self.f.legacy_card
		card.work_order = self.f.order.name
		with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
			card.save()
		card.reload()
		self.assertEqual(card.work_order, self.f.legacy_order.name)


class TestJobCardReadPermissions(FrappeTestCase):
	"""Helper reads must obey the same native object grants as document reads."""

	def setUp(self):
		from frappe.permissions import add_permission, add_user_permission

		import erpnext

		frappe.set_user("Administrator")
		self.prefix = "B02-" + random_string(8)
		company = erpnext.get_default_company()
		warehouse = (
			frappe.get_doc({"doctype": "Warehouse", "warehouse_name": self.prefix, "company": company})
			.insert()
			.name
		)
		raw = create_item(self.prefix + "-RM", company=company, warehouse=warehouse)
		finished = create_item(self.prefix + "-FG", company=company, warehouse=warehouse)
		bom = make_bom(
			item=finished.name,
			company=company,
			currency=frappe.get_cached_value("Company", company, "default_currency"),
			raw_materials=[raw.name],
			rm_qty=1,
			with_operations=False,
		)
		workstation = make_workstation(workstation_name=self.prefix).name
		self.operations = [
			frappe.get_doc({"doctype": "Operation", "__newname": self.prefix + suffix}).insert().name
			for suffix in ("-下料", "-检验")
		]
		self.orders = []
		self.cards = []
		for index in range(2):
			order = make_wo_order_test_record(
				item=finished.name,
				bom_no=bom.name,
				qty=10,
				company=company,
				stock_uom="Nos",
				source_warehouse=warehouse,
				wip_warehouse=warehouse,
				fg_warehouse=warehouse,
				do_not_save=True,
			)
			for operation in self.operations:
				order.append(
					"operations", {"operation": operation, "workstation": workstation, "time_in_mins": 1}
				)
			order.insert()
			self.orders.append(order)
			card = frappe.get_doc(
				{
					"doctype": "Job Card",
					"work_order": order.name,
					"company": company,
					"workstation": workstation,
					"wip_warehouse": warehouse,
					"operation": self.operations[0],
					"operation_id": order.operations[0].name,
					"for_quantity": 1,
					"remarks": self.prefix + ("-可见" if index == 0 else "-受限"),
					"time_logs": [
						{
							"from_time": f"2026-10-{20 + index} 08:00:00",
							"to_time": f"2026-10-{20 + index} 08:01:00",
						}
					],
				}
			).insert()
			self.cards.append(card)
		self.role = (
			frappe.get_doc({"doctype": "Role", "role_name": self.prefix, "desk_access": 1}).insert().name
		)
		for doctype in ("Work Order", "Job Card"):
			add_permission(doctype, self.role, ptype="read")
		self.reader = frappe.get_doc(
			{
				"doctype": "User",
				"email": self.prefix.lower() + "@example.invalid",
				"first_name": "权限验证员",
				"send_welcome_email": 0,
				"language": "zh",
				"roles": [{"role": self.role}],
			}
		).insert()
		self.outsider = frappe.get_doc(
			{
				"doctype": "User",
				"email": self.prefix.lower() + "-outside@example.invalid",
				"first_name": "无权限对照",
				"send_welcome_email": 0,
				"language": "zh",
			}
		).insert()
		add_user_permission("Work Order", self.orders[0].name, self.reader.name)
		frappe.set_user(self.reader.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.clear_cache()

	def test_read_fixture_and_authorized_helpers(self):
		self.orders[0].check_permission("read")
		with self.assertRaises(frappe.PermissionError):
			self.orders[1].check_permission("read")
		self.assertFalse(frappe.has_permission("Stock Entry", "create"))
		self.assertEqual(
			get_operation_details(self.orders[0].name, self.operations[0]),
			[{"name": self.orders[0].operations[0].name, "idx": 1}],
		)
		self.assertEqual(
			[
				row[0]
				for row in get_operations(
					"Operation", "检验", "name", 0, 1, {"work_order": self.orders[0].name}
				)
			],
			[self.operations[1]],
		)
		self.assertEqual(
			[
				row[0]
				for row in get_operations("Operation", "", "name", 1, 1, {"work_order": self.orders[0].name})
			],
			[self.operations[1]],
		)

	def test_operation_helpers_reject_other_work_order(self):
		with self.assertRaises(frappe.PermissionError):
			get_operation_details(self.orders[1].name, self.operations[0])
		with self.assertRaises(frappe.PermissionError):
			get_operations("Operation", "", "name", 0, 20, {"work_order": self.orders[1].name})

	def test_helpers_reject_user_without_business_role(self):
		frappe.set_user(self.outsider.name)
		with self.assertRaises(frappe.PermissionError):
			get_operation_details(self.orders[0].name, self.operations[0])
		with self.assertRaises(frappe.PermissionError):
			get_operations("Operation", "", "name", 0, 20, {"work_order": self.orders[0].name})
		with self.assertRaises(frappe.PermissionError):
			get_job_details("2026-10-19", "2026-10-22")

	def test_calendar_contains_only_readable_cards(self):
		events = get_job_details("2026-10-19", "2026-10-22")
		self.assertEqual({event["name"] for event in events}, {self.cards[0].name})
		self.assertEqual(str(events[0]["from_time"]), "2026-10-20 08:00:00")
		self.assertEqual(str(events[0]["to_time"]), "2026-10-20 08:01:00")
		self.assertIn(self.orders[0].name, events[0]["subject"])
		self.assertEqual(
			get_job_details("2026-10-19", "2026-10-22", frappe.as_json({"name": self.cards[1].name})), []
		)

	def test_helpers_recheck_removed_role(self):
		frappe.set_user("Administrator")
		self.reader.set("roles", [])
		self.reader.save()
		frappe.set_user(self.reader.name)
		with self.assertRaises(frappe.PermissionError):
			get_operation_details(self.orders[0].name, self.operations[0])
		with self.assertRaises(frappe.PermissionError):
			get_job_details("2026-10-19", "2026-10-22")

	def test_calendar_requires_read_not_select_and_honors_shared_read(self):
		from frappe.permissions import update_permission_property

		frappe.set_user("Administrator")
		update_permission_property("Job Card", self.role, 0, "read", 0)
		update_permission_property("Job Card", self.role, 0, "select", 1)
		frappe.set_user(self.reader.name)
		self.assertTrue(frappe.only_has_select_perm("Job Card"))
		with self.assertRaises(frappe.PermissionError):
			get_job_details("2026-10-19", "2026-10-22")

		frappe.set_user("Administrator")
		frappe.share.add("Job Card", self.cards[0].name, user=self.reader.name, read=1)
		for permission in frappe.get_all("User Permission", filters={"user": self.reader.name}, pluck="name"):
			frappe.delete_doc("User Permission", permission)
		frappe.set_user(self.reader.name)
		self.assertTrue(frappe.has_permission("Job Card", "read"))
		self.assertFalse(frappe.has_permission("Job Card", "read", doc=self.cards[1].name))
		events = get_job_details("2026-10-19", "2026-10-22")
		self.assertEqual({event["name"] for event in events}, {self.cards[0].name})

	def test_calendar_preserves_exclusion_filters(self):
		events = get_job_details("2026-10-19", "2026-10-22", frappe.as_json({"status": "!Completed"}))
		self.assertEqual({event["name"] for event in events}, {self.cards[0].name})
		self.assertEqual(
			get_job_details("2026-10-19", "2026-10-22", frappe.as_json({"status": "!Work In Progress"})), []
		)
		events = get_job_details(
			"2026-10-19", "2026-10-22", frappe.as_json({"work_order": ["like", self.orders[0].name + "%"]})
		)
		self.assertEqual({event["name"] for event in events}, {self.cards[0].name})

	def test_operation_search_without_parent_has_no_results(self):
		self.assertEqual(get_operations("Operation", "", "name", 0, 20), [])
		self.assertEqual(get_operations("Operation", "", "name", 0, 20, None), [])
		self.assertEqual(get_operations("Operation", "", "name", 0, 20, {}), [])

	def test_calendar_preserves_literal_percent_filters(self):
		frappe.set_user("Administrator")
		self.cards[0].remarks = "进度100% '备注'"
		self.cards[0].save()
		frappe.set_user(self.reader.name)
		events = get_job_details(
			"2026-10-19", "2026-10-22", frappe.as_json({"remarks": self.cards[0].remarks})
		)
		self.assertEqual({event["name"] for event in events}, {self.cards[0].name})
		self.assertEqual(
			get_job_details(
				"2026-10-19", "2026-10-22", frappe.as_json({"remarks": "!" + self.cards[0].remarks})
			),
			[],
		)

	def test_operation_search_rejects_malformed_filters(self):
		for filters in (["work_order"], '["work_order"]', 7):
			with self.subTest(filters=filters), self.assertRaises(frappe.ValidationError):
				get_operations("Operation", "", "name", 0, 20, filters)


class TestJobCard(FrappeTestCase):
	def setUp(self):
		make_bom_for_jc_tests()
		self.transfer_material_against: Literal["Work Order", "Job Card"] = "Work Order"
		self.source_warehouse = None
		self._work_order = None

	@property
	def work_order(self) -> WorkOrder:
		"""Work Order lazily created for tests."""
		if not self._work_order:
			self._work_order = make_wo_order_test_record(
				item="_Test FG Item 2",
				qty=2,
				transfer_material_against=self.transfer_material_against,
				source_warehouse=self.source_warehouse,
			)
		return self._work_order

	def generate_required_stock(self, work_order: WorkOrder) -> None:
		"""Create twice the stock for all required items in work order."""
		for item in work_order.required_items:
			make_stock_entry(
				item_code=item.item_code,
				target=item.source_warehouse or self.source_warehouse,
				qty=item.required_qty * 2,
				basic_rate=100,
			)

	def tearDown(self):
		frappe.db.rollback()

	def test_job_card_operations(self):
		job_cards = frappe.get_all(
			"Job Card", filters={"work_order": self.work_order.name}, fields=["operation_id", "name"]
		)

		if job_cards:
			job_card = job_cards[0]
			frappe.db.set_value("Job Card", job_card.name, "operation_row_number", job_card.operation_id)

			doc = frappe.get_doc("Job Card", job_card.name)
			doc.operation_id = "Test Data"
			self.assertRaises(OperationMismatchError, doc.save)

	def test_job_card_with_different_work_station(self):
		job_cards = frappe.get_all(
			"Job Card",
			filters={"work_order": self.work_order.name},
			fields=["operation_id", "workstation", "name", "for_quantity"],
		)

		job_card = job_cards[0]

		if job_card:
			workstation = frappe.db.get_value(
				"Workstation", {"name": ("not in", [job_card.workstation])}, "name"
			)

			if not workstation or job_card.workstation == workstation:
				workstation = make_workstation(workstation_name=random_string(5)).name

			doc = frappe.get_doc("Job Card", job_card.name)
			doc.workstation = workstation
			doc.append(
				"time_logs",
				{
					"from_time": "2009-01-01 12:06:25",
					"to_time": "2009-01-01 12:37:25",
					"time_in_mins": "31.00002",
					"completed_qty": job_card.for_quantity,
				},
			)
			doc.submit()

			completed_qty = frappe.db.get_value(
				"Work Order Operation", job_card.operation_id, "completed_qty"
			)
			self.assertEqual(completed_qty, job_card.for_quantity)

	def test_job_card_overlap(self):
		wo2 = make_wo_order_test_record(item="_Test FG Item 2", qty=2)

		jc1 = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		jc2 = frappe.get_last_doc("Job Card", {"work_order": wo2.name})

		employee = "_T-Employee-00001"  # from test records

		jc1.append(
			"time_logs",
			{
				"from_time": "2021-01-01 00:00:00",
				"to_time": "2021-01-01 08:00:00",
				"completed_qty": 1,
				"employee": employee,
			},
		)
		jc1.save()

		# add a new entry in same time slice
		jc2.append(
			"time_logs",
			{
				"from_time": "2021-01-01 00:01:00",
				"to_time": "2021-01-01 06:00:00",
				"completed_qty": 1,
				"employee": employee,
			},
		)
		self.assertRaises(OverlapError, jc2.save)

	def test_job_card_overlap_with_capacity(self):
		wo2 = make_wo_order_test_record(item="_Test FG Item 2", qty=2)

		workstation = make_workstation(workstation_name=random_string(5)).name
		frappe.db.set_value("Workstation", workstation, "production_capacity", 1)

		jc1 = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		jc2 = frappe.get_last_doc("Job Card", {"work_order": wo2.name})

		jc1.workstation = workstation
		jc1.append(
			"time_logs",
			{"from_time": "2021-01-01 00:00:00", "to_time": "2021-01-01 08:00:00", "completed_qty": 1},
		)
		jc1.save()

		jc2.workstation = workstation

		# add a new entry in same time slice
		jc2.append(
			"time_logs",
			{"from_time": "2021-01-01 00:01:00", "to_time": "2021-01-01 06:00:00", "completed_qty": 1},
		)
		self.assertRaises(OverlapError, jc2.save)

		frappe.db.set_value("Workstation", workstation, "production_capacity", 2)
		jc2.load_from_db()

		jc2.workstation = workstation

		# add a new entry in same time slice
		jc2.append(
			"time_logs",
			{"from_time": "2021-01-01 00:01:00", "to_time": "2021-01-01 06:00:00", "completed_qty": 1},
		)

		jc2.save()
		self.assertTrue(jc2.name)

	def test_job_card_multiple_materials_transfer(self):
		"Test transferring RMs separately against Job Card with multiple RMs."
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card_name = frappe.db.get_value("Job Card", {"work_order": self.work_order.name})
		job_card = frappe.get_doc("Job Card", job_card_name)

		transfer_entry_1 = make_stock_entry_from_jc(job_card_name)
		del transfer_entry_1.items[1]  # transfer only 1 of 2 RMs
		transfer_entry_1.insert()
		transfer_entry_1.submit()

		job_card.reload()

		self.assertEqual(transfer_entry_1.fg_completed_qty, 2)
		self.assertEqual(job_card.transferred_qty, 2)

		# transfer second RM
		transfer_entry_2 = make_stock_entry_from_jc(job_card_name)
		del transfer_entry_2.items[0]
		transfer_entry_2.insert()
		transfer_entry_2.submit()

		# 'For Quantity' here will be 0 since
		# transfer was made for 2 fg qty in first transfer Stock Entry
		self.assertEqual(transfer_entry_2.fg_completed_qty, 0)

	@change_settings("Manufacturing Settings", {"job_card_excess_transfer": 1})
	def test_job_card_excess_material_transfer(self):
		"Test transferring more than required RM against Job Card."
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		self.assertEqual(job_card.status, "Open")

		# fully transfer both RMs
		transfer_entry_1 = make_stock_entry_from_jc(job_card.name)
		transfer_entry_1.insert()
		transfer_entry_1.submit()

		# transfer extra qty of both RM due to previously damaged RM
		transfer_entry_2 = make_stock_entry_from_jc(job_card.name)
		# deliberately change 'For Quantity'
		transfer_entry_2.fg_completed_qty = 1
		transfer_entry_2.items[0].qty = 5
		transfer_entry_2.items[1].qty = 3
		transfer_entry_2.insert()
		transfer_entry_2.submit()

		job_card.reload()
		self.assertGreater(job_card.transferred_qty, job_card.for_quantity)

		# Check if 'For Quantity' is negative
		# as 'transferred_qty' > Qty to Manufacture
		transfer_entry_3 = make_stock_entry_from_jc(job_card.name)
		self.assertEqual(transfer_entry_3.fg_completed_qty, 0)

		job_card.append(
			"time_logs",
			{"from_time": "2021-01-01 00:01:00", "to_time": "2021-01-01 06:00:00", "completed_qty": 2},
		)
		job_card.save()
		job_card.submit()

		# JC is Completed with excess transfer
		self.assertEqual(job_card.status, "Completed")

	def test_job_card_time_log_blocked_until_material_transfer(self):
		"Time logs must wait for the transfer when RMs move against Job Card."
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})

		self.assertRaises(
			frappe.ValidationError, job_card.add_time_log, frappe._dict(start_time=now(), employees=[])
		)

		transfer_entry = make_stock_entry_from_jc(job_card.name)
		transfer_entry.insert()
		transfer_entry.submit()

		job_card.reload()
		job_card.add_time_log(frappe._dict(start_time=now(), employees=[]))
		self.assertTrue(job_card.time_logs)

	@change_settings("Manufacturing Settings", {"job_card_excess_transfer": 0})
	def test_job_card_excess_material_transfer_block(self):
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card_name = frappe.db.get_value("Job Card", {"work_order": self.work_order.name})

		# fully transfer both RMs
		transfer_entry_1 = make_stock_entry_from_jc(job_card_name)
		transfer_entry_1.insert()
		transfer_entry_1.submit()

		# transfer extra qty of both RM due to previously damaged RM
		transfer_entry_2 = make_stock_entry_from_jc(job_card_name)
		# deliberately change 'For Quantity'
		transfer_entry_2.fg_completed_qty = 1
		transfer_entry_2.items[0].qty = 5
		transfer_entry_2.items[1].qty = 3
		transfer_entry_2.insert()
		self.assertRaises(JobCardOverTransferError, transfer_entry_2.submit)

	@change_settings("Manufacturing Settings", {"job_card_excess_transfer": 0})
	def test_job_card_excess_material_transfer_with_no_reference(self):
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card_name = frappe.db.get_value("Job Card", {"work_order": self.work_order.name})

		# fully transfer both RMs
		transfer_entry_1 = make_stock_entry_from_jc(job_card_name)
		row = transfer_entry_1.items[0]

		# Add new row without reference of the job card item
		transfer_entry_1.append(
			"items",
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"item_group": row.item_group,
				"qty": row.qty,
				"uom": row.uom,
				"conversion_factor": row.conversion_factor,
				"stock_uom": row.stock_uom,
				"basic_rate": row.basic_rate,
				"basic_amount": row.basic_amount,
				"expense_account": row.expense_account,
				"cost_center": row.cost_center,
				"s_warehouse": row.s_warehouse,
				"t_warehouse": row.t_warehouse,
			},
		)

		self.assertRaises(frappe.ValidationError, transfer_entry_1.insert)

	def test_job_card_partial_material_transfer(self):
		"Test partial material transfer against Job Card"
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})

		# partially transfer
		transfer_entry = make_stock_entry_from_jc(job_card.name)
		transfer_entry.fg_completed_qty = 1
		transfer_entry.get_items()
		transfer_entry.insert()
		transfer_entry.submit()

		job_card.reload()
		self.assertEqual(job_card.transferred_qty, 1)
		self.assertEqual(transfer_entry.items[0].qty, 5)
		self.assertEqual(transfer_entry.items[1].qty, 3)

		# transfer remaining
		transfer_entry_2 = make_stock_entry_from_jc(job_card.name)

		self.assertEqual(transfer_entry_2.fg_completed_qty, 1)
		self.assertEqual(transfer_entry_2.items[0].qty, 5)
		self.assertEqual(transfer_entry_2.items[1].qty, 3)

		transfer_entry_2.insert()
		transfer_entry_2.submit()

		job_card.reload()
		self.assertEqual(job_card.transferred_qty, 2)

		transfer_entry_2.cancel()
		transfer_entry.cancel()

		job_card.reload()
		self.assertEqual(job_card.transferred_qty, 0.0)

	def test_work_order_transferred_qty_with_multiple_job_cards(self):
		create_bom_with_multiple_operations()
		work_order = make_wo_with_transfer_against_jc()
		self.generate_required_stock(work_order)

		job_cards = frappe.get_all(
			"Job Card",
			filters={"work_order": work_order.name},
			pluck="name",
			order_by="sequence_id",
		)
		completed_qty = (4, 3)

		for job_card_name, qty in zip(job_cards, completed_qty, strict=True):
			job_card = frappe.get_doc("Job Card", job_card_name)
			job_card.for_quantity = qty
			job_card.save()

			transfer_entry = make_stock_entry_from_jc(job_card.name)
			transfer_entry.fg_completed_qty = qty
			transfer_entry.get_items()
			transfer_entry.submit()

			job_card.reload()
			job_card.append(
				"time_logs",
				{
					"from_time": now(),
					"to_time": add_to_date(now(), hours=1),
					"completed_qty": qty,
				},
			)
			job_card.submit()

		work_order.reload()
		self.assertEqual(work_order.material_transferred_for_manufacturing, min(completed_qty))

		# Refreshing required items must not replace the Job Card roll-up with the sum
		# of FG quantities from Material Transfer Stock Entries (4 + 3).
		work_order.update_required_items()
		work_order.reload()
		self.assertEqual(work_order.material_transferred_for_manufacturing, min(completed_qty))

	def test_job_card_material_transfer_correctness(self):
		"""
		1. Test if only current Job Card Items are pulled in a Stock Entry against a Job Card
		2. Test impact of changing 'For Qty' in such a Stock Entry
		"""
		create_bom_with_multiple_operations()
		work_order = make_wo_with_transfer_against_jc()

		job_card_name = frappe.db.get_value(
			"Job Card", {"work_order": work_order.name, "operation": "Test Operation A"}
		)
		job_card = frappe.get_doc("Job Card", job_card_name)

		self.assertEqual(len(job_card.items), 1)
		self.assertEqual(job_card.items[0].item_code, "_Test Item")

		# check if right items are mapped in transfer entry
		transfer_entry = make_stock_entry_from_jc(job_card_name)
		transfer_entry.insert()

		self.assertEqual(len(transfer_entry.items), 1)
		self.assertEqual(transfer_entry.items[0].item_code, "_Test Item")
		self.assertEqual(transfer_entry.items[0].qty, 4)

		# change 'For Qty' and check impact on items table
		# no.of items should be the same with qty change
		transfer_entry.fg_completed_qty = 2
		transfer_entry.get_items()

		self.assertEqual(len(transfer_entry.items), 1)
		self.assertEqual(transfer_entry.items[0].item_code, "_Test Item")
		self.assertEqual(transfer_entry.items[0].qty, 2)

	@change_settings(
		"Manufacturing Settings", {"add_corrective_operation_cost_in_finished_good_valuation": 1}
	)
	def test_corrective_costing(self):
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})

		job_card.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 2},
		)
		job_card.submit()

		self.work_order.reload()
		original_cost = self.work_order.total_operating_cost

		# Create a corrective operation against it
		corrective_action = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()

		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_action.name, for_operation=job_card.operation
		)
		corrective_job_card.hour_rate = 100
		corrective_job_card.insert()
		corrective_job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=2),
				"to_time": add_to_date(now(), hours=2, minutes=30),
				"completed_qty": 2,
			},
		)
		corrective_job_card.submit()

		self.work_order.reload()
		cost_after_correction = self.work_order.total_operating_cost
		self.assertGreater(cost_after_correction, original_cost)

		corrective_job_card.cancel()
		self.work_order.reload()
		cost_after_cancel = self.work_order.total_operating_cost
		self.assertEqual(cost_after_cancel, original_cost)

	@change_settings(
		"Manufacturing Settings", {"add_corrective_operation_cost_in_finished_good_valuation": 1}
	)
	def test_if_corrective_jc_ops_cost_is_added_to_manufacture_stock_entry(self):
		wo = make_wo_order_test_record(
			item="_Test FG Item 2",
			qty=10,
			transfer_material_against=self.transfer_material_against,
			source_warehouse=self.source_warehouse,
		)
		self.generate_required_stock(wo)
		job_card = frappe.get_last_doc("Job Card", {"work_order": wo.name})
		job_card.update({"for_quantity": 4})
		job_card.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 4},
		)
		job_card.submit()

		corrective_action = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()

		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_action.name, for_operation=job_card.operation
		)
		corrective_job_card.hour_rate = 100
		corrective_job_card.insert()
		corrective_job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=2),
				"to_time": add_to_date(now(), hours=2, minutes=30),
				"completed_qty": 4,
			},
		)
		corrective_job_card.submit()
		wo.reload()

		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_stock_entry_for_wo,
		)

		stock_entry = make_stock_entry_for_wo(wo.name, "Manufacture", qty=3)
		self.assertEqual(stock_entry.additional_costs[1].amount, 37.5)
		frappe.get_doc(stock_entry).submit()

		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card

		make_job_card(
			wo.name,
			[{"name": wo.operations[0].name, "operation": "_Test Operation 1", "qty": 3, "pending_qty": 3}],
		)
		workstation = job_card.workstation
		job_card = frappe.get_last_doc("Job Card", {"work_order": wo.name})
		job_card.update({"for_quantity": 3})
		job_card.workstation = workstation
		job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=3),
				"to_time": add_to_date(now(), hours=4),
				"completed_qty": 3,
			},
		)
		job_card.submit()

		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_action.name, for_operation=job_card.operation
		)
		corrective_job_card.hour_rate = 80
		corrective_job_card.insert()
		corrective_job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=4),
				"to_time": add_to_date(now(), hours=4, minutes=30),
				"completed_qty": 3,
			},
		)
		corrective_job_card.submit()
		wo.reload()

		stock_entry = make_stock_entry_for_wo(wo.name, "Manufacture", qty=4)
		self.assertEqual(stock_entry.additional_costs[1].amount, 52.5)

	def test_job_card_statuses(self):
		def assertStatus(status):
			jc.set_status()
			self.assertEqual(jc.status, status)

		jc = frappe.new_doc("Job Card")
		jc.process_loss_qty = 0
		jc.for_quantity = 2
		jc.transferred_qty = 1
		jc.total_completed_qty = 0
		assertStatus("Open")

		jc.transferred_qty = jc.for_quantity
		assertStatus("Material Transferred")

		jc.append("time_logs", {})
		assertStatus("Work In Progress")

		jc.docstatus = 1
		jc.total_completed_qty = jc.for_quantity
		assertStatus("Completed")

		jc.docstatus = 2
		assertStatus("Cancelled")

	def test_job_card_material_request_and_bom_details(self):
		from erpnext.stock.doctype.material_request.material_request import make_stock_entry

		create_bom_with_multiple_operations()
		work_order = make_wo_with_transfer_against_jc()

		job_card_name = frappe.db.get_value("Job Card", {"work_order": work_order.name}, "name")

		mr = make_material_request(job_card_name)
		mr.schedule_date = today()
		mr.submit()

		ste = make_stock_entry(mr.name)
		self.assertEqual(ste.purpose, "Material Transfer for Manufacture")
		self.assertEqual(ste.work_order, work_order.name)
		self.assertEqual(ste.job_card, job_card_name)
		self.assertEqual(ste.from_bom, 1.0)
		self.assertEqual(ste.bom_no, work_order.bom_no)

	def test_job_card_proccess_qty_and_completed_qty(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		operations = [
			{"operation": "Test Operation A1", "workstation": "Test Workstation A", "time_in_mins": 30},
			{"operation": "Test Operation B1", "workstation": "Test Workstation A", "time_in_mins": 20},
		]

		make_test_records("UOM")

		warehouse = create_warehouse("Test Warehouse 123 for Job Card")

		setup_operations(operations)

		item_code = "Test Job Card Process Qty Item"
		for item in [item_code, item_code + "RM 1", item_code + "RM 2"]:
			if not frappe.db.exists("Item", item):
				make_item(
					item,
					{
						"item_name": item,
						"stock_uom": "Nos",
						"is_stock_item": 1,
					},
				)

		routing_doc = create_routing(routing_name="Testing Route", operations=operations)
		bom_doc = setup_bom(
			item_code=item_code,
			routing=routing_doc.name,
			raw_materials=[item_code + "RM 1", item_code + "RM 2"],
			source_warehouse=warehouse,
		)

		for row in bom_doc.items:
			make_stock_entry(
				item_code=row.item_code,
				target=row.source_warehouse,
				qty=10,
				basic_rate=100,
			)

		wo_doc = make_wo_order_test_record(
			production_item=item_code,
			bom_no=bom_doc.name,
			skip_transfer=1,
			from_wip_warehouse=1,
			wip_warehouse=warehouse,
			source_warehouse=warehouse,
		)

		for row in routing_doc.operations:
			self.assertEqual(row.sequence_id, row.idx)

		first_job_card = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 1},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc = frappe.get_doc("Job Card", first_job_card)
		for row in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": row.from_time,
					"to_time": row.to_time,
					"time_in_mins": row.time_in_mins,
				},
			)

		jc.time_logs[0].completed_qty = 8
		jc.save()
		jc.submit()

		self.assertEqual(jc.process_loss_qty, 2)
		self.assertEqual(jc.for_quantity, 10)

		second_job_card = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 2},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc2 = frappe.get_doc("Job Card", second_job_card)
		for row in jc2.scheduled_time_logs:
			jc2.append(
				"time_logs",
				{
					"from_time": row.from_time,
					"to_time": row.to_time,
					"time_in_mins": row.time_in_mins,
				},
			)
		jc2.time_logs[0].completed_qty = 10

		self.assertRaises(frappe.ValidationError, jc2.save)

		jc2.load_from_db()
		for row in jc2.scheduled_time_logs:
			jc2.append(
				"time_logs",
				{
					"from_time": row.from_time,
					"to_time": row.to_time,
					"time_in_mins": row.time_in_mins,
				},
			)

		jc2.time_logs[0].completed_qty = 8
		jc2.save()
		jc2.submit()

		self.assertEqual(jc2.for_quantity, 10)
		self.assertEqual(jc2.process_loss_qty, 2)

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 10))
		s.submit()

		self.assertEqual(s.process_loss_qty, 2)

		wo_doc.reload()
		for row in wo_doc.operations:
			self.assertEqual(row.completed_qty, 8)
			self.assertEqual(row.process_loss_qty, 2)

		self.assertEqual(wo_doc.produced_qty, 8)
		self.assertEqual(wo_doc.process_loss_qty, 2)
		self.assertEqual(wo_doc.status, "Completed")

	def test_op_cost_calculation(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		suffix = random_string(5)
		workstation = make_workstation(
			workstation_name=f"Test Workstation Z {suffix}", hour_rate_rent=240, hour_rate_labour=0
		)
		workstation.update(
			{
				"hour_rate_rent": 240,
				"hour_rate_labour": 0,
				"hour_rate_electricity": 0,
				"hour_rate_consumable": 0,
			}
		)
		workstation.save()
		operations = [
			{
				"operation": f"Test Operation A1 {suffix}",
				"workstation": workstation.name,
				"time_in_mins": 30,
			},
		]

		warehouse = create_warehouse(f"Test Warehouse 123 for Job Card {suffix}")
		setup_operations(operations)

		item_code = f"Test Job Card Process Qty Item {suffix}"
		for item in [item_code, item_code + "RM 1", item_code + "RM 2"]:
			if not frappe.db.exists("Item", item):
				make_item(
					item,
					{
						"item_name": item,
						"stock_uom": "Nos",
						"is_stock_item": 1,
					},
				)

		routing_doc = create_routing(routing_name="Testing Route", operations=operations)
		bom_doc = setup_bom(
			item_code=item_code,
			routing=routing_doc.name,
			raw_materials=[item_code + "RM 1", item_code + "RM 2"],
			source_warehouse=warehouse,
		)

		for row in bom_doc.items:
			make_stock_entry(
				item_code=row.item_code,
				target=row.source_warehouse,
				qty=10,
				basic_rate=100,
			)

		wo_doc = make_wo_order_test_record(
			production_item=item_code,
			bom_no=bom_doc.name,
			qty=10,
			skip_transfer=1,
			wip_warehouse=warehouse,
			source_warehouse=warehouse,
		)

		first_job_card = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 1},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc = frappe.get_doc("Job Card", first_job_card)
		from_time = "2025-01-01 09:00:00"
		for _ in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": from_time,
					"to_time": add_to_date(from_time, minutes=1),
					"completed_qty": 4,
				},
			)
		jc.for_quantity = 4
		jc.save()
		jc.submit()

		s1 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 4))
		s1.submit()

		wo_doc.reload()
		precision = s1.additional_costs[0].precision("amount")
		self.assertEqual(
			flt(s1.additional_costs[0].amount, precision),
			flt(wo_doc.operations[0].actual_operating_cost, precision),
		)

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": operations[0]["operation"],
					"workstation": wo_doc.operations[0].workstation,
					"qty": 6,
					"pending_qty": 6,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-01 10:00:00"
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, minutes=2),
				"completed_qty": 6,
			},
		)
		job_card.for_quantity = 6
		job_card.save()
		job_card.submit()

		s2 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 6))
		wo_doc.reload()
		precision = s2.additional_costs[0].precision("amount")
		self.assertEqual(
			flt(s2.additional_costs[0].amount, precision),
			flt(wo_doc.operations[0].actual_operating_cost - s1.additional_costs[0].amount, precision),
		)

	@change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 100})
	def test_operating_cost_with_overproduction(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		suffix = random_string(5)
		workstation = make_workstation(
			workstation_name=f"Test Workstation for Overproduction {suffix}",
			hour_rate_rent=10,
			hour_rate_labour=10,
		)
		workstation.update(
			{
				"hour_rate_rent": 10,
				"hour_rate_labour": 10,
				"hour_rate_electricity": 0,
				"hour_rate_consumable": 0,
			}
		)
		workstation.save()
		operations = [
			{"operation": f"Test Operation 1 {suffix}", "workstation": workstation.name, "time_in_mins": 30},
			{"operation": f"Test Operation 2 {suffix}", "workstation": workstation.name, "time_in_mins": 30},
		]
		warehouse = create_warehouse(f"Test Warehouse for Overproduction {suffix}")
		setup_operations(operations)

		fg = make_item(f"Test FG for Overproduction {suffix}", {"stock_uom": "Nos", "is_stock_item": 1})
		rm = make_item(f"Test RM for Overproduction {suffix}", {"stock_uom": "Nos", "is_stock_item": 1})

		routing_doc = create_routing(routing_name=f"Testing Route {suffix}", operations=operations)
		bom_doc = setup_bom(
			item_code=fg.name,
			routing=routing_doc.name,
			raw_materials=[rm.name],
			source_warehouse=warehouse,
		)

		for row in bom_doc.items:
			make_stock_entry(
				item_code=row.item_code,
				target=row.source_warehouse,
				qty=100,
				basic_rate=100,
			)

		wo_doc = make_wo_order_test_record(
			production_item=fg.name,
			bom_no=bom_doc.name,
			qty=10,
			skip_transfer=1,
			source_warehouse=warehouse,
		)

		first_operation = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 1},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc = frappe.get_doc("Job Card", first_operation)
		from_time = "2025-01-02 09:00:00"
		for _ in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": from_time,
					"to_time": add_to_date(from_time, days=1),
					"completed_qty": 4,
				},
			)
		jc.for_quantity = 4
		jc.save()
		jc.submit()

		second_operation = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 2},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc = frappe.get_doc("Job Card", second_operation)
		from_time = "2025-01-05 09:00:00"
		for _ in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": from_time,
					"to_time": add_to_date(from_time, days=2),
					"completed_qty": 4,
				},
			)
		jc.for_quantity = 4
		jc.save()
		jc.submit()

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 6))  # overproduction
		s.submit()

		def assert_operating_costs(stock_entry, qty, previous_entries):
			wo_doc.reload()
			for idx, operation in enumerate(wo_doc.operations):
				consumed_cost = sum(
					entry.additional_costs[idx].amount for entry in previous_entries if entry.docstatus == 1
				)
				consumed_qty = sum(
					entry.additional_costs[idx].qty for entry in previous_entries if entry.docstatus == 1
				)
				remaining_cost = operation.actual_operating_cost - consumed_cost
				remaining_qty = operation.completed_qty - consumed_qty
				precision = stock_entry.additional_costs[idx].precision("amount")
				expected_cost = flt(remaining_cost / remaining_qty * min(remaining_qty, qty), precision)

				self.assertEqual(flt(stock_entry.additional_costs[idx].amount, precision), expected_cost)

		assert_operating_costs(s, 6, [])

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": operations[0]["operation"],
					"workstation": wo_doc.operations[0].workstation,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-09 09:00:00"
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, days=1),
				"completed_qty": 2,
			},
		)
		job_card.for_quantity = 2
		job_card.save()
		job_card.submit()

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[1].name,
					"operation": operations[1]["operation"],
					"workstation": wo_doc.operations[1].workstation,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-12 09:00:00"
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, days=2),
				"completed_qty": 2,
			},
		)
		job_card.for_quantity = 2
		job_card.save()
		job_card.submit()

		s2 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 1))
		s2.submit()

		assert_operating_costs(s2, 1, [s])

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": operations[0]["operation"],
					"workstation": wo_doc.operations[0].workstation,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-16 09:00:00"
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, days=1),
				"completed_qty": 2,
			},
		)
		job_card.for_quantity = 2
		job_card.save()
		job_card.submit()

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[1].name,
					"operation": operations[1]["operation"],
					"workstation": wo_doc.operations[1].workstation,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-19 09:00:00"
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, days=2),
				"completed_qty": 2,
			},
		)
		job_card.for_quantity = 2
		job_card.save()
		job_card.submit()

		s3 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 2))
		s3.submit()

		assert_operating_costs(s3, 2, [s, s2])

		s2.cancel()

		s4 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 3))
		s4.submit()

		assert_operating_costs(s4, 3, [s, s3])

	def test_completed_qty_sums_without_float_noise(self):
		jc = frappe.new_doc("Job Card")
		jc.update({"docstatus": 1, "for_quantity": 0.8, "total_completed_qty": 0.7, "process_loss_qty": 0.1})
		jc.append("items", {"item_code": "_Test Item"})
		jc.set_status()
		self.assertEqual(jc.status, "Completed")

	def test_set_process_loss(self):
		nothing_done = frappe.new_doc("Job Card")
		nothing_done.for_quantity = 10
		nothing_done.total_completed_qty = 0
		nothing_done.set_process_loss()
		self.assertEqual(nothing_done.process_loss_qty, 0)

		all_process_loss = frappe.new_doc("Job Card")
		all_process_loss.for_quantity = 10
		all_process_loss.process_loss_qty = 10
		all_process_loss.set_process_loss()
		self.assertEqual(all_process_loss.process_loss_qty, 10)

	def test_lowered_overproduction_allowance_checks_only_job_card_operation(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation

		item = create_item("Lowered Allowance FG").name
		bom = frappe.new_doc("BOM", company="_Test Company", item=item, quantity=1, with_operations=1)
		bom.append("items", {"item_code": "_Test Item", "qty": 1})
		for operation in ("Lowered Allowance Op A", "Lowered Allowance Op B"):
			make_operation(operation=operation, workstation="_Test Workstation 1")
			bom.append(
				"operations",
				{"operation": operation, "workstation": "_Test Workstation 1", "time_in_mins": 1},
			)
		bom.insert()
		bom.submit()

		def complete(job_card, qty, hours):
			job_card.append(
				"time_logs",
				{
					"from_time": add_to_date(now(), hours=hours),
					"to_time": add_to_date(now(), hours=hours + 1),
					"completed_qty": qty,
				},
			)

		with change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 100}):
			work_order = make_wo_order_test_record(
				item=item, qty=2, bom_no=bom.name, skip_transfer=1, source_warehouse="Stores - _TC"
			)
			job_card_a = frappe.get_last_doc(
				"Job Card", {"work_order": work_order.name, "operation": "Lowered Allowance Op A"}
			)
			job_card_a.for_quantity = 4
			complete(job_card_a, 4, 1)
			job_card_a.submit()

		with change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 0}):
			job_card_b = frappe.get_last_doc(
				"Job Card", {"work_order": work_order.name, "operation": "Lowered Allowance Op B"}
			)
			complete(job_card_b, 2, 3)
			job_card_b.submit()

			operation_a = work_order.operations[0]
			make_job_card(
				work_order.name,
				[
					{
						"name": operation_a.name,
						"operation": operation_a.operation,
						"workstation": operation_a.workstation,
						"qty": 1,
						"pending_qty": 1,
					}
				],
			)
			extra_job_card_a = frappe.get_last_doc(
				"Job Card", {"operation_id": operation_a.name, "docstatus": 0}
			)
			complete(extra_job_card_a, 1, 5)
			self.assertRaisesRegex(
				frappe.ValidationError, "Completed Qty cannot be greater", extra_job_card_a.submit
			)

		work_order.reload()
		self.assertEqual([row.status for row in work_order.operations], ["Completed", "Completed"])


def create_bom_with_multiple_operations():
	"Create a BOM with multiple operations and Material Transfer against Job Card"
	from erpnext.manufacturing.doctype.operation.test_operation import make_operation

	test_record = frappe.get_test_records("BOM")[2]
	bom_doc = frappe.get_doc(test_record)

	row = {
		"operation": "Test Operation A",
		"workstation": "_Test Workstation A",
		"hour_rate_rent": 300,
		"time_in_mins": 60,
	}
	make_workstation(row)
	make_operation(row)

	bom_doc.append(
		"operations",
		{
			"operation": "Test Operation A",
			"description": "Test Operation A",
			"workstation": "_Test Workstation A",
			"hour_rate": 300,
			"time_in_mins": 60,
			"operating_cost": 100,
		},
	)

	bom_doc.transfer_material_against = "Job Card"
	bom_doc.save()
	bom_doc.submit()

	return bom_doc


def make_wo_with_transfer_against_jc():
	"Create a WO with multiple operations and Material Transfer against Job Card"

	work_order = make_wo_order_test_record(
		item="_Test FG Item 2",
		qty=4,
		transfer_material_against="Job Card",
		source_warehouse="Stores - _TC",
		do_not_submit=True,
	)
	work_order.required_items[0].operation = "Test Operation A"
	work_order.required_items[1].operation = "_Test Operation 1"
	work_order.submit()

	return work_order


def make_bom_for_jc_tests():
	test_records = frappe.get_test_records("BOM")
	bom = frappe.copy_doc(test_records[2])
	bom.set_rate_of_sub_assembly_item_based_on_bom = 0
	bom.rm_cost_as_per = "Valuation Rate"
	bom.items[0].uom = "_Test UOM 1"
	bom.items[0].conversion_factor = 5
	bom.insert()


class TestProductionTimeMetrics(FrappeTestCase):
	"""B04 calculation contracts; not confirmation, payroll or workflow acceptance."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.db.rollback)

	def calculator(self, name):
		from erpnext.manufacturing.doctype.job_card import job_card
		method = getattr(job_card, name, None)
		self.assertTrue(callable(method), f"B04 required calculation entry missing: {name}")
		return method

	def make_card(self, start, end, minutes=0):
		from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrderRequiredQuantity
		order, raw, _ = TestWorkOrderRequiredQuantity.make_quantity_order(self, 0.5, planned=10)
		station = make_workstation(workstation_name=raw.name + "-工时").name
		operation = frappe.get_doc({"doctype": "Operation", "__newname": raw.name + "-工序"}).insert().name
		order.append("operations", {"operation": operation, "workstation": station, "time_in_mins": 1})
		order.insert()
		return frappe.get_doc({"doctype": "Job Card", "work_order": order.name, "company": order.company,
			"operation": operation, "operation_id": order.operations[0].name,
			"workstation": station, "wip_warehouse": order.wip_warehouse, "for_quantity": 5,
			"time_logs": [{"from_time": start, "to_time": end, "time_in_mins": minutes}]})

	def test_native_closed_time_recalculated_and_cross_day(self):
		for start, end, expected in (("2026-10-20 09:00:00", "2026-10-20 17:00:00", 480),
			("2026-10-20 22:00:00", "2026-10-21 02:00:00", 240)):
			card = self.make_card(start, end, 999999).insert().reload()
			self.assertEqual(card.total_time_in_mins, expected)
			self.assertEqual(card.time_logs[0].time_in_mins, expected)
			self.assertEqual(str(card.time_logs[0].from_time), start)

	def test_native_open_row_cannot_save_forged_minutes(self):
		card = self.make_card("2026-10-20 09:00:00", None, 999999).insert().reload()
		self.assertEqual(card.time_logs[0].time_in_mins, 0)
		self.assertEqual(card.total_time_in_mins, 0)
		self.assertIsNone(card.time_logs[0].to_time)

	def test_native_end_requires_start(self):
		card = self.make_card(None, "2099-10-20 10:00:00", 999999)
		with self.assertRaises(frappe.ValidationError):
			card.insert()

	def test_native_reverse_and_overlap_still_rejected(self):
		card = self.make_card("2026-10-20 10:00:00", "2026-10-20 09:00:00")
		with self.assertRaises(frappe.ValidationError):
			card.insert()
		card.time_logs[0].to_time = "2026-10-20 11:00:00"
		card.insert()
		overlap = frappe.copy_doc(card)
		overlap.time_logs[0].from_time = "2026-10-20 10:30:00"
		overlap.time_logs[0].to_time = "2026-10-20 11:30:00"
		with self.assertRaises(frappe.ValidationError):
			overlap.insert()

	def rule(self, **changes):
		return {"name": "午休", "priority": 1, "enabled": True, "operation": None,
			"rest_periods": [["12:00", "13:00"]], "overtime_periods": [], **changes}

	def test_work_time_t01_to_t04_and_t06_to_t09(self):
		calc = self.calculator("calculate_report_time")
		day = ("2026-10-20 09:00:00", "2026-10-20 17:00:00")
		result = calc(*day, rules=[self.rule()])
		self.assertEqual((result["reported_seconds"], result["rest_seconds"], result["effective_seconds"]), (28800, 3600, 25200))
		cross = calc("2026-10-20 22:00:00", "2026-10-21 02:00:00", rules=[self.rule(rest_periods=[["23:00", "01:00"]])])
		self.assertEqual((cross["reported_seconds"], cross["rest_seconds"], cross["effective_seconds"]), (14400, 7200, 7200))
		with self.assertRaisesRegex(frappe.ValidationError, "7小时"):
			calc(*day, rules=[self.rule()], shutdown_seconds=28800)
		covered = calc("2026-10-20 12:30:00", "2026-10-20 12:45:00", rules=[self.rule()])
		self.assertEqual((covered["rest_seconds"], covered["effective_seconds"]), (900, 0))
		rule = self.rule(overtime_periods=[["16:00", "17:00"]])
		result = calc(*day, rules=[rule], shutdown_seconds=3600, overtime_seconds=1800)
		self.assertEqual((result["overtime_limit_seconds"], result["effective_seconds"]), (3600, 23400))
		with self.assertRaisesRegex(frappe.ValidationError, "1小时"):
			calc(*day, rules=[rule], overtime_seconds=3601)
		with self.assertRaises(frappe.ValidationError):
			calc(day[1], day[0], rules=[])
		with self.assertRaises(TypeError):
			calc(*day, rules=[rule], effective_seconds=999999)

	def test_rule_priority_scope_overlap_union_and_multiday(self):
		calc = self.calculator("calculate_report_time")
		day = ("2026-10-20 09:00:00", "2026-10-20 17:00:00")
		rules = [self.rule(name="后序", priority=2), self.rule(name="他工序", priority=0, operation="他工序"),
			self.rule(name="命中", rest_periods=[["12:00", "13:00"], ["12:30", "13:30"]])]
		result = calc(*day, rules=rules, operation="下料")
		self.assertEqual((result["matched_rule"], result["rest_seconds"], result["effective_seconds"]), ("命中", 5400, 23400))
		result = calc("2026-10-20 00:00:00", "2026-10-23 00:00:00", rules=[self.rule()])
		self.assertEqual(result["rest_seconds"], 10800)
		result = calc("2026-10-20T01:00:00+00:00", "2026-10-20T09:00:00+00:00", rules=[self.rule()])
		self.assertEqual(result["effective_seconds"], 25200)
		result = calc("2026-10-20 09:00:00.200", "2026-10-20 09:00:02.100", rules=[])
		self.assertEqual(result["effective_seconds"], 1)

	def test_fractional_overlap_matches_before_whole_second_conversion(self):
		calc = self.calculator("calculate_report_time")
		span = ("2026-10-20 12:59:59.500", "2026-10-20 14:00:00")
		first = self.rule(name="优先规则")
		second = self.rule(name="后序规则", priority=2, rest_periods=[["13:00", "14:00"]])
		for rules in ([first, second], [first]):
			with self.subTest(rules=rules):
				result = calc(*span, rules=rules)
				self.assertEqual(result["matched_rule"], "优先规则")
				self.assertEqual(result["rest_seconds"], 0)
				self.assertEqual(result["effective_seconds"], 3600)
				self.assertEqual(result["overtime_limit_seconds"], 0)

	def test_no_rule_is_explicit_and_bad_context_is_rejected(self):
		calc = self.calculator("calculate_report_time")
		day = ("2026-10-20 09:00:00", "2026-10-20 10:00:00")
		result = calc(*day, rules=[])
		self.assertEqual((result["rest_seconds"], result["overtime_limit_seconds"], result["effective_seconds"]), (0, 3600, 3600))
		self.assertIsNone(result["matched_rule"])
		self.assertIn("未匹配", result["rule_message"])
		for rules in (None, {}, [self.rule(rest_periods=[["25:00", "13:00"]])]):
			with self.subTest(rules=rules), self.assertRaises(frappe.ValidationError):
				calc(*day, rules=rules)
		for field in ("shutdown_seconds", "overtime_seconds"):
			for value in (-1, 0.5, False, "NaN", "Infinity"):
				with self.subTest(field=field, value=value), self.assertRaises(frappe.ValidationError):
					calc(*day, rules=[], **{field: value})
		for value in (None, "", "not-a-date"):
			with self.subTest(value=value), self.assertRaises(frappe.ValidationError):
				calc(value, day[1], rules=[])

	def test_metrics_m01_m02_efficiency_and_pay(self):
		calc = self.calculator("calculate_report_metrics")
		args = {"plan_quantity": 10, "good_quantity": 8, "bad_quantity": 2, "effective_seconds": 7200,
			"completed_tasks": 1, "total_tasks": 1, "issued_quantity": 4, "required_quantity": 10,
			"standard_efficiency": 10, "wage_mode": "hourly", "wage_rate": 10}
		for rework in (0, 3):
			result = calc(**args, rework_quantity=rework)
			self.assertEqual(result["quality_percent"], 80)
			self.assertEqual(result["unfinished_quantity"], 0)
			self.assertEqual(result["task_completion_percent"], 100)
			self.assertEqual(result["material_issue_percent"], 40)
			self.assertEqual(result["actual_efficiency"], 5)
			self.assertEqual(result["efficiency_percent"], 50)
			self.assertEqual(result["estimated_wage"], 20)
		args["wage_mode"] = "piece"
		self.assertEqual(calc(**args)["estimated_wage"], 80)

	def test_metrics_zero_denominators_and_decimal_quantity(self):
		from decimal import Decimal
		calc = self.calculator("calculate_report_metrics")
		for rework in (0, 3):
			result = calc(plan_quantity=10, good_quantity=0, bad_quantity=0, rework_quantity=rework, effective_seconds=0,
				completed_tasks=0, total_tasks=0, issued_quantity=0, required_quantity=0, standard_efficiency=0)
			for field in ("quality_percent", "task_completion_percent", "material_issue_percent", "actual_efficiency", "efficiency_percent", "estimated_wage"):
				self.assertIsNone(result[field], field)
		result = calc(plan_quantity="0.123457", good_quantity="0.123456", bad_quantity=0, effective_seconds=1,
			completed_tasks=0, total_tasks=1, issued_quantity=0, required_quantity=1)
		self.assertEqual(result["unfinished_quantity"], Decimal("0.000001"))

	def test_metrics_reject_invalid_inputs(self):
		calc = self.calculator("calculate_report_metrics")
		args = dict(plan_quantity=10, good_quantity=8, bad_quantity=2, effective_seconds=7200,
			completed_tasks=1, total_tasks=1, issued_quantity=4, required_quantity=10)
		for field, value in (("good_quantity", -1), ("bad_quantity", "NaN"), ("plan_quantity", 1000000000),
			("good_quantity", "0.0000001"), ("effective_seconds", 0.5), ("completed_tasks", 2),
			("total_tasks", False), ("standard_efficiency", -1), ("wage_mode", "other")):
			with self.subTest(field=field, value=value), self.assertRaises(frappe.ValidationError):
				calc(**{**args, field: value})

	def test_shared_quantity_validator_preserves_positive_default(self):
		from erpnext.manufacturing.doctype.bom.bom import validate_quantity_input
		with self.assertRaises(frappe.ValidationError):
			validate_quantity_input(0, "数量")
		self.assertEqual(validate_quantity_input("999999999.999999", "数量"), 999999999.999999)
		self.assertEqual(validate_quantity_input("0.000000", "数量", allow_zero=True), 0)
		for value in (False, -1, "0.0000001", 1000000000):
			with self.subTest(value=value), self.assertRaises(frappe.ValidationError):
				validate_quantity_input(value, "数量", allow_zero=True)


class TestProductionReportConfirmation(FrappeTestCase):
	"""B08: real workflow fixture, narrow operator, native per-confirmation cards."""

	def setUp(self, report_scope="PERSON", report_values=None):
		from frappe.permissions import add_permission, add_user_permission, update_permission_property
		from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrderApproval
		self.approval = TestWorkOrderApproval()
		self.addCleanup(self.approval.clean_fixture)
		self.approval.setUp()
		f = self.approval
		frappe.set_user("Administrator")
		if not frappe.db.exists("Role", "生产报工"):
			frappe.get_doc({"doctype": "Role", "role_name": "生产报工", "desk_access": 1}).insert()
		add_permission("Work Order", "生产报工", ptype="read")
		add_permission("Job Card", "生产报工", ptype="read")
		for p in ("create", "write", "submit"):
			update_permission_property("Job Card", "生产报工", 0, p, 1)
		for dt in ("Employee", "Operation", "Workstation", "Item"):
			add_permission(dt, "生产报工", ptype="select")
		self.user = f.prefix.lower() + "-report@example.invalid"
		frappe.get_doc({"doctype": "User", "email": self.user, "first_name": "报工验收员",
			"language": "zh", "send_welcome_email": 0, "roles": [{"role": "生产报工"}]}).insert()
		self.employee = frappe.get_doc({"doctype": "Employee", "first_name": "报工验收员", "gender": "Male",
			"date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01", "company": f.company,
			"department": f.teams[0], "status": "Active", "user_id": self.user, "create_user_permission": 0}).insert().name
		add_user_permission("Company", f.company, self.user)
		add_user_permission("Department", f.teams[0], self.user, applicable_for="Work Order")
		add_user_permission("Work Order", f.order.name, self.user)
		frappe.set_user(f.users["operator"])
		f.order.operations[0].report_scope = report_scope
		f.order.operations[0].report_employee = self.employee if report_scope == "PERSON" else None
		f.order.operations[0].report_department = f.teams[0] if report_scope == "DEPT" else None
		if report_values:
			f.order.operations[0].update(report_values)
		f.order.operations[1].report_scope = "ALL" if self._testMethodName == "test_correction_rejects_existing_downstream_facts" else ""
		f.order.operations[2].report_scope = "ALL"
		f.order.save()
		f.act("operator", "送审")
		f.act("reviewer", "审核通过")
		f.act("director", "签批通过")
		self.order = f.order
		self.operation_id = self.order.operations[0].name
		self.plan_names = frappe.get_all("Job Card", filters={"work_order": self.order.name}, pluck="name")
		frappe.set_user(self.user)

	def method(self, name):
		from erpnext.manufacturing.doctype.job_card import job_card
		method = getattr(job_card, name, None)
		self.assertTrue(callable(method), name + " is not implemented")
		return method

	def report(self, good, bad, hour=9, request_id=None, **changes):
		start, end = f"2026-10-20 {hour:02}:00:00", f"2026-10-20 {hour+1:02}:00:00"
		preview = self.method("preview_production_report_time")(self.order.name, self.operation_id, start, end)
		return self.method("confirm_production_report")(**dict(request_id=request_id or frappe.generate_hash(length=32),
			work_order=self.order.name, operation_id=self.operation_id, good_quantity=good, bad_quantity=bad,
			from_time=start, to_time=end, shutdown_seconds=0, overtime_seconds=0,
			context_fingerprint=preview["context_fingerprint"], **changes))

	def test_00_narrow_fixture_runnable(self):
		self.assertEqual(len(self.plan_names), 3)
		self.assertEqual(self.order.workflow_state, "已批准")
		self.assertFalse(frappe.has_permission("Work Order", "write"))
		self.assertFalse(frappe.has_permission("Stock Entry", "create"))
		self.assertTrue(frappe.has_permission("Job Card", "submit"))
		self.assertEqual(self.order.operations[0].report_employee, self.employee)

	def test_three_reports_preserve_plan_and_explicit_bad(self):
		for index, (good, bad, fine, rejected) in enumerate(((1,0,1,0),(1,0,2,0),(6,2,8,2))):
			result = self.report(good, bad, 9+index)
			doc = frappe.get_doc("Job Card", result["name"])
			self.assertEqual((doc.docstatus, doc.total_completed_qty, doc.process_loss_qty, doc.for_quantity), (1,good,bad,good+bad))
			self.assertEqual(doc.time_logs[0].employee, self.employee)
			self.order.reload()
			row = self.order.operations[0]
			self.assertEqual((row.completed_qty,row.process_loss_qty,self.order.qty), (fine,rejected,10))
			self.assertEqual(self.order.status, "In Process")
			self.assertEqual(self.order.produced_qty, 0)
			self.assertTrue(all(o.completed_qty == 0 for o in self.order.operations[1:]))
		self.assertEqual(self.order.operations[0].status, "Completed")
		self.assertEqual(frappe.db.count("Job Card", {"work_order":self.order.name,"docstatus":1}),3)
		self.assertTrue(all(frappe.db.get_value("Job Card", n, "for_quantity") == 10 for n in self.plan_names))

	def test_scope_denial_and_parent_write_remain_restricted(self):
		preview = self.method("preview_production_report_time")
		with self.assertRaises(frappe.PermissionError):
			preview(self.order.name, self.order.operations[1].name, "2026-10-20 09:00", "2026-10-20 10:00")
		self.order.qty = 11
		with self.assertRaises(frappe.PermissionError):
			self.order.save()
		self.order.reload()
		result = self.report(1, 0)
		self.assertEqual(frappe.db.get_value("Work Order", self.order.name, "qty"),10)
		frappe.set_user("Administrator")
		user = frappe.get_doc("User", self.user)
		user.roles = [r for r in user.roles if r.role != "生产报工"]
		user.save()
		frappe.set_user(self.user)
		with self.assertRaises(frappe.PermissionError):
			preview(self.order.name, self.operation_id, "2026-10-20 10:00", "2026-10-20 11:00")
		self.assertEqual(frappe.db.get_value("Job Card",result["name"],"total_completed_qty"),1)

	def test_same_key_retry_and_distinct_quantities(self):
		key = frappe.generate_hash(length=32)
		first = self.report(1, 0, request_id=key)
		self.assertEqual(self.report(1, 0, request_id=key), first)
		with self.assertRaises(frappe.PermissionError):
			self.report(2, 0, request_id=key)
		second = self.report(1, 0, hour=10)
		self.assertNotEqual(first["name"], second["name"])
		self.order.reload()
		self.assertEqual(self.order.operations[0].completed_qty,2)

	def test_real_overquantity_still_rejected_and_plan_not_loss(self):
		self.report(1, 0)
		frappe.db.savepoint("before_overquantity")
		with self.assertRaises(frappe.ValidationError):
			self.report(10, 0, hour=10)
		frappe.db.rollback(save_point="before_overquantity")
		self.assertEqual(frappe.db.count("Job Card", {"work_order":self.order.name,"docstatus":1}),1)
		plan = frappe.get_doc("Job Card", self.plan_names[0])
		plan.total_completed_qty = 1
		plan.process_loss_qty = 9
		plan.set_process_loss()
		self.assertEqual(plan.process_loss_qty,0)
		with self.assertRaises(frappe.PermissionError):
			plan.submit()

	def test_original_parent_and_child_protected(self):
		name = self.report(1, 0)["name"]
		for action in ("update", "clear_key", "cancel", "delete", "child"):
			with self.subTest(action=action):
				doc = frappe.get_doc("Job Card", name)
				with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
					if action == "update":
						doc.flags.ignore_validate_update_after_submit = True
						doc.remarks = "tampered"
						doc.save()
					elif action == "clear_key":
						doc.report_request_id = None
						doc.flags.ignore_validate_update_after_submit = True
						doc.save()
					elif action == "cancel":
						doc.cancel()
					elif action == "delete":
						frappe.delete_doc("Job Card", name, ignore_permissions=True)
					else:
						row = frappe.get_doc("Job Card Time Log", doc.time_logs[0].name)
						row.completed_qty = 9
						row.flags.ignore_validate_update_after_submit = True
						row.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Job Card Time Log",doc.time_logs[0].name,"completed_qty"),1)

	def test_rule_snapshot_and_stale_preview(self):
		frappe.set_user("Administrator")
		rule = frappe.get_doc({"doctype":"Production Time Rule", "rule_name":self.approval.prefix+"休息",
			"company":self.order.company,"enabled":1,"priority":0,"operation":self.order.operations[0].operation,
			"periods":[{"period_type":"Rest","start_time":"12:00","end_time":"13:00"}]}).insert()
		frappe.set_user(self.user)
		preview = self.method("preview_production_report_time")
		confirm = self.method("confirm_production_report")
		args = dict(work_order=self.order.name, operation_id=self.operation_id,
			from_time="2026-10-20 09:00",to_time="2026-10-20 17:00")
		old = preview(**args)
		self.assertEqual(old["effective_seconds"],25200)
		first = confirm(**args, request_id=frappe.generate_hash(length=32),good_quantity=1,bad_quantity=0,
			context_fingerprint=old["context_fingerprint"])
		original = frappe.get_doc("Job Card",first["name"])
		frappe.set_user("Administrator")
		rule.periods[0].end_time = "14:00"
		rule.save()
		frappe.set_user(self.user)
		with self.assertRaisesRegex(frappe.ValidationError,"时段依据已变化"):
			confirm(**args,request_id=frappe.generate_hash(length=32),good_quantity=1,bad_quantity=0,
				context_fingerprint=old["context_fingerprint"])
		args.update(from_time="2026-10-21 09:00",to_time="2026-10-21 17:00")
		new = preview(**args)
		self.assertEqual(new["effective_seconds"],21600)
		second = confirm(**args,request_id=frappe.generate_hash(length=32),good_quantity=1,bad_quantity=0,
			context_fingerprint=new["context_fingerprint"])
		original.reload()
		self.assertEqual(original.report_effective_seconds,25200)
		self.assertEqual(frappe.parse_json(original.report_time_context)["rule"]["rest_periods"],[["12:00","13:00"]])
		self.assertEqual(frappe.db.get_value("Job Card",second["name"],"report_effective_seconds"),21600)

	def test_full_correction_retains_original_rule_and_fact(self):
		from frappe.permissions import update_permission_property
		frappe.set_user("Administrator")
		update_permission_property("Job Card","生产报工",0,"cancel",1)
		frappe.set_user(self.user)
		first = self.report(10,0)
		original = frappe.get_doc("Job Card",first["name"])
		old_context = original.report_time_context
		correct = self.method("correct_production_report")
		key = frappe.generate_hash(length=32)
		new = correct(original.name,key,8,0,"数量录错，按实际更正")
		self.assertEqual(correct(original.name,key,8,0,"数量录错，按实际更正"),new)
		original.reload()
		self.assertEqual((original.docstatus,original.total_completed_qty,original.report_time_context),(2,10,old_context))
		replacement = frappe.get_doc("Job Card",new["name"])
		self.assertEqual((replacement.docstatus,replacement.amended_from,replacement.total_completed_qty),(1,original.name,8))
		self.assertEqual(frappe.parse_json(replacement.report_time_context)["result"],frappe.parse_json(old_context)["result"])
		self.order.reload()
		self.assertEqual((self.order.operations[0].completed_qty,self.order.qty),(8,10))
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Job Card",original.name,ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			correct(original.name,frappe.generate_hash(length=32),7,0,"另一次更正")

	def test_task_menu_and_saved_result_are_scoped(self):
		menu = self.method("get_production_report_tasks")(self.order.name)
		self.assertEqual({r["name"] for r in menu["tasks"]},{self.operation_id,self.order.operations[2].name})
		key = frappe.generate_hash(length=32)
		first = self.report(1,0,request_id=key)
		result = self.method("get_production_report_result")(key)
		self.assertEqual((result["name"],result["docstatus"]),(first["name"],1))
		frappe.set_user(self.approval.users["other"])
		with self.assertRaises(frappe.PermissionError):
			self.method("get_production_report_result")(key)

	def test_operator_cannot_rewrite_plan_card(self):
		plan = frappe.get_doc("Job Card",self.plan_names[0])
		plan.for_quantity = 1
		with self.assertRaises(frappe.PermissionError):
			plan.save()
		self.assertEqual(frappe.db.get_value("Job Card",plan.name,"for_quantity"),10)

	def test_identical_zero_time_facts_distinct_keys(self):
		args=dict(work_order=self.order.name,operation_id=self.operation_id,from_time="2026-10-20 09:00",to_time="2026-10-20 09:00")
		preview=self.method("preview_production_report_time")(**args)
		confirm=self.method("confirm_production_report")
		names=[confirm(**args,request_id=frappe.generate_hash(length=32),good_quantity=1,bad_quantity=0,
			context_fingerprint=preview["context_fingerprint"])["name"] for _ in range(2)]
		self.assertNotEqual(*names)
		self.order.reload()
		self.assertEqual(self.order.operations[0].completed_qty,2)
		self.assertTrue(all(frappe.db.get_value("Job Card",n,"report_effective_seconds")==0 for n in names))

	def test_correction_rejects_existing_downstream_facts(self):
		from frappe.permissions import update_permission_property
		frappe.set_user("Administrator")
		update_permission_property("Job Card","生产报工",0,"cancel",1)
		frappe.set_user(self.user)
		original=self.report(10,0)["name"]
		args=dict(work_order=self.order.name,operation_id=self.order.operations[1].name,from_time="2026-10-20 10:00",to_time="2026-10-20 11:00")
		preview=self.method("preview_production_report_time")(**args)
		self.method("confirm_production_report")(**args,request_id=frappe.generate_hash(length=32),good_quantity=10,bad_quantity=0,context_fingerprint=preview["context_fingerprint"])
		with self.assertRaisesRegex(frappe.ValidationError,"后工序"):
			self.method("correct_production_report")(original,frappe.generate_hash(length=32),8,0,"数量更正")
		self.assertEqual(frappe.db.get_value("Job Card",original,"docstatus"),1)

	def test_retry_after_stop_returns_existing_but_rejects_new(self):
		args=dict(work_order=self.order.name,operation_id=self.operation_id,from_time="2026-10-20 09:00",to_time="2026-10-20 10:00")
		preview=self.method("preview_production_report_time")(**args)
		args.update(request_id=frappe.generate_hash(length=32),good_quantity=1,bad_quantity=0,context_fingerprint=preview["context_fingerprint"])
		confirm=self.method("confirm_production_report")
		first=confirm(**args)
		self.approval.order.reload()
		self.approval.act("director","停止执行",reason="停止新增执行")
		frappe.set_user(self.user)
		self.assertEqual(confirm(**args),first)
		with self.assertRaises(frappe.PermissionError):
			confirm(**{**args,"request_id":frappe.generate_hash(length=32)})

	def test_sub_operations_rejected_before_confirmation(self):
		frappe.set_user("Administrator")
		op=frappe.get_doc("Operation",self.order.operations[0].operation)
		op.append("sub_operations",{"operation":self.order.operations[2].operation,"time_in_mins":1})
		op.save()
		frappe.set_user(self.user)
		with self.assertRaisesRegex(frappe.ValidationError,"子工序"):
			self.method("preview_production_report_time")(self.order.name,self.operation_id,"2026-10-20 09:00","2026-10-20 10:00")

	def test_derivation_failure_rolls_back_native_fact(self):
		from unittest.mock import patch
		from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
		validate = WorkOrder.validate_report_derivation
		seen = []
		def invalid_plan_write(order, before, operation_id):
			context = frappe.local.production_report_context
			self.assertTrue(frappe.db.exists("Job Card", context.card.name))
			self.assertTrue(frappe.db.exists("Job Card Time Log", {"parent": context.card.name}))
			seen.append(context.card.name)
			order.qty = 11
			return validate(order, before, operation_id)
		frappe.db.savepoint("report_derivation_failure")
		with patch.object(WorkOrder, "validate_report_derivation", invalid_plan_write):
			with self.assertRaisesRegex(frappe.PermissionError, "报工不能修改工单字段"):
				self.report(1, 0)
		self.assertTrue(seen)
		self.assertIsNone(frappe.local.production_report_context)
		# This is controlled failure injection with a real DB rollback, not an HTTP result.
		frappe.db.rollback(save_point="report_derivation_failure")
		self.assertFalse(frappe.db.exists("Job Card", seen[0]))
		self.assertFalse(frappe.db.exists("Job Card Time Log", {"parent": seen[0]}))
		self.order.reload()
		self.assertEqual((self.order.qty, self.order.operations[0].completed_qty), (10, 0))


class TestProductionReportFollowup(FrappeTestCase):
	"""B08-02/05 missing combinations; reuse the existing rollback-only fixture."""

	method = TestProductionReportConfirmation.method
	report = TestProductionReportConfirmation.report

	def setUp(self):
		scope = "DEPT" if "dept" in self._testMethodName else "ALL" if self._testMethodName.startswith("test_all_") else "PERSON"
		TestProductionReportConfirmation.setUp(self, report_scope=scope)

	def args(self, operation_id=None, day=20):
		return dict(work_order=self.order.name, operation_id=operation_id or self.operation_id,
			from_time=f"2026-10-{day} 09:00", to_time=f"2026-10-{day} 17:00")

	def prepare(self, args):
		preview = self.method("preview_production_report_time")(**args)
		return dict(**args, request_id=frappe.generate_hash(length=32), good_quantity=1, bad_quantity=0,
			context_fingerprint=preview["context_fingerprint"])

	def fact_state(self):
		cards = frappe.get_all("Job Card", filters={"work_order":self.order.name}, fields=["*"], order_by="name")
		rows = frappe.get_all("Job Card Time Log", filters={"parent":["in",[c.name for c in cards]]}, fields=["*"], order_by="name")
		order = frappe.get_doc("Work Order", self.order.name)
		return frappe.as_json(dict(cards=cards, rows=rows, order=order.as_dict(),
			stock=frappe.db.count("Stock Entry"), ledger=frappe.db.count("Stock Ledger Entry")))

	def assert_new_denied(self, args, *, existing_request=None):
		before = self.fact_state()
		with self.assertRaises(frappe.PermissionError):
			self.method("preview_production_report_time")(**{k:args[k] for k in self.args()})
		with self.assertRaises(frappe.PermissionError):
			self.method("confirm_production_report")(**args)
		if existing_request:
			with self.assertRaises(frappe.PermissionError):
				self.method("get_production_report_result")(existing_request)
		self.assertEqual(self.fact_state(), before, "Denied request must not partially write facts or totals")

	def test_dept_same_department_can_confirm(self):
		args = self.prepare(self.args())
		result = self.method("confirm_production_report")(**args)
		self.assertEqual(self.method("get_production_report_result")(args["request_id"])["name"], result["name"])
		self.assertEqual(frappe.db.get_value("Job Card",result["name"],"total_completed_qty"),1)
		self.assertFalse(frappe.has_permission("Work Order","write"))

	def test_dept_changed_employee_denies_new_but_preserves_history_read(self):
		args = self.prepare(self.args())
		result = self.method("confirm_production_report")(**args)
		stale = self.prepare(self.args(day=21))
		frappe.set_user("Administrator")
		employee = frappe.get_doc("Employee",self.employee)
		employee.department = self.approval.teams[1]
		employee.save()
		frappe.set_user(self.user)
		self.assert_new_denied(stale)
		# Scope determines new work, while current object read authorizes existing evidence.
		frappe.get_doc("Job Card",result["name"]).check_permission("read")
		self.assertEqual(self.method("get_production_report_result")(args["request_id"])["name"],result["name"])

	def other_reporter(self):
		from frappe.permissions import add_user_permission
		frappe.set_user("Administrator")
		other = self.approval.prefix.lower()+"-second-report@example.invalid"
		frappe.get_doc({"doctype":"User","email":other,"first_name":"报工对照","language":"zh",
			"send_welcome_email":0,"roles":[{"role":"生产报工"}]}).insert()
		frappe.get_doc({"doctype":"Employee","first_name":"报工对照","gender":"Male",
			"date_of_birth":"1990-01-01","date_of_joining":"2020-01-01","company":self.order.company,
			"department":self.approval.teams[0],"status":"Active","user_id":other,"create_user_permission":0}).insert()
		add_user_permission("Company",self.order.company,other)
		add_user_permission("Department",self.approval.teams[0],other,applicable_for="Work Order")
		add_user_permission("Work Order",self.order.name,other)
		frappe.set_user(other)
		return other

	def test_person_other_employee_denied(self):
		stale = self.prepare(self.args())
		self.other_reporter()
		self.assert_new_denied(stale)

	def test_all_other_employee_can_confirm(self):
		self.other_reporter()
		args = self.prepare(self.args())
		result = self.method("confirm_production_report")(**args)
		self.assertEqual(self.method("get_production_report_result")(args["request_id"])["name"], result["name"])
		self.assertFalse(frappe.has_permission("Work Order","write"))

	def test_all_still_requires_company_team_and_work_order_read(self):
		from frappe.permissions import remove_user_permission, add_user_permission, update_permission_property
		args = self.prepare(self.args())
		first = self.method("confirm_production_report")(**args)
		stale = self.prepare(self.args(day=21))
		for boundary in ("Company", "Department", "Work Order read", "other team", "other company"):
			with self.subTest(boundary=boundary):
				frappe.db.savepoint("scope_boundary")
				frappe.set_user("Administrator")
				if boundary == "Work Order read":
					update_permission_property("Work Order","生产报工",0,"read",0)
				elif boundary in ("Company","Department"):
					value = self.order.company if boundary == "Company" else self.approval.teams[0]
					remove_user_permission(boundary,value,self.user)
				elif boundary == "other team":
					remove_user_permission("Department",self.approval.teams[0],self.user)
					add_user_permission("Department",self.approval.teams[1],self.user,applicable_for="Work Order")
				else:
					remove_user_permission("Company",self.order.company,self.user)
					other = frappe.db.get_value("Company",{"name":["!=",self.order.company]},"name")
					self.assertTrue(other,"A second synthetic company is required")
					add_user_permission("Company",other,self.user)
				frappe.clear_cache(user=self.user)
				frappe.set_user(self.user)
				self.assert_new_denied(stale,existing_request=args["request_id"])
				frappe.db.rollback(save_point="scope_boundary")
				frappe.clear_cache()
				frappe.set_user(self.user)
		self.assertEqual(self.method("get_production_report_result")(args["request_id"])["name"], first["name"])

	def test_employee_state_binding_and_company_are_current(self):
		original = self.prepare(self.args())
		self.method("confirm_production_report")(**original)
		args = self.prepare(self.args(day=21))
		for boundary in ("Inactive", "unbound", "other company"):
			with self.subTest(boundary=boundary):
				frappe.db.savepoint("employee_boundary")
				frappe.set_user("Administrator")
				employee = frappe.get_doc("Employee",self.employee)
				if boundary == "Inactive":
					employee.status = "Inactive"
				elif boundary == "unbound":
					employee.user_id = None
				else:
					employee.company = frappe.db.get_value("Company",{"name":["!=",self.order.company]},"name")
					employee.department = None
				employee.save()
				frappe.set_user(self.user)
				self.assert_new_denied(args,existing_request=original["request_id"])
				frappe.db.rollback(save_point="employee_boundary")
				frappe.clear_cache()
				frappe.set_user(self.user)

	def test_duplicate_active_employee_rejected_by_native_constraint(self):
		frappe.set_user("Administrator")
		before = frappe.db.count("Employee",{"user_id":self.user,"status":"Active"})
		other = frappe.copy_doc(frappe.get_doc("Employee",self.employee))
		with self.assertRaises(frappe.DuplicateEntryError):
			other.insert()
		self.assertEqual(frappe.db.count("Employee",{"user_id":self.user,"status":"Active"}),before)

	def test_rules_disable_stale_preview_reenable_keep_snapshots(self):
		from erpnext.manufacturing.doctype.production_time_rule.production_time_rule import load_report_time_rules
		frappe.set_user("Administrator")
		# Isolate existing synthetic rules inside this fixture's rolled-back transaction.
		for candidate in load_report_time_rules(self.order.company,self.order.operations[0].operation):
			previous = frappe.get_doc("Production Time Rule",candidate["name"])
			previous.enabled = 0
			previous.save()
		self.assertEqual(load_report_time_rules(self.order.company,self.order.operations[0].operation),[],
			"Fixture must isolate other matching rules before expecting an unmatched result")
		rule = frappe.get_doc({"doctype":"Production Time Rule","rule_name":self.approval.prefix+"停启",
			"company":self.order.company,"enabled":1,"priority":0,"operation":self.order.operations[0].operation,
			"periods":[{"period_type":"Rest","start_time":"12:00","end_time":"13:00"}]}).insert()
		frappe.set_user(self.user)
		args = self.prepare(self.args())
		old = self.method("confirm_production_report")(**args)
		original = frappe.get_doc("Job Card",old["name"])
		old_snapshot = original.report_time_context
		self.assertEqual(original.report_effective_seconds,25200)
		stale = self.prepare(self.args(day=21))
		frappe.set_user("Administrator")
		rule.enabled = 0
		rule.save()
		frappe.set_user(self.user)
		before = self.fact_state()
		with self.assertRaisesRegex(frappe.ValidationError,"时段依据已变化"):
			self.method("confirm_production_report")(**stale)
		self.assertEqual(self.fact_state(),before)
		unmatched = self.method("preview_production_report_time")(**self.args(day=21))
		self.assertIsNone(unmatched["matched_rule"])
		self.assertEqual(unmatched["effective_seconds"],28800)
		second = self.method("confirm_production_report")(**{**stale,"context_fingerprint":unmatched["context_fingerprint"]})
		second_doc = frappe.get_doc("Job Card",second["name"])
		second_snapshot = second_doc.report_time_context
		self.assertEqual(second_doc.report_effective_seconds,28800)
		stale_disabled = self.prepare(self.args(day=22))
		frappe.set_user("Administrator")
		rule.enabled = 1
		rule.save()
		frappe.set_user(self.user)
		before = self.fact_state()
		with self.assertRaisesRegex(frappe.ValidationError,"时段依据已变化"):
			self.method("confirm_production_report")(**stale_disabled)
		self.assertEqual(self.fact_state(),before)
		third_args = self.prepare(self.args(day=22))
		third = self.method("confirm_production_report")(**third_args)
		third_doc = frappe.get_doc("Job Card",third["name"])
		self.assertEqual(third_doc.report_effective_seconds,25200)
		self.assertNotEqual(args["context_fingerprint"],third_args["context_fingerprint"])
		self.assertEqual(frappe.parse_json(third_doc.report_time_context)["rule"]["modified"],str(rule.modified))
		original.reload(); second_doc.reload()
		self.assertEqual((original.report_effective_seconds,original.report_time_context),(25200,old_snapshot))
		self.assertEqual((second_doc.report_effective_seconds,second_doc.report_time_context),(28800,second_snapshot))


class TestProductionReportMetrics(FrappeTestCase):
	"""B08 pricing integration, using native approval and rollback-only fixtures."""
	method = TestProductionReportConfirmation.method
	fact_state = TestProductionReportFollowup.fact_state

	def setUp(self):
		values = dict(report_wage_mode="piece" if "piece" in self._testMethodName else "hourly",
			report_wage_rate="0" if "zero" in self._testMethodName else "10", report_standard_efficiency="10")
		if "unconfigured" in self._testMethodName:
			values = {}
		if "zero" in self._testMethodName:
			values["report_standard_efficiency"] = "0"
		TestProductionReportConfirmation.setUp(self, report_values=values)
		frappe.set_user("Administrator")
		for name in frappe.get_all("Production Time Rule", filters={"company":self.order.company,"enabled":1}, pluck="name"):
			rule = frappe.get_doc("Production Time Rule", name)
			rule.enabled = 0
			rule.save()
		frappe.set_user(self.user)

	def args(self, good=8, bad=2, end="11:00"):
		return dict(work_order=self.order.name, operation_id=self.operation_id,
			from_time="2026-10-20 09:00", to_time="2026-10-20 " + end,
			good_quantity=good, bad_quantity=bad)

	def save_report(self, args):
		preview = self.method("preview_production_report_time")(**args)
		self.assertIn("metrics", preview, "Preview must expose server-priced metrics")
		payload = dict(**args, request_id=frappe.generate_hash(length=32), context_fingerprint=preview["context_fingerprint"])
		result = self.method("confirm_production_report")(**payload)
		return frappe.get_doc("Job Card", result["name"]), preview, payload

	def draft(self):
		frappe.set_user(self.approval.users["operator"])
		doc = frappe.copy_doc(self.order)
		doc.docstatus = 0
		doc.workflow_state = "草稿"
		doc.approval_requested_by = doc.approval_reviewed_by = doc.approval_note = None
		for row in doc.operations:
			row.status = "Pending"
			for name in ("completed_qty", "process_loss_qty", "actual_operation_time", "actual_operating_cost"):
				row.set(name, 0)
			row.actual_start_time = row.actual_end_time = None
		return doc

	def test_hourly_preview_confirm_and_reopen_use_frozen_source(self):
		before = self.fact_state()
		preview = self.method("preview_production_report_time")(**self.args())
		self.assertIn("metrics", preview, "Current time-only API lacks wage and efficiency")
		self.assertEqual(self.fact_state(), before)
		result = preview["metrics"]["result"]
		self.assertEqual((result["estimated_wage"], result["actual_efficiency"], result["efficiency_percent"]), ("20.00", "5", "50"))
		doc, preview, payload = self.save_report(self.args())
		source = frappe.parse_json(doc.report_metrics_context)
		self.assertEqual((source["work_order"], source["operation_id"], source["wage_mode"], source["wage_rate"]), (self.order.name, self.operation_id, "hourly", "10"))
		self.assertEqual(source["unit"], self.order.stock_uom)
		self.assertEqual(doc.report_estimated_wage, "20.00")
		self.assertNotIn("efficiency_percent", source)
		doc.onload()
		self.assertEqual(doc.get_onload()["report_metrics"]["result"], result)
		found = self.method("get_production_report_result")(payload["request_id"])
		self.assertEqual(found["metrics"]["result"], result)
		self.assertEqual(self.method("confirm_production_report")(**payload)["name"], doc.name)
		self.assertEqual(frappe.db.count("Job Card", {"work_order":self.order.name,"report_request_id":["is","set"]}), 1)
		for field, value in (("report_metrics_context", "{}"), ("report_estimated_wage", "999.00")):
			changed = frappe.get_doc("Job Card", doc.name)
			changed.set(field, value)
			changed.flags.ignore_validate_update_after_submit = True
			with self.assertRaises(frappe.PermissionError): changed.save()
		# Controlled storage drift, not an allowed edit: old results never consult current terms.
		frappe.db.savepoint("changed_terms")
		frappe.db.set_value("Work Order Operation", self.operation_id,
			{"report_wage_rate":"25", "report_standard_efficiency":"20", "report_wage_currency":"CNY"}, update_modified=False)
		doc.reload(); doc.onload()
		self.assertEqual(doc.get_onload()["report_metrics"]["source"], source)
		self.assertEqual(doc.get_onload()["report_metrics"]["result"], result)
		frappe.db.rollback(save_point="changed_terms")

	def test_piece_rounding_captures_native_currency_precision(self):
		# Same frozen fixture, explicit 0.005 piece price gives 0.01 at native 2-place precision.
		frappe.db.set_value("Work Order Operation", self.operation_id, "report_wage_rate", "0.005", update_modified=False)
		doc, preview, payload = self.save_report(self.args(good=1, bad=0))
		self.assertEqual(preview["metrics"]["source"]["currency_precision"], 2)
		self.assertEqual(doc.report_estimated_wage, "0.01")
		self.assertEqual(frappe.parse_json(doc.report_metrics_context)["wage_rate"], "0.005")

	def test_piece_correction_recalculates_with_original_price(self):
		from frappe.permissions import update_permission_property
		doc, preview, payload = self.save_report(self.args())
		self.assertEqual(preview["metrics"]["result"]["estimated_wage"], "80.00")
		original_context = doc.report_metrics_context
		frappe.set_user("Administrator")
		update_permission_property("Job Card", "生产报工", 0, "cancel", 1)
		frappe.set_user(self.user)
		new = self.method("correct_production_report")(doc.name, frappe.generate_hash(length=32), 6, 2, "合成样例：更正良品数量")
		replacement = frappe.get_doc("Job Card", new["name"])
		doc.reload()
		self.assertEqual((doc.docstatus, doc.total_completed_qty, doc.report_estimated_wage, doc.report_metrics_context), (2, 8, "80.00", original_context))
		self.assertEqual((replacement.amended_from, replacement.report_estimated_wage, replacement.report_metrics_context), (doc.name, "60.00", original_context))
		replacement.onload()
		self.assertEqual(replacement.get_onload()["report_metrics"]["result"]["efficiency_percent"], "40")

	def test_unconfigured_is_unknown_and_legacy_snapshot_not_backfilled(self):
		doc, preview, payload = self.save_report(self.args())
		self.assertIsNone(preview["metrics"]["result"]["estimated_wage"])
		self.assertIsNone(preview["metrics"]["source"]["wage_mode"])
		self.assertIsNone(preview["metrics"]["source"]["standard_efficiency"])
		self.assertIsNone(preview["metrics"]["result"]["efficiency_percent"])
		self.assertIn(doc.report_estimated_wage, (None, ""))
		# A pre-feature record has no source. Read it without inventing today's terms.
		frappe.db.set_value("Job Card", doc.name, {"report_metrics_context":None,"report_estimated_wage":None}, update_modified=False)
		doc.reload(); doc.onload()
		self.assertIsNone(doc.get_onload()["report_metrics"])
		self.assertIsNone(self.method("get_production_report_result")(payload["request_id"])["metrics"])

	def test_zero_rate_and_zero_seconds_remain_explicit(self):
		doc, preview, payload = self.save_report(self.args(good=1, bad=0, end="09:00"))
		self.assertEqual(preview["metrics"]["source"]["wage_rate"], "0")
		self.assertEqual(doc.report_estimated_wage, "0.00")
		self.assertIsNone(preview["metrics"]["result"]["actual_efficiency"])
		self.assertIsNone(preview["metrics"]["result"]["efficiency_percent"])

	def test_source_validation_and_approval_freeze(self):
		for field,value in (("report_wage_rate","-1"),("report_wage_rate","NaN"),("report_wage_rate","0.0000001"),
			("report_wage_rate",""),("report_wage_mode","other"),("report_standard_efficiency","Infinity")):
			with self.subTest(field=field, value=value):
				draft = self.draft(); draft.operations[0].set(field, value)
				with self.assertRaises(frappe.ValidationError): draft.insert()
		frappe.set_user(self.approval.users["operator"])
		order = frappe.get_doc("Work Order", self.order.name)
		order.operations[0].report_wage_rate = "99"
		with self.assertRaises(frappe.PermissionError): order.save()
		self.assertEqual(frappe.db.get_value("Work Order Operation", self.operation_id, "report_wage_rate"), "10")

	def test_stale_source_forgery_and_revoked_access_reject_without_facts(self):
		args = self.args(good=1, bad=0)
		preview = self.method("preview_production_report_time")(**args)
		self.assertIn("metrics", preview)
		payload = dict(**args, request_id=frappe.generate_hash(length=32), context_fingerprint=preview["context_fingerprint"])
		before = self.fact_state()
		with self.assertRaises(TypeError): self.method("confirm_production_report")(**payload, wage_rate="1")
		self.assertEqual(self.fact_state(), before)
		# Controlled source drift: prove fingerprints bind the price; not a legal edit path.
		frappe.db.savepoint("metrics_drift")
		frappe.db.set_value("Work Order Operation", self.operation_id, "report_wage_rate", "11", update_modified=False)
		drifted = self.fact_state()
		with self.assertRaises(frappe.ValidationError): self.method("confirm_production_report")(**payload)
		self.assertEqual(self.fact_state(), drifted)
		frappe.db.rollback(save_point="metrics_drift")
		frappe.set_user(self.approval.users["other"])
		with self.assertRaises(frappe.PermissionError): self.method("preview_production_report_time")(**args)
		frappe.set_user(self.user)
		self.assertEqual(self.fact_state(), before)

	def test_amount_precision_and_unrelated_metrics_are_not_invented(self):
		calc = self.method("calculate_report_metrics")
		result = calc(plan_quantity=10, good_quantity=8, bad_quantity=2, effective_seconds=7200,
			wage_mode="hourly", wage_rate="10", standard_efficiency=10)
		self.assertEqual(result["estimated_wage"], 20)
		self.assertIsNone(result["material_issue_percent"])
		self.assertIsNone(result["task_completion_percent"])
		with self.assertRaises(frappe.ValidationError): calc(plan_quantity=10,good_quantity=1,bad_quantity=0,effective_seconds=1,issued_quantity=1)
		draft = self.draft(); draft.operations[0].report_wage_rate = "0.123456"
		draft.operations[0].report_wage_mode = "piece"; draft.insert()
		self.assertEqual(frappe.db.get_value("Work Order Operation", draft.operations[0].name,"report_wage_rate"), "0.123456")

	def test_direct_child_save_cannot_bypass_pricing_freeze_or_validation(self):
		from frappe.client import save
		from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
		draft = self.draft(); draft.insert()
		child = frappe.get_doc("Work Order Operation", draft.operations[0].name)
		child.report_wage_rate = "-1"
		frappe.db.savepoint("child_invalid")
		with self.subTest(path="draft invalid price"), self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
			save(frappe.as_json(child.as_dict()))
		frappe.db.rollback(save_point="child_invalid")
		draft.reload()
		apply_production_approval(draft.name, "送审", str(draft.modified)); draft.reload()
		before = frappe.as_json(draft.as_dict())
		child = frappe.get_doc("Work Order Operation", draft.operations[0].name)
		child.report_wage_rate = "99"
		with self.subTest(path="submitted for review"), self.assertRaises(frappe.PermissionError): save(frappe.as_json(child.as_dict()))
		for path in ("insert", "operation", "clear"):
			child = frappe.get_doc("Work Order Operation", draft.operations[0].name)
			if path == "insert": child = frappe.copy_doc(child)
			elif path == "operation": child.operation = draft.operations[1].operation
			else:
				for field in ("report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency"):
					child.set(field, None)
			with self.subTest(path=path), self.assertRaises(frappe.PermissionError): save(frappe.as_json(child.as_dict()))
		draft.reload()
		self.assertEqual(frappe.as_json(draft.as_dict()), before)

	def test_saved_currency_precision_survive_current_settings_changes(self):
		doc, preview, payload = self.save_report(self.args(good=1, bad=0))
		source = frappe.parse_json(doc.report_metrics_context)
		old_currency = frappe.db.get_value("Company", self.order.company, "default_currency")
		defaults_before = frappe.as_json(frappe.get_all("DefaultValue", filters={"defkey":"currency_precision"},fields=["*"],order_by="name"))
		frappe.db.savepoint("currency_settings")
		try:
			# Controlled current-setting change; the approved row and original report stay frozen.
			frappe.db.set_value("Company", self.order.company, "default_currency", "USD" if old_currency != "USD" else "CNY", update_modified=False)
			frappe.db.set_default("currency_precision", "3")
			current = self.method("preview_production_report_time")(**self.args(good=1,bad=0))
			self.assertEqual(current["metrics"]["source"]["currency"], source["currency"])
			self.assertEqual(current["metrics"]["source"]["currency_precision"], 3)
			self.assertEqual(current["metrics"]["result"]["estimated_wage"], "20.000")
			doc.reload();doc.onload()
			self.assertEqual(doc.get_onload()["report_metrics"]["source"],source)
			self.assertEqual(doc.get_onload()["report_metrics"]["result"]["estimated_wage"],"20.00")
			self.assertEqual(doc.report_estimated_wage,"20.00")
			before = self.fact_state()
			with self.assertRaises(frappe.ValidationError):
				self.method("confirm_production_report")(**{**payload,"request_id":frappe.generate_hash(length=32)})
			self.assertEqual(self.fact_state(),before)
		finally:
			frappe.db.rollback(save_point="currency_settings")
			frappe.defaults.clear_defaults_cache("__default")
		self.assertEqual(frappe.db.get_value("Company",self.order.company,"default_currency"),old_currency)
		self.assertEqual(frappe.as_json(frappe.get_all("DefaultValue",filters={"defkey":"currency_precision"},fields=["*"],order_by="name")),defaults_before)


class TestProductionReportHistoryPaths(FrappeTestCase):
	"""Previously uncovered native child/history paths; real DB, rollback-only fixture."""
	setUp = TestProductionReportConfirmation.setUp
	method = TestProductionReportConfirmation.method
	report = TestProductionReportConfirmation.report
	draft = TestProductionReportMetrics.draft

	def snapshot(self, *orders):
		names = [self.order.name, *orders]
		cards = frappe.get_all("Job Card", filters={"work_order": ["in", names]}, pluck="name")
		return frappe.as_json({
			"orders": frappe.get_all("Work Order", filters={"name": ["in", names]}, fields=["*"], order_by="name"),
			"operations": frappe.get_all("Work Order Operation", filters={"parent": ["in", names]}, fields=["*"], order_by="name"),
			"cards": frappe.get_all("Job Card", filters={"name": ["in", cards]}, fields=["*"], order_by="name"),
			"logs": frappe.get_all("Job Card Time Log", filters={"parent": ["in", cards]}, fields=["*"], order_by="name"),
		})

	def as_creator_with_delete(self):
		from frappe.permissions import update_permission_property
		frappe.set_user("Administrator")
		update_permission_property("Work Order", "生产工单发起", 0, "delete", 1)
		frappe.set_user(self.approval.users["operator"])
		self.assertNotEqual(frappe.session.user, "Administrator")

	def test_resource_operation_delete_keeps_reported_task(self):
		from frappe.api.v1 import delete_doc
		self.report(1, 0)
		self.as_creator_with_delete()
		row = frappe.get_doc("Work Order Operation", self.operation_id)
		self.assertFalse(row.report_wage_mode, "Do not rely on the already-tested pricing guard")
		self.assertTrue(row.has_permission("delete"))
		before = self.snapshot()
		with self.subTest(check="history_guard"), self.assertRaises(frappe.PermissionError):
			delete_doc("Work Order Operation", self.operation_id)
		with self.subTest(check="history_unchanged"):
			self.assertEqual(self.snapshot(), before)


	def test_client_operation_reparent_keeps_reported_task(self):
		from frappe.client import save
		self.report(1, 0)
		draft = self.draft().insert()
		row = frappe.get_doc("Work Order Operation", self.operation_id)
		self.assertTrue(row.has_permission("write"))
		self.assertTrue(row.has_permission("submit"))
		before = self.snapshot(draft.name)
		row.parent = draft.name
		with self.subTest(check="history_guard"), self.assertRaises(frappe.PermissionError):
			save(row.as_dict())
		with self.subTest(check="history_unchanged"):
			self.assertEqual(self.snapshot(draft.name), before)


	def test_cancelled_time_log_native_delete_paths_keep_original(self):
		from frappe.api.v1 import delete_doc as resource_delete
		from frappe.client import delete as client_delete, save
		from frappe.permissions import update_permission_property
		frappe.set_user("Administrator")
		for ptype in ("cancel", "delete"):
			update_permission_property("Job Card", "生产报工", 0, ptype, 1)
		frappe.set_user(self.user)
		first = self.report(2, 0)
		corrected = self.method("correct_production_report")(first["name"], frappe.generate_hash(length=32), 1, 0, "校验取消态历史入口")
		original = frappe.get_doc("Job Card", first["name"])
		self.assertEqual(original.docstatus, 2)
		row = frappe.get_doc("Job Card Time Log", original.time_logs[0].name)
		self.assertTrue(row.has_permission("delete"))
		self.assertTrue(original.has_permission("write"))
		for action in ("resource_delete", "client_delete", "reparent"):
			before = self.snapshot()
			with self.subTest(action=action), self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
				if action == "resource_delete":
					resource_delete("Job Card Time Log", row.name)
				elif action == "client_delete":
					client_delete("Job Card Time Log", row.name)
				else:
					payload = row.as_dict()
					payload.parent = corrected["name"]
					save(payload)
			self.assertEqual(self.snapshot(), before)
		self.assertEqual(frappe.db.get_value("Job Card", corrected["name"], "total_completed_qty"), 1)

	def test_unreported_draft_operations_remain_editable_and_deletable(self):
		from frappe.api.v1 import delete_doc as resource_delete
		from frappe.client import delete as client_delete, save
		draft = self.draft().insert()
		self.as_creator_with_delete()
		row = frappe.get_doc("Work Order Operation", draft.operations[0].name)
		self.assertFalse(frappe.db.exists("Job Card", {"operation_id":row.name,"docstatus":[">",0]}))
		self.assertTrue(row.has_permission("write"))
		self.assertTrue(row.has_permission("delete"))
		row.time_in_mins = 2
		save(row.as_dict())
		self.assertEqual(frappe.db.get_value("Work Order Operation", row.name, "time_in_mins"), 2)
		last = draft.operations[2].name
		resource_delete("Work Order Operation", last)
		self.assertFalse(frappe.db.exists("Work Order Operation", last))
		client_delete("Work Order Operation", draft.operations[1].name)
		draft.reload()
		self.assertEqual([r.name for r in draft.operations], [row.name])


	def test_cancelled_only_operation_reference_stays_protected(self):
		from frappe.api.v1 import delete_doc
		from frappe.client import save
		from frappe.permissions import update_permission_property
		frappe.set_user("Administrator")
		update_permission_property("Job Card", "生产报工", 0, "cancel", 1)
		frappe.set_user(self.user)
		original = frappe.get_doc("Job Card", self.report(1, 0)["name"])
		# Controlled server-side cancellation creates a cancelled-only history fixture.
		# This is not a new client cancel API or authority supplied in document flags.
		previous = getattr(frappe.local, "production_report_context", None)
		frappe.local.production_report_context = frappe._dict(
			card=original, user=self.user, order=None, operation_id=self.operation_id)
		try:
			original.cancel()
		finally:
			frappe.local.production_report_context = previous
		self.assertEqual(original.docstatus, 2)
		self.assertFalse(frappe.db.exists("Job Card", {"operation_id":self.operation_id,"docstatus":1}))
		self.assertTrue(frappe.db.exists("Job Card", {"operation_id":self.operation_id,"docstatus":2}))
		draft = self.draft().insert()
		self.as_creator_with_delete()
		row = frappe.get_doc("Work Order Operation", self.operation_id)
		self.assertTrue(row.has_permission("delete"))
		before = self.snapshot(draft.name)
		with self.assertRaisesRegex(frappe.PermissionError, "工序已有报工历史"):
			delete_doc("Work Order Operation", row.name)
		row.parent = draft.name
		with self.assertRaisesRegex(frappe.PermissionError, "工序已有报工历史"):
			save(row.as_dict())
		self.assertEqual(self.snapshot(draft.name), before)
