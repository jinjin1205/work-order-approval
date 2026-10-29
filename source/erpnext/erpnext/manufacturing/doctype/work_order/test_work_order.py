# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from collections import defaultdict
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings, timeout
from frappe.utils import (
	add_days,
	add_months,
	add_to_date,
	cint,
	flt,
	get_datetime,
	now,
	nowdate,
	nowtime,
	today,
)

from erpnext.manufacturing.doctype.job_card.job_card import JobCardCancelError
from erpnext.manufacturing.doctype.job_card.job_card import make_stock_entry as make_stock_entry_from_jc
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.work_order import (
	CapacityError,
	ItemHasVariantError,
	OverProductionError,
	StockOverProductionError,
	close_work_order,
	make_job_card,
	make_stock_entry,
	make_stock_return_entry,
	stop_unstop,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.utils import get_bin

test_dependencies = ["BOM"]


class TestWorkOrderApproval(FrappeTestCase):
	"""Isolated real Workflow, users and Work Orders; no mocked business writes."""

	def setUp(self, *, before_workflow=None):
		from frappe.permissions import add_permission, add_user_permission, update_permission_property
		from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
		import erpnext

		frappe.set_user("Administrator")
		self.addCleanup(self.clean_fixture)
		self.assertTrue(frappe.get_meta("Work Order").has_field("production_team"))
		self.assertFalse(frappe.db.exists("Workflow", {"document_type": "Work Order"}))
		self.prefix = "B19-" + frappe.generate_hash(length=8)
		self.company = erpnext.get_default_company()
		self.roles = ["生产工单发起", "生产工单审核", "生产工单签批"]
		for role in self.roles:
			if not frappe.db.exists("Role", role):
				frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert()
			add_permission("Item", role, ptype="read")
			for dt in ("Work Order", "Job Card"):
				add_permission(dt, role, ptype="read")
				for ptype in ("create", "write", "submit"):
					update_permission_property(dt, role, 0, ptype, 1)
		self.teams = [frappe.get_doc({"doctype": "Department", "department_name": self.prefix + suffix,
			"company": self.company}).insert().name for suffix in ("-甲班", "-乙班")]
		self.users = {}
		for key, roles, team in [("operator", [self.roles[0]], 0), ("reviewer", [self.roles[1]], 0),
			("director", [self.roles[2]], None), ("other", [self.roles[1]], 1), ("outsider", [], None)]:
			user = frappe.get_doc({"doctype": "User", "email": self.prefix.lower() + "-" + key + "@example.invalid",
				"first_name": key, "language": "zh", "send_welcome_email": 0,
				"roles": [{"role": role} for role in roles]}).insert()
			self.users[key] = user.name
			if roles:
				add_user_permission("Company", self.company, user.name)
			if team is not None:
				add_user_permission("Department", self.teams[team], user.name, applicable_for="Work Order")
		warehouse = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": self.prefix, "company": self.company}).insert().name
		raw = create_item(self.prefix + "-RM", company=self.company, warehouse=warehouse)
		finished = create_item(self.prefix + "-FG", company=self.company, warehouse=warehouse)
		bom = make_bom(item=finished.name, company=self.company,
			currency=frappe.get_cached_value("Company", self.company, "default_currency"),
			raw_materials=[raw.name], rm_qty=1, with_operations=False)
		self.order_args = dict(item=finished.name, bom_no=bom.name, qty=10, company=self.company,
			expected_delivery_date=frappe.utils.add_days(frappe.utils.nowdate(), 7),
			stock_uom="Nos", source_warehouse=warehouse, wip_warehouse=warehouse, fg_warehouse=warehouse, do_not_save=True)
		self.workstation = make_workstation(workstation_name=self.prefix).name
		self.operations = [frappe.get_doc({"doctype": "Operation", "__newname": self.prefix + suffix}).insert().name
			for suffix in ("-下料", "-加工", "-检验")]
		# Create old draft/submitted records before enabling Workflow. They must never become approved.
		self.old_draft = make_wo_order_test_record(**self.order_args).insert()
		self.old_submitted = make_wo_order_test_record(**self.order_args).insert().submit()
		if before_workflow:
			before_workflow(self)
		self.workflow = self.make_workflow()
		frappe.set_user(self.users["operator"])
		self.order = make_wo_order_test_record(**self.order_args)
		self.order.production_team = self.teams[0]
		for operation in self.operations:
			self.order.append("operations", {"operation": operation, "workstation": self.workstation, "time_in_mins": 1})
		self.order.insert()

	def clean_fixture(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.clear_cache()

	def make_workflow(self):
		states = [("草稿", 0, self.roles[0]), ("待审核", 0, self.roles[1]),
			("待签批", 0, self.roles[2]), ("退回", 0, self.roles[0]),
			("终止", 0, self.roles[0]), ("存量待核", 1, "System Manager"), ("已批准", 1, self.roles[2]),
			("已取消", 2, self.roles[2])]
		transitions = [("草稿", "送审", "待审核", 0), ("退回", "送审", "待审核", 0),
			("待审核", "审核通过", "待签批", 1), ("待签批", "签批通过", "已批准", 2),
			("待审核", "退回", "退回", 1), ("待签批", "退回", "退回", 2),
			("待审核", "撤回", "草稿", 0), ("待签批", "撤回", "草稿", 0),
			("已批准", "取消修订", "已取消", 2)]
		transitions.extend((state, "终止", "终止", 0) for state in ("草稿", "待审核", "待签批", "退回"))
		for state, _, _ in states:
			if not frappe.db.exists("Workflow State", state):
				frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state}).insert()
		for action in {row[1] for row in transitions}:
			if not frappe.db.exists("Workflow Action Master", action):
				frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert()
		return frappe.get_doc({"doctype": "Workflow", "workflow_name": "生产工单两级审批", "document_type": "Work Order",
			"workflow_state_field": "workflow_state", "is_active": 1, "override_status": 1, "send_email_alert": 0,
			"states": [{"state": s, "doc_status": str(d), "allow_edit": r, "send_email": 0} for s,d,r in states],
			"transitions": [{"state": s, "action": a, "next_state": n, "allowed": self.roles[r],
				"allow_self_approval": int(r == 0)} for s,a,n,r in transitions]}).insert()

	def act(self, user, action, version=None, reason=None):
		from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
		frappe.set_user(self.users[user])
		result = apply_production_approval(self.order.name, action, str(version or self.order.modified), reason)
		self.order.reload()
		return result

	def ready_for_review(self):
		self.act("operator", "送审")

	def test_00_fixture_runnable(self):
		self.assertEqual(self.order.docstatus, 0)
		self.assertEqual(self.order.workflow_state, "草稿")
		self.assertEqual(len(self.order.operations), 3)
		self.assertEqual(self.order.owner, self.users["operator"])
		self.assertFalse(frappe.db.exists("Job Card", {"work_order": self.order.name}))

	def test_normal_two_stage_workflow(self):
		self.ready_for_review()
		self.assertEqual(self.order.docstatus, 0)
		self.act("reviewer", "审核通过")
		self.assertEqual(self.order.docstatus, 0)
		with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
			self.act("director", "签批通过")
		self.assertEqual(self.order.workflow_state, "已批准")
		self.assertEqual(self.order.approval_requested_by, self.users["operator"])
		self.assertEqual(self.order.approval_reviewed_by, self.users["reviewer"])
		comments = frappe.get_all("Comment", filters={"reference_doctype": "Work Order", "reference_name": self.order.name, "comment_type": "Comment"}, fields=["owner", "content", "creation"])
		approval_comments = [c for c in comments if "依据版本" in c.content]
		self.assertEqual({c.owner for c in approval_comments}, {self.users[k] for k in ("operator", "reviewer", "director")})
		self.assertTrue(all(c.creation for c in approval_comments))
		self.assertEqual(self.order.docstatus, 1)
		self.assertEqual(self.order.status, "Not Started")
		cards = frappe.get_all("Job Card", filters={"work_order": self.order.name}, fields=["name", "docstatus", "total_completed_qty"])
		self.assertEqual(len(cards), 3)
		self.assertTrue(all(c.docstatus == 0 and c.total_completed_qty == 0 for c in cards))
		self.assertFalse(frappe.db.exists("Stock Entry", {"work_order": self.order.name}))
		self.assertGreaterEqual(frappe.db.count("Comment", {"reference_doctype": "Work Order", "reference_name": self.order.name, "comment_type": "Workflow"}), 3)

	def test_cross_team_and_no_role_denied(self):
		self.ready_for_review()
		for user in ("other", "outsider"):
			with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
				self.act(user, "审核通过")
		self.order.reload()
		self.assertEqual(self.order.workflow_state, "待审核")

	def test_creator_self_approval_denied(self):
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.users["operator"]).add_roles(self.roles[1])
		self.ready_for_review()
		with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
			self.act("operator", "审核通过")

	def test_reviewer_cannot_also_sign(self):
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.users["reviewer"]).add_roles(self.roles[2])
		self.ready_for_review()
		self.act("reviewer", "审核通过")
		with self.assertRaises(frappe.PermissionError):
			self.act("reviewer", "签批通过")

	def test_direct_submit_denied(self):
		self.ready_for_review()
		frappe.set_user(self.users["director"])
		with self.assertRaises(frappe.PermissionError):
			self.order.submit()
		self.assertFalse(frappe.db.exists("Job Card", {"work_order": self.order.name}))

	def test_direct_save_self_approval_denied(self):
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.users["operator"]).add_roles(self.roles[1])
		self.ready_for_review()
		frappe.set_user(self.users["operator"])
		self.order.workflow_state = "待签批"
		with self.assertRaises(frappe.PermissionError):
			self.order.save()

	def test_stale_page_after_resubmit_denied(self):
		self.ready_for_review()
		old_version = self.order.modified
		self.act("reviewer", "退回", reason="修改计划数量")
		frappe.set_user(self.users["operator"])
		self.order.qty = 11
		self.order.save()
		self.act("operator", "送审")
		with self.assertRaises(frappe.TimestampMismatchError):
			self.act("reviewer", "审核通过", version=old_version)
		self.order.reload()
		self.assertEqual(self.order.workflow_state, "待审核")

	def test_old_orders_not_backfilled_as_approved(self):
		frappe.set_user("Administrator")
		self.workflow.save()
		self.old_draft.reload()
		self.old_submitted.reload()
		self.assertEqual(self.old_draft.docstatus, 0)
		self.assertEqual(self.old_submitted.docstatus, 1)
		self.assertNotEqual(self.old_draft.workflow_state, "已批准")
		self.assertEqual(self.old_submitted.workflow_state, "存量待核")
		self.assertEqual(frappe.db.count("Workflow", {"document_type": "Work Order"}), 1)


	def test_native_action_cannot_bypass_business_entry(self):
		from frappe.model.workflow import apply_workflow
		self.ready_for_review()
		frappe.set_user(self.users["reviewer"])
		with self.assertRaises(frappe.PermissionError):
			apply_workflow(self.order.as_dict(), "审核通过")
		self.order.reload()
		self.assertEqual(self.order.workflow_state, "待审核")
		self.assertFalse(self.order.approval_reviewed_by)

	def test_pending_basis_and_forged_actor_are_rejected(self):
		self.ready_for_review()
		for user, field, value in [("reviewer", "qty", 99), ("operator", "approval_reviewed_by", self.users["reviewer"])]:
			frappe.set_user(self.users[user])
			self.order.reload()
			self.order.set(field, value)
			self.order.flags.production_approval_context = {"action": "审核通过"}
			with self.subTest(field=field), self.assertRaises(frappe.PermissionError):
				self.order.save()
		self.order.reload()
		self.assertEqual(self.order.qty, 10)
		self.assertFalse(self.order.approval_reviewed_by)

	def test_revoked_role_and_company_scope_denied(self):
		from frappe.permissions import remove_user_permission
		self.ready_for_review()
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.users["reviewer"]).remove_roles(self.roles[1])
		with self.assertRaises(frappe.PermissionError):
			self.act("reviewer", "审核通过")
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.users["reviewer"]).add_roles(self.roles[1])
		remove_user_permission("Company", self.company, self.users["reviewer"])
		with self.assertRaises(frappe.PermissionError):
			self.act("reviewer", "审核通过")
		self.order.reload()
		self.assertEqual(self.order.workflow_state, "待审核")

	def test_return_requires_reason_and_reruns_review(self):
		self.ready_for_review()
		self.act("reviewer", "审核通过")
		with self.assertRaises(frappe.ValidationError):
			self.act("director", "退回")
		self.order.reload()
		self.assertEqual(self.order.workflow_state, "待签批")
		self.act("director", "退回", reason="数量需要调整")
		self.assertFalse(self.order.approval_reviewed_by)
		frappe.set_user(self.users["operator"])
		self.order.qty = 11
		self.order.save()
		self.act("operator", "送审")
		self.assertEqual(self.order.workflow_state, "待审核")
		with self.assertRaises(frappe.PermissionError):
			self.act("director", "签批通过")

	def test_old_draft_is_not_a_new_approval_request(self):
		from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
		frappe.set_user("Administrator")
		self.old_draft.reload()
		with self.assertRaises(frappe.PermissionError):
			apply_production_approval(self.old_draft.name, "送审", str(self.old_draft.modified))
		self.old_draft.approval_requested_by = self.users["operator"]
		with self.assertRaises(frappe.PermissionError):
			self.old_draft.save()

	def test_new_order_cannot_claim_approval(self):
		frappe.set_user(self.users["operator"])
		doc = make_wo_order_test_record(**self.order_args)
		doc.production_team = self.teams[0]
		doc.approval_reviewed_by = self.users["reviewer"]
		with self.assertRaises(frappe.PermissionError):
			doc.insert()

	def test_review_and_withdrawal_clear_previous_reviewer(self):
		self.ready_for_review()
		self.act("reviewer", "审核通过")
		self.assertEqual(self.order.approval_reviewed_by, self.users["reviewer"])
		self.act("operator", "撤回", reason="调整计划")
		self.assertEqual(self.order.workflow_state, "草稿")
		self.assertFalse(self.order.approval_reviewed_by)
		self.act("operator", "送审")
		self.assertEqual(self.order.workflow_state, "待审核")


	def test_disabled_workflow_cannot_be_bypassed_by_clearing_actor(self):
		self.ready_for_review()
		frappe.set_user("Administrator")
		self.workflow.is_active = 0
		self.workflow.save()
		frappe.set_user(self.users["reviewer"])
		self.order.approval_requested_by = None
		self.order.workflow_state = None
		self.order.qty = 99
		with self.assertRaises(frappe.PermissionError):
			self.order.save()
		self.order.reload()
		self.assertEqual(self.order.approval_requested_by, self.users["operator"])
		self.assertEqual(self.order.qty, 10)


class TestWorkOrderApprovalHistory(FrappeTestCase):
	"""Native batch-save and history APIs, within the existing rollback fixture."""

	def setUp(self):
		from frappe.permissions import add_permission, update_permission_property

		self.fixture = TestWorkOrderApproval("test_00_fixture_runnable")
		self.addCleanup(self.fixture.doCleanups)
		self.fixture.setUp()
		frappe.set_user("Administrator")
		for dt in ("Version", "Work Order", "Comment"):
			add_permission(dt, self.fixture.roles[0], ptype="read")
			for permission in ("write", "delete"):
				update_permission_property(dt, self.fixture.roles[0], 0, permission, 1)
		update_permission_property("Comment", self.fixture.roles[0], 0, "create", 1)
		# Document._save disables Version by default while in_test; exercise real audit creation.
		in_test = frappe.flags.in_test
		try:
			frappe.flags.in_test = False
			self.fixture.ready_for_review()
		finally:
			frappe.flags.in_test = in_test
		self.order = self.fixture.order
		self.comment = frappe.get_last_doc("Comment", filters={
			"reference_doctype": "Work Order", "reference_name": self.order.name, "comment_type": "Comment"})
		self.version = frappe.get_last_doc("Version", filters={"ref_doctype": "Work Order", "docname": self.order.name})
		frappe.set_user(self.fixture.users["operator"])

	def test_00_history_fixture_runnable(self):
		self.assertIn("审批动作：送审", self.comment.content)
		self.assertIn("workflow_state", self.version.data)
		self.assertEqual(self.order.workflow_state, "待审核")
		self.assertTrue(frappe.has_permission("Comment", "write", doc=self.comment))
		self.assertTrue(frappe.has_permission("Version", "write", doc=self.version))

	def test_batch_update_cannot_approve(self):
		from frappe.client import bulk_update

		frappe.set_user(self.fixture.users["reviewer"])
		result = bulk_update(frappe.as_json([{"doctype": "Work Order", "docname": self.order.name,
			"workflow_state": "待签批", "approval_reviewed_by": frappe.session.user}]))
		self.assertEqual(len(result["failed_docs"]), 1)
		self.order.reload()
		self.assertEqual(self.order.workflow_state, "待审核")
		self.assertFalse(self.order.approval_reviewed_by)

	def test_batch_update_cannot_modify_pending_basis(self):
		from frappe.client import bulk_update

		result = bulk_update(frappe.as_json([{"doctype": "Work Order", "docname": self.order.name, "qty": 99}]))
		self.assertEqual(len(result["failed_docs"]), 1)
		self.order.reload()
		self.assertEqual(self.order.qty, 10)

	def test_batch_update_allows_withdrawn_draft(self):
		from frappe.client import bulk_update

		self.fixture.act("operator", "撤回", reason="调整计划")
		result = bulk_update(frappe.as_json([{"doctype": "Work Order", "docname": self.order.name, "qty": 11}]))
		self.assertEqual(result["failed_docs"], [])
		self.order.reload()
		self.assertEqual(self.order.qty, 11)

	def test_approval_comment_cannot_be_rewritten(self):
		original = self.comment.content
		self.comment.content = "替换原审批意见"
		with self.assertRaises(frappe.PermissionError):
			self.comment.save()
		self.comment.reload()
		self.assertEqual(self.comment.content, original)

	def test_approval_comment_cannot_be_deleted(self):
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Comment", self.comment.name)
		self.assertTrue(frappe.db.exists("Comment", self.comment.name))

	def test_native_comment_editor_cannot_rewrite_approval(self):
		from frappe.desk.form.utils import update_comment

		original = self.comment.content
		with self.assertRaises(frappe.PermissionError):
			update_comment(self.comment.name, "替换原审批意见")
		self.comment.reload()
		self.assertEqual(self.comment.content, original)

	def test_approval_comment_cannot_be_detached(self):
		self.comment.reference_doctype = None
		self.comment.reference_name = None
		with self.assertRaises(frappe.PermissionError):
			self.comment.save()
		self.comment.reload()
		self.assertEqual(self.comment.reference_name, self.order.name)

	def test_approval_version_cannot_be_rewritten(self):
		original = self.version.data
		self.version.data = "{}"
		with self.assertRaises(frappe.PermissionError):
			self.version.save()
		self.version.reload()
		self.assertEqual(self.version.data, original)

	def test_approval_version_cannot_be_deleted(self):
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Version", self.version.name)
		self.assertTrue(frappe.db.exists("Version", self.version.name))

	def test_approval_version_cannot_be_detached(self):
		self.version.ref_doctype = "Item"
		self.version.docname = self.order.production_item
		with self.assertRaises(frappe.PermissionError):
			self.version.save()
		self.version.reload()
		self.assertEqual(self.version.docname, self.order.name)

	def test_withdrawn_order_with_history_cannot_be_deleted(self):
		self.fixture.act("operator", "撤回", reason="调整计划")
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Work Order", self.order.name)
		self.assertTrue(frappe.db.exists("Work Order", self.order.name))

	def test_append_comment_and_unrelated_comments_still_work(self):
		note = self.order.add_comment("Comment", "补充说明不覆盖原记录")
		self.assertTrue(frappe.db.exists("Comment", note.name))
		unrelated = frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "content": "普通评论"}).insert()
		unrelated.content = "普通评论修改"
		unrelated.save()
		frappe.delete_doc("Comment", unrelated.name)
		self.assertFalse(frappe.db.exists("Comment", unrelated.name))

	def test_unrelated_versions_and_unsent_draft_keep_native_permissions(self):
		frappe.set_user("Administrator")
		unrelated = frappe.get_doc({"doctype": "Version", "ref_doctype": "Item",
			"docname": self.order.production_item, "data": '{"changed": []}'}).insert()
		frappe.set_user(self.fixture.users["operator"])
		unrelated.data = '{"added": []}'
		unrelated.save()
		frappe.delete_doc("Version", unrelated.name)
		self.assertFalse(frappe.db.exists("Version", unrelated.name))
		draft = make_wo_order_test_record(**self.fixture.order_args)
		draft.production_team = self.fixture.teams[0]
		draft.insert()
		frappe.delete_doc("Work Order", draft.name)
		self.assertFalse(frappe.db.exists("Work Order", draft.name))


def make_approval_execution_fixture(test_case, *, stock=False):
	"""Reuse B19 setup, adding genuine pre-activation tasks and stock in the same rollback."""
	fixture = TestWorkOrderApproval()
	test_case.addCleanup(fixture.doCleanups)

	def seed_before_workflow(f):
		f.wip = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": f.prefix + "-线边在制", "company": f.company}).insert().name
		f.order_args["wip_warehouse"] = f.wip
		f.legacy_order = make_wo_order_test_record(**f.order_args)
		f.legacy_order.production_team = f.teams[0]
		for operation in f.operations:
			f.legacy_order.append("operations", {"operation": operation, "workstation": f.workstation, "time_in_mins": 1})
		with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
			f.legacy_order.insert().submit()
		f.legacy_card = frappe.get_doc("Job Card", {"work_order": f.legacy_order.name, "operation": f.operations[0]})
		if stock:
			f.raw = f.legacy_order.required_items[0].item_code
			f.legacy_card.append("items", {"item_code": f.raw, "source_warehouse": f.order_args["source_warehouse"], "uom": "Nos", "required_qty": 10})
			f.legacy_card.save()
			test_stock_entry.make_stock_entry(item_code=f.raw, company=f.company, target=f.order_args["source_warehouse"], qty=100, basic_rate=2)

	fixture.setUp(before_workflow=seed_before_workflow)
	if stock:
		from frappe.permissions import add_permission, add_user_permission, update_permission_property
		frappe.set_user("Administrator")
		role = frappe.get_doc({"doctype": "Role", "role_name": fixture.prefix + "-仓管", "desk_access": 1}).insert().name
		for dt in ("Stock Entry", "Work Order", "Job Card", "Item", "Warehouse"):
			add_permission(dt, role, ptype="read")
		for ptype in ("create", "write", "submit", "cancel"):
			update_permission_property("Stock Entry", role, 0, ptype, 1)
		user = frappe.get_doc({"doctype": "User", "email": fixture.prefix.lower() + "-warehouse@example.invalid", "first_name": "线边仓管", "language": "zh", "send_welcome_email": 0, "roles": [{"role": role}]}).insert()
		fixture.users["warehouse"] = user.name
		add_user_permission("Company", fixture.company, user.name)
		for warehouse in (fixture.order_args["source_warehouse"], fixture.wip):
			add_user_permission("Warehouse", warehouse, user.name)
		frappe.set_user(user.name)
	return fixture


class TestWorkOrderApprovalChanges(FrappeTestCase):
	"""Approved basis and stopped execution; reuse the real rollback fixture."""

	def setUp(self):
		self.f = make_approval_execution_fixture(self, stock=True)
		from frappe.permissions import update_permission_property
		frappe.set_user("Administrator")
		update_permission_property("Work Order", self.f.roles[2], 0, "cancel", 1)

	def approve(self):
		self.f.act("operator", "送审")
		self.f.act("reviewer", "审核通过")
		with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
			self.f.act("director", "签批通过")

	def issue(self):
		case = test_stock_entry.TestStockExecutionApproval()
		case.f = self.f
		frappe.set_user(self.f.users["warehouse"])
		entry = case.transfer(self.f.order).insert().submit()
		self.f.order.reload()
		return entry

	def stop(self):
		self.f.act("director", "停止执行", reason="剩余需求变更，停止原单新增执行")
		self.f.order.reload()
		self.assertEqual(self.f.order.status, "Stopped")

	def copy_request(self):
		# Native copy_doc deliberately retains docstatus in tests; use its real request behavior.
		in_test = frappe.flags.in_test
		frappe.flags.in_test = False
		try:
			return frappe.copy_doc(self.f.order, ignore_no_copy=False)
		finally:
			frappe.flags.in_test = in_test

	def test_00_change_fixture_runnable(self):
		self.approve()
		self.assertEqual(self.f.order.workflow_state, "已批准")
		self.assertEqual(frappe.db.count("Job Card", {"work_order": self.f.order.name}), 3)
		self.assertFalse(frappe.db.exists("Stock Entry", {"work_order": self.f.order.name}))

	def test_approved_plan_date_cannot_be_changed(self):
		self.approve()
		old_date = self.f.order.planned_start_date
		self.f.order.planned_start_date = add_days(old_date, 1)
		with self.assertRaises(frappe.PermissionError):
			self.f.order.save()
		self.f.order.reload()
		self.assertEqual(self.f.order.planned_start_date, old_date)

	def test_initiator_can_terminate_pending_request_with_reason(self):
		self.f.act("operator", "送审")
		self.f.act("operator", "终止", reason="该生产需求取消")
		self.assertEqual(self.f.order.workflow_state, "终止")
		self.assertEqual(self.f.order.docstatus, 0)
		self.assertFalse(frappe.db.exists("Job Card", {"work_order": self.f.order.name}))
		self.assertTrue(frappe.db.exists("Comment", {"reference_doctype": "Work Order",
			"reference_name": self.f.order.name, "comment_type": "Workflow"}))

	def test_stopped_order_cannot_resume_via_native_endpoint(self):
		self.approve()
		self.issue()
		self.stop()
		frappe.set_user(self.f.users["operator"])
		with self.assertRaises(frappe.PermissionError):
			stop_unstop(self.f.order.name, "Not Started")
		self.f.order.reload()
		self.assertEqual(self.f.order.status, "Stopped")

	def test_stopped_order_preserves_material_return(self):
		self.approve()
		self.issue()
		self.stop()
		frappe.set_user(self.f.users["warehouse"])
		returned = make_stock_return_entry(self.f.order.name)
		returned.company = self.f.company
		returned.items[0].cost_center = frappe.get_cached_value("Company", self.f.company, "cost_center")
		returned.submit()
		self.assertEqual(returned.docstatus, 1)
		self.assertEqual(frappe.db.get_value("Bin", {"item_code": self.f.raw, "warehouse": self.f.wip}, "actual_qty"), 0)
		self.f.order.reload()
		self.assertEqual(self.f.order.status, "Stopped")

	def test_stopped_order_preserves_stock_cancellation(self):
		self.approve()
		entry = self.issue()
		self.stop()
		frappe.set_user(self.f.users["warehouse"])
		entry.cancel()
		self.assertEqual(entry.docstatus, 2)
		self.assertTrue(frappe.db.exists("Stock Entry", entry.name))
		self.assertEqual(frappe.db.get_value("Bin", {"item_code": self.f.raw, "warehouse": self.f.wip}, "actual_qty"), 0)
		self.f.order.reload()
		self.assertEqual(self.f.order.status, "Stopped")

	def test_approved_without_facts_can_cancel_and_amend(self):
		self.approve()
		self.f.act("director", "取消修订", reason="计划日期调整后重新审批")
		self.assertEqual(self.f.order.docstatus, 2)
		frappe.set_user(self.f.users["operator"])
		amended = self.copy_request()
		amended.amended_from = self.f.order.name
		amended.planned_start_date = add_days(self.f.order.planned_start_date, 1)
		amended.insert()
		self.assertEqual(amended.workflow_state, "草稿")
		self.assertEqual(amended.docstatus, 0)
		self.assertFalse(amended.approval_reviewed_by)
		self.assertEqual(amended.approval_requested_by, self.f.users["operator"])
		self.assertTrue(frappe.db.exists("Work Order", self.f.order.name))
		self.f.order = amended
		with self.assertRaises(frappe.PermissionError):
			self.f.act("director", "签批通过")
		self.approve()
		self.assertEqual(self.f.order.workflow_state, "已批准")

	def test_close_endpoint_cannot_resume_stopped_order(self):
		self.approve()
		self.issue()
		self.stop()
		frappe.set_user(self.f.users["director"])
		with self.assertRaises(frappe.PermissionError):
			close_work_order(self.f.order.name, "Not Started")
		self.f.order.reload()
		self.assertEqual(self.f.order.status, "Stopped")

	def test_terminate_requires_owner_reason_and_cannot_reopen(self):
		self.f.act("operator", "送审")
		with self.assertRaises(frappe.PermissionError):
			self.f.act("reviewer", "终止", reason="不得代办")
		with self.assertRaises(frappe.ValidationError):
			self.f.act("operator", "终止", reason=" ")
		self.f.act("operator", "终止", reason="需求取消")
		with self.assertRaises(frappe.PermissionError):
			self.f.act("operator", "送审")
		self.f.order.qty = 11
		with self.assertRaises(frappe.PermissionError):
			self.f.order.save()

	def test_stop_requires_director_reason_and_viewed_version(self):
		self.approve()
		for role in ("operator", "reviewer", "other"):
			with self.subTest(role=role), self.assertRaises(frappe.PermissionError):
				self.f.act(role, "停止执行", reason="无权停止")
		with self.assertRaises(frappe.ValidationError):
			self.f.act("director", "停止执行", reason=" ")
		with self.assertRaises(frappe.TimestampMismatchError):
			self.f.act("director", "停止执行", version="2000-01-01", reason="旧页面")
		self.stop()
		self.assertTrue(frappe.db.exists("Comment", {"reference_doctype": "Work Order",
			"reference_name": self.f.order.name, "content": ["like", "%停止执行%"]}))

	def test_direct_cancel_and_stop_cannot_skip_controlled_action(self):
		self.approve()
		with self.assertRaises(frappe.PermissionError):
			self.f.order.cancel()
		self.f.order.reload()
		with self.assertRaises(frappe.PermissionError):
			stop_unstop(self.f.order.name, "Stopped")
		self.f.order.reload()
		self.assertEqual(self.f.order.docstatus, 1)
		self.assertEqual(self.f.order.status, "Not Started")

	def test_stock_history_prevents_cancel_even_after_reversal(self):
		self.approve()
		entry = self.issue()
		for reversed_entry in (False, True):
			if reversed_entry:
				frappe.set_user(self.f.users["warehouse"])
				entry.cancel()
				self.f.order.reload()
			with self.subTest(reversed=reversed_entry), self.assertRaises(frappe.PermissionError):
				self.f.act("director", "取消修订", reason="有领料历史不能取消原单")
			self.f.order.reload()
			self.assertEqual(self.f.order.docstatus, 1)

	def test_timer_history_prevents_work_order_cancellation(self):
		from erpnext.manufacturing.doctype.job_card.job_card import make_time_log
		self.approve()
		card = frappe.get_doc("Job Card", {"work_order": self.f.order.name, "operation": self.f.operations[0]})
		frappe.set_user(self.f.users["operator"])
		make_time_log({"job_card_id": card.name, "start_time": now(), "status": "Work In Progress", "employees": []})
		self.f.order.reload()
		with self.assertRaises(frappe.PermissionError):
			self.f.act("director", "取消修订", reason="已有计时不能取消原单")
		self.f.order.reload()
		self.assertEqual(self.f.order.docstatus, 1)
		card.reload()
		self.assertEqual(len(card.time_logs), 1)

	def test_stopped_order_denies_new_stock_and_timer(self):
		from erpnext.manufacturing.doctype.job_card.job_card import make_time_log
		self.approve()
		self.issue()
		self.stop()
		case = test_stock_entry.TestStockExecutionApproval()
		case.f = self.f
		frappe.set_user(self.f.users["warehouse"])
		with self.assertRaises(frappe.PermissionError):
			case.transfer(self.f.order).insert().submit()
		card = frappe.get_doc("Job Card", {"work_order": self.f.order.name, "operation": self.f.operations[0]})
		frappe.set_user(self.f.users["operator"])
		with self.assertRaises(frappe.PermissionError):
			make_time_log({"job_card_id": card.name, "start_time": now(), "status": "Work In Progress", "employees": []})
		card.reload()
		self.assertFalse(card.time_logs)
		self.assertEqual(frappe.db.get_value("Bin", {"item_code": self.f.raw, "warehouse": self.f.wip}, "actual_qty"), 1)

	def test_remaining_demand_is_new_linked_request_without_inherited_approval(self):
		self.approve()
		self.issue()
		self.stop()
		frappe.set_user(self.f.users["operator"])
		new = self.copy_request()
		new.previous_work_order = self.f.order.name
		new.qty = 6
		new.insert()
		new.reload()
		self.assertEqual(new.workflow_state, "草稿")
		self.assertEqual(new.docstatus, 0)
		self.assertEqual(new.previous_work_order, self.f.order.name)
		self.assertFalse(new.amended_from)
		self.assertFalse(new.approval_reviewed_by)
		self.assertFalse(frappe.db.exists("Job Card", {"work_order": new.name}))
		self.f.order.reload()
		self.assertEqual(self.f.order.qty, 10)
		self.assertEqual(self.f.order.status, "Stopped")
		self.f.order = new
		with self.assertRaises(frappe.PermissionError):
			self.f.act("director", "签批通过")
		self.approve()
		self.assertEqual(self.f.order.workflow_state, "已批准")

	def test_new_request_cannot_link_an_unstopped_or_unreadable_order(self):
		self.approve()
		self.issue()
		frappe.set_user(self.f.users["operator"])
		new = self.copy_request()
		new.previous_work_order = self.f.order.name
		with self.assertRaises(frappe.PermissionError):
			new.insert()
		self.stop()
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.f.users["other"]).add_roles(self.f.roles[0])
		frappe.set_user(self.f.users["other"])
		new = make_wo_order_test_record(**self.f.order_args)
		new.production_team = self.f.teams[1]
		new.previous_work_order = self.f.order.name
		with self.assertRaises(frappe.PermissionError):
			new.insert()


	def test_draft_cannot_repoint_remaining_demand_to_unstopped_source(self):
		self.approve()
		self.issue()
		frappe.set_user(self.f.users["operator"])
		draft = make_wo_order_test_record(**self.f.order_args)
		draft.production_team = self.f.teams[0]
		draft.insert()
		draft.previous_work_order = self.f.order.name
		with self.assertRaises(frappe.PermissionError):
			draft.save()
		draft.reload()
		self.assertFalse(draft.previous_work_order)

	def test_cancel_partial_manufacture_keeps_approval_order_stopped(self):
		frappe.set_user(self.f.users["operator"])
		self.f.order.skip_transfer = 1
		self.f.order.set("operations", [])
		self.f.order.save()
		self.approve()
		frappe.set_user(self.f.users["warehouse"])
		entries = []
		for _ in range(2):
			entry = frappe.get_doc(make_stock_entry(self.f.order.name, "Manufacture", 2))
			entry.insert().submit()
			entries.append(entry)
		self.f.order.reload()
		self.assertEqual(self.f.order.produced_qty, 4)
		self.stop()
		frappe.set_user(self.f.users["warehouse"])
		entries[-1].cancel()
		self.f.order.reload()
		self.assertEqual(self.f.order.produced_qty, 2)
		self.assertEqual(self.f.order.status, "Stopped")
		self.assertEqual(frappe.db.get_value("Stock Entry", entries[0].name, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Stock Entry", entries[1].name, "docstatus"), 2)


class TestWorkOrderRequiredQuantity(FrappeTestCase):
	"""Final demand, saved values and native stock consumers share one result."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(self.clean_fixture)
		self.assertFalse(frappe.db.exists("Workflow", {"document_type": "Work Order"}))

	def clean_fixture(self):
		frappe.db.rollback()
		frappe.clear_cache()

	def make_quantity_order(self, raw_qty, planned=3, parent_qty=1):
		from frappe.utils.nestedset import get_root_of
		import erpnext

		prefix = "B04-" + frappe.generate_hash(length=8)
		company = erpnext.get_default_company()
		warehouses = [frappe.get_doc({"doctype": "Warehouse", "company": company,
			"warehouse_name": prefix + suffix}).insert().name for suffix in ("-原料", "-在制", "-成品")]
		unit = frappe.get_doc({"doctype": "UOM", "uom_name": prefix, "must_be_whole_number": 0}).insert().name
		raw = make_item(prefix + "-RM", {"item_group": get_root_of("Item Group"), "is_stock_item": 1,
			"stock_uom": unit, "valuation_method": "Moving Average"})
		finished = make_item(prefix + "-FG", {"item_group": get_root_of("Item Group"), "is_stock_item": 1, "stock_uom": "Nos"})
		bom = make_bom(item=finished.name, company=company,
			currency=frappe.get_cached_value("Company", company, "default_currency"),
			quantity=parent_qty, raw_materials=[raw.name], rm_qty=raw_qty, rate=2,
			source_warehouse=warehouses[0], with_operations=False)
		order = make_wo_order_test_record(item=finished.name, bom_no=bom.name, qty=planned,
			company=company, stock_uom="Nos", source_warehouse=warehouses[0],
			wip_warehouse=warehouses[1], fg_warehouse=warehouses[2], do_not_save=True)
		return order, raw, bom

	@change_settings("System Settings", {"float_precision": 6})
	def test_quantity_fixture_runnable(self):
		order, raw, bom = self.make_quantity_order(0.5, planned=10)
		order.insert()
		order.reload()
		self.assertEqual(order.required_items[0].required_qty, 5)
		self.assertEqual(bom.docstatus, 1)
		self.assertEqual(order.required_items[0].item_code, raw.name)

	@change_settings("System Settings", {"float_precision": 6})
	def test_required_qty_q05_rounds_at_final_boundary(self):
		order, raw, bom = self.make_quantity_order(0.000050)
		bom.reload()
		self.assertEqual(bom.items[0].qty, 0.000050)
		self.assertEqual(bom.items[0].stock_qty, 0.000050)
		self.assertEqual(order.required_items[0].required_qty, 0.0002)
		order.insert().submit()
		order.reload()
		self.assertEqual(frappe.db.get_value("Work Order Item", order.required_items[0].name, "required_qty"), 0.0002)
		test_stock_entry.make_stock_entry(item_code=raw.name, company=order.company,
			target=order.source_warehouse, qty=1, basic_rate=2)
		entry = frappe.get_doc(make_stock_entry(order.name, "Material Transfer for Manufacture", 3))
		self.assertEqual(entry.items[0].qty, 0.0002)
		entry.insert().submit()
		entry.reload()
		order.reload()
		self.assertEqual(entry.items[0].transfer_qty, 0.0002)
		self.assertEqual(order.required_items[0].required_qty, 0.0002)
		self.assertEqual(order.required_items[0].transferred_qty, 0.0002)
		self.assertEqual(frappe.db.get_value("Bin", {"item_code": raw.name, "warehouse": order.wip_warehouse}, "actual_qty"), 0.0002)

	@change_settings("System Settings", {"float_precision": 6, "rounding_method": "Banker's Rounding"})
	def test_required_qty_reset_uses_commercial_final_rounding(self):
		order, _, _ = self.make_quantity_order(0.000050)
		order.qty = 5
		order.set_required_items(reset_only_qty=True)
		self.assertEqual(order.required_items[0].required_qty, 0.0003)
		order.insert()
		order.reload()
		self.assertEqual(order.required_items[0].required_qty, 0.0003)

	@change_settings("System Settings", {"float_precision": 6})
	def test_reference_quantities_and_parent_base(self):
		for raw_qty, planned, parent_qty, expected in (
			(0.5495, 100, 1, 54.95), (0.083333, 100, 1, 8.3333),
			(0.000167, 100, 1, 0.0167), (0.083333, 100, 2, 4.1667),
		):
			with self.subTest(raw_qty=raw_qty, parent_qty=parent_qty):
				order, _, _ = self.make_quantity_order(raw_qty, planned, parent_qty)
				order.insert()
				order.reload()
				self.assertEqual(order.required_items[0].required_qty, expected)


class TestWorkOrderStockUnits(FrappeTestCase):
	"""Real stock documents exercise consumption totals and cancel recalculation."""

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.local.future_sle = {}
		frappe.db.rollback()
		frappe.clear_cache()

	def make_stock_uom_fixture(self):
		from frappe.utils.nestedset import get_root_of

		import erpnext

		prefix = "B10-" + frappe.generate_hash(length=8)
		company = erpnext.get_default_company()
		warehouses = [
			frappe.get_doc({"doctype": "Warehouse", "company": company, "warehouse_name": prefix + suffix})
			.insert()
			.name
			for suffix in ("-原料", "-在制", "-成品")
		]
		kg, gram = prefix + "-kg", prefix + "-g"
		for unit in (kg, gram):
			frappe.get_doc({"doctype": "UOM", "uom_name": unit, "must_be_whole_number": 0}).insert()
		raw = make_item(
			prefix + "-RM",
			{
				"item_group": get_root_of("Item Group"),
				"is_stock_item": 1,
				"stock_uom": kg,
				"valuation_method": "Moving Average",
			},
			uoms=[{"uom": kg, "conversion_factor": 1}, {"uom": gram, "conversion_factor": 0.001}],
		)
		finished = make_item(
			prefix + "-FG", {"item_group": get_root_of("Item Group"), "is_stock_item": 1, "stock_uom": "Nos"}
		)
		bom = make_bom(
			item=finished.name,
			company=company,
			currency=frappe.get_cached_value("Company", company, "default_currency"),
			quantity=1,
			raw_materials=[raw.name],
			rm_qty=0.001,
			rate=2,
			source_warehouse=warehouses[0],
			with_operations=False,
		)
		test_stock_entry.make_stock_entry(
			item_code=raw.name, company=company, target=warehouses[0], qty=1, basic_rate=2
		)
		order = make_wo_order_test_record(
			item=finished.name,
			bom_no=bom.name,
			qty=1,
			company=company,
			stock_uom="Nos",
			source_warehouse=warehouses[0],
			wip_warehouse=warehouses[1],
			fg_warehouse=warehouses[2],
		)
		transfer = frappe.get_doc(make_stock_entry(order.name, "Material Transfer for Manufacture", 1))
		transfer.submit()
		returned = make_stock_return_entry(order.name)
		returned.company = company
		returned.items[0].cost_center = frappe.get_cached_value("Company", company, "cost_center")
		returned.items[0].qty = 0.0004
		returned.submit()
		order.reload()
		self.assertEqual(order.required_items[0].transferred_qty, 0.001)
		self.assertEqual(order.required_items[0].returned_qty, 0.0004)
		self.assertEqual(
			frappe.db.get_value("Bin", {"item_code": raw.name, "warehouse": warehouses[1]}, "actual_qty"),
			0.0006,
		)
		return frappe._dict(order=order, raw=raw.name, kg=kg, gram=gram, warehouses=warehouses)

	def consumption_draft(self, order, raw, qty, uom, factor):
		doc = frappe.new_doc("Stock Entry")
		doc.update(
			{
				"company": order.company,
				"purpose": "Material Consumption for Manufacture",
				"work_order": order.name,
				"from_bom": 1,
				"bom_no": order.bom_no,
				"fg_completed_qty": order.qty,
				"from_warehouse": order.wip_warehouse,
			}
		)
		doc.set_stock_entry_type()
		doc.append(
			"items",
			{
				"item_code": raw,
				"s_warehouse": order.wip_warehouse,
				"qty": qty,
				"uom": uom,
				"conversion_factor": factor,
			},
		)
		return doc

	@change_settings("System Settings", {"float_precision": 6})
	@change_settings(
		"Manufacturing Settings",
		{
			"material_consumption": 1,
			"disable_capacity_planning": 1,
			"backflush_raw_materials_based_on": "Material Transferred for Manufacture",
		},
	)
	def test_consumed_qty_uses_stock_uom(self):
		fixture = self.make_stock_uom_fixture()
		consumption = self.consumption_draft(fixture.order, fixture.raw, 0.5, fixture.gram, 0.001)
		consumption.submit()
		consumption.reload()
		fixture.order.reload()
		self.assertEqual(consumption.items[0].qty, 0.5)
		self.assertEqual(consumption.items[0].uom, fixture.gram)
		self.assertEqual(consumption.items[0].transfer_qty, 0.0005)
		self.assertEqual(fixture.order.required_items[0].consumed_qty, 0.0005)
		self.assertEqual(
			frappe.db.get_value(
				"Bin", {"item_code": fixture.raw, "warehouse": fixture.warehouses[1]}, "actual_qty"
			),
			0.0001,
		)
		consumption.cancel()
		fixture.order.reload()
		self.assertEqual(fixture.order.required_items[0].consumed_qty, 0)
		self.assertEqual(
			frappe.db.get_value(
				"Bin", {"item_code": fixture.raw, "warehouse": fixture.warehouses[1]}, "actual_qty"
			),
			0.0006,
		)
		self.assertEqual(frappe.db.get_value("Stock Entry", consumption.name, "docstatus"), 2)
		self.assertEqual(frappe.db.get_value("Stock Entry Detail", consumption.items[0].name, "qty"), 0.5)

	@change_settings("System Settings", {"float_precision": 6})
	@change_settings(
		"Manufacturing Settings",
		{
			"material_consumption": 1,
			"disable_capacity_planning": 1,
			"backflush_raw_materials_based_on": "Material Transferred for Manufacture",
		},
	)
	def test_consumed_qty_keeps_order_and_document_status_filters(self):
		fixture = self.make_stock_uom_fixture()
		order = fixture.order
		other = make_wo_order_test_record(
			item=order.production_item,
			bom_no=order.bom_no,
			qty=1,
			company=order.company,
			stock_uom="Nos",
			source_warehouse=order.source_warehouse,
			wip_warehouse=order.wip_warehouse,
			fg_warehouse=order.fg_warehouse,
		)
		frappe.get_doc(make_stock_entry(other.name, "Material Transfer for Manufacture", 1)).submit()
		self.consumption_draft(other, fixture.raw, 0.0002, fixture.kg, 1).submit()
		draft = self.consumption_draft(order, fixture.raw, 0.0003, fixture.kg, 1).insert()
		order.update_consumed_qty_for_required_items()
		order.reload()
		self.assertEqual(order.required_items[0].consumed_qty, 0)
		draft.submit()
		order.reload()
		self.assertEqual(order.required_items[0].consumed_qty, 0.0003)
		other.reload()
		self.assertEqual(other.required_items[0].consumed_qty, 0.0002)
		draft.cancel()
		order.reload()
		self.assertEqual(order.required_items[0].consumed_qty, 0)
		other.reload()
		self.assertEqual(other.required_items[0].consumed_qty, 0.0002)


class TestWorkOrder(FrappeTestCase):
	def setUp(self):
		self.warehouse = "_Test Warehouse 2 - _TC"
		self.item = "_Test Item"
		prepare_data_for_backflush_based_on_materials_transferred()

	def tearDown(self):
		frappe.local.future_sle = {}
		frappe.db.rollback()

	def check_planned_qty(self):
		planned0 = (
			frappe.db.get_value(
				"Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"
			)
			or 0
		)

		wo_order = make_wo_order_test_record()

		planned1 = frappe.db.get_value(
			"Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"
		)

		self.assertEqual(planned1, planned0 + 10)

		# add raw materials to stores
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="Stores - _TC", qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Stores - _TC", qty=100, basic_rate=100
		)

		# from stores to wip
		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 4))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		# from wip to fg
		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 4))
		s.insert()
		s.submit()

		self.assertEqual(frappe.db.get_value("Work Order", wo_order.name, "produced_qty"), 4)

		planned2 = frappe.db.get_value(
			"Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"
		)

		self.assertEqual(planned2, planned0 + 6)

		return wo_order

	def test_actual_dates_ignore_unsubmitted_stock_entries(self):
		work_order = self.make_work_order_for_actual_dates()
		for posting_time in ("02:00:00", "22:00:00"):
			entry = self.make_manufacture_for_actual_dates(work_order, posting_time)
			entry.submit()
			entry.cancel()
		for posting_time in ("01:30:00", "23:00:00"):
			draft = self.make_manufacture_for_actual_dates(work_order, posting_time, qty=1)
			entry = self.make_manufacture_for_actual_dates(work_order, "05:00:00")
			entry.submit()
			work_order.reload()
			self.assertEqual(work_order.status, "Completed")
			self.assertEqual(work_order.actual_start_date, get_datetime(f"{today()} 05:00:00"))
			self.assertEqual(work_order.actual_end_date, work_order.actual_start_date)
			entry.cancel()
			draft.delete()

	def test_actual_dates_recompute_on_cancellation(self):
		work_order = self.make_work_order_for_actual_dates()
		first = self.make_manufacture_for_actual_dates(work_order, "03:00:00", qty=1)
		first.submit()
		last = self.make_manufacture_for_actual_dates(work_order, "05:00:00", qty=1)
		last.submit()
		work_order.reload()
		self.assertEqual(work_order.actual_start_date, get_datetime(f"{today()} 03:00:00"))
		self.assertEqual(work_order.actual_end_date, get_datetime(f"{today()} 05:00:00"))

		first.cancel()
		work_order.reload()
		self.assertNotEqual(work_order.status, "Completed")
		self.assertEqual(work_order.actual_start_date, get_datetime(f"{today()} 05:00:00"))
		self.assertIsNone(work_order.actual_end_date)
		last.cancel()
		work_order.reload()
		self.assertIsNone(work_order.actual_start_date)
		self.assertIsNone(work_order.actual_end_date)

	def make_work_order_for_actual_dates(self):
		for item in ("_Test Item", "_Test Item Home Desktop 100"):
			test_stock_entry.make_stock_entry(
				item_code=item,
				target="Stores - _TC",
				qty=100,
				basic_rate=100,
				posting_date=today(),
				posting_time="01:00:00",
			)
		work_order = make_wo_order_test_record(qty=2, source_warehouse="Stores - _TC", skip_transfer=1)
		self.assertFalse(work_order.operations)
		return work_order

	def make_manufacture_for_actual_dates(self, work_order, posting_time, qty=2):
		entry = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", qty))
		entry.update({"set_posting_time": 1, "posting_date": today(), "posting_time": posting_time})
		return entry.insert()

	def test_disassembled_qty_sums_without_float_noise(self):
		wo = frappe.new_doc("Work Order")
		wo.update({"docstatus": 1, "produced_qty": 0.3, "disassembled_qty": 0.1})
		with patch.object(wo, "db_set"):
			wo.update_disassembled_qty(0.2)

		self.assertEqual(wo.disassembled_qty, 0.3)

	def test_disassembly_available_qty_has_no_float_noise(self):
		from erpnext.manufacturing.doctype.work_order.work_order import get_disassembly_available_qty

		real_get_value = frappe.db.get_value

		def get_value(doctype, filters=None, *args, **kwargs):
			if doctype != "Stock Entry":
				return real_get_value(doctype, filters, *args, **kwargs)
			return frappe._dict(fg_completed_qty=0.3) if isinstance(filters, str) else 0.1

		with patch.object(frappe.db, "get_value", side_effect=get_value):
			self.assertEqual(get_disassembly_available_qty("Manufacture Entry"), 0.2)

	def test_over_production(self):
		wo_doc = self.check_planned_qty()

		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=100, basic_rate=100
		)

		s = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 7))
		s.insert()

		self.assertRaises(StockOverProductionError, s.submit)

	def test_planned_operating_cost(self):
		wo_order = make_wo_order_test_record(
			item="_Test FG Item 2", planned_start_date=now(), qty=1, do_not_save=True
		)
		wo_order.set_work_order_operations()
		cost = wo_order.planned_operating_cost
		wo_order.qty = 2
		wo_order.set_work_order_operations()
		self.assertEqual(wo_order.planned_operating_cost, cost * 2)

	def test_reserved_qty_for_partial_completion(self):
		item = "_Test Item"
		warehouse = "_Test Warehouse - _TC"

		bin1_at_start = get_bin(item, warehouse)

		# reset to correct value
		bin1_at_start.update_reserved_qty_for_production()

		wo_order = make_wo_order_test_record(
			item="_Test FG Item", qty=2, source_warehouse=warehouse, skip_transfer=1
		)

		reserved_qty_on_submission = cint(get_bin(item, warehouse).reserved_qty_for_production)

		# reserved qty for production is updated
		self.assertEqual(cint(bin1_at_start.reserved_qty_for_production) + 2, reserved_qty_on_submission)

		test_stock_entry.make_stock_entry(item_code="_Test Item", target=warehouse, qty=100, basic_rate=100)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target=warehouse, qty=100, basic_rate=100
		)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 1))
		s.submit()

		bin1_at_completion = get_bin(item, warehouse)

		self.assertEqual(cint(bin1_at_completion.reserved_qty_for_production), reserved_qty_on_submission - 1)

	def test_production_item(self):
		wo_order = make_wo_order_test_record(item="_Test FG Item", qty=1, do_not_save=True)
		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", "2000-1-1")

		self.assertRaises(frappe.ValidationError, wo_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", None)
		frappe.db.set_value("Item", "_Test FG Item", "disabled", 1)

		self.assertRaises(frappe.ValidationError, wo_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "disabled", 0)

		wo_order = make_wo_order_test_record(item="_Test Variant Item", qty=1, do_not_save=True)
		self.assertRaises(ItemHasVariantError, wo_order.save)

	def test_reserved_qty_for_production_submit(self):
		self.bin1_at_start = get_bin(self.item, self.warehouse)

		# reset to correct value
		self.bin1_at_start.update_reserved_qty_for_production()

		self.wo_order = make_wo_order_test_record(
			item="_Test FG Item", qty=2, source_warehouse=self.warehouse
		)

		self.bin1_on_submit = get_bin(self.item, self.warehouse)

		# reserved qty for production is updated
		self.assertEqual(
			cint(self.bin1_at_start.reserved_qty_for_production) + 2,
			cint(self.bin1_on_submit.reserved_qty_for_production),
		)
		self.assertEqual(cint(self.bin1_at_start.projected_qty), cint(self.bin1_on_submit.projected_qty) + 2)

	def test_reserved_qty_for_production_cancel(self):
		self.test_reserved_qty_for_production_submit()

		self.wo_order.cancel()

		bin1_on_cancel = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(
			cint(self.bin1_at_start.reserved_qty_for_production),
			cint(bin1_on_cancel.reserved_qty_for_production),
		)
		self.assertEqual(self.bin1_at_start.projected_qty, cint(bin1_on_cancel.projected_qty))

	def test_reserved_qty_for_production_on_stock_entry(self):
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target=self.warehouse, qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target=self.warehouse, qty=100, basic_rate=100
		)

		self.test_reserved_qty_for_production_submit()

		s = frappe.get_doc(make_stock_entry(self.wo_order.name, "Material Transfer for Manufacture", 2))

		s.submit()

		bin1_on_start_production = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(
			cint(self.bin1_at_start.reserved_qty_for_production),
			cint(bin1_on_start_production.reserved_qty_for_production),
		)

		# projected qty will now be 2 less (becuase of item movement)
		self.assertEqual(
			cint(self.bin1_at_start.projected_qty), cint(bin1_on_start_production.projected_qty) + 2
		)

		s = frappe.get_doc(make_stock_entry(self.wo_order.name, "Manufacture", 2))

		bin1_on_end_production = get_bin(self.item, self.warehouse)

		# no change in reserved / projected
		self.assertEqual(
			cint(bin1_on_end_production.reserved_qty_for_production),
			cint(bin1_on_start_production.reserved_qty_for_production),
		)

	def test_reserved_qty_for_production_closed(self):
		wo1 = make_wo_order_test_record(item="_Test FG Item", qty=2, source_warehouse=self.warehouse)
		item = wo1.required_items[0].item_code
		bin_before = get_bin(item, self.warehouse)
		bin_before.update_reserved_qty_for_production()

		make_wo_order_test_record(item="_Test FG Item", qty=2, source_warehouse=self.warehouse)
		close_work_order(wo1.name, "Closed")

		bin_after = get_bin(item, self.warehouse)
		self.assertEqual(bin_before.reserved_qty_for_production, bin_after.reserved_qty_for_production)

	def test_backflush_qty_for_overpduction_manufacture(self):
		cancel_stock_entry = []
		allow_overproduction("overproduction_percentage_for_work_order", 30)
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=100)
		ste1 = test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=120, basic_rate=5000.0
		)
		ste2 = test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=240,
			basic_rate=1000.0,
		)

		cancel_stock_entry.extend([ste1.name, ste2.name])

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 60))
		s.submit()
		cancel_stock_entry.append(s.name)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 60))
		s.submit()
		cancel_stock_entry.append(s.name)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 60))
		s.submit()
		cancel_stock_entry.append(s.name)

		s1 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 50))
		s1.submit()
		cancel_stock_entry.append(s1.name)

		self.assertEqual(s1.items[0].qty, 50)
		self.assertEqual(s1.items[1].qty, 100)
		cancel_stock_entry.reverse()
		for ste in cancel_stock_entry:
			doc = frappe.get_doc("Stock Entry", ste)
			doc.cancel()

		allow_overproduction("overproduction_percentage_for_work_order", 0)

	def test_reserved_qty_for_stopped_production(self):
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target=self.warehouse, qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target=self.warehouse, qty=100, basic_rate=100
		)

		# 	0 0 0

		self.test_reserved_qty_for_production_submit()

		# 2 0 -2

		s = frappe.get_doc(make_stock_entry(self.wo_order.name, "Material Transfer for Manufacture", 1))

		s.submit()

		# 1 -1 0

		bin1_on_start_production = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(
			cint(self.bin1_at_start.reserved_qty_for_production) + 1,
			cint(bin1_on_start_production.reserved_qty_for_production),
		)

		# projected qty will now be 2 less (becuase of item movement)
		self.assertEqual(
			cint(self.bin1_at_start.projected_qty), cint(bin1_on_start_production.projected_qty) + 2
		)

		# STOP
		stop_unstop(self.wo_order.name, "Stopped")

		bin1_on_stop_production = get_bin(self.item, self.warehouse)

		# no change in reserved / projected
		self.assertEqual(
			cint(bin1_on_stop_production.reserved_qty_for_production),
			cint(self.bin1_at_start.reserved_qty_for_production),
		)
		self.assertEqual(
			cint(bin1_on_stop_production.projected_qty) + 1, cint(self.bin1_at_start.projected_qty)
		)

	def test_scrap_material_qty(self):
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=2)

		# add raw materials to stores
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="Stores - _TC", qty=10, basic_rate=5000.0
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, basic_rate=1000.0
		)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 2))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		s.insert()
		s.submit()

		wo_order_details = frappe.db.get_value(
			"Work Order", wo_order.name, ["scrap_warehouse", "qty", "produced_qty", "bom_no"], as_dict=1
		)

		scrap_item_details = get_scrap_item_details(wo_order_details.bom_no)

		self.assertEqual(wo_order_details.produced_qty, 2)

		for item in s.items:
			if item.bom_no and item.item_code in scrap_item_details:
				self.assertEqual(wo_order_details.scrap_warehouse, item.t_warehouse)
				self.assertEqual(
					flt(wo_order_details.qty) * flt(scrap_item_details[item.item_code]), item.qty
				)

	def test_allow_overproduction(self):
		allow_overproduction("overproduction_percentage_for_work_order", 0)
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=2)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=10, basic_rate=5000.0
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=10,
			basic_rate=1000.0,
		)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 3))
		s.insert()
		self.assertRaises(StockOverProductionError, s.submit)

		allow_overproduction("overproduction_percentage_for_work_order", 50)
		s.load_from_db()
		s.submit()
		self.assertEqual(s.docstatus, 1)

		allow_overproduction("overproduction_percentage_for_work_order", 0)

	def test_over_production_for_sales_order(self):
		so = make_sales_order(item_code="_Test FG Item", qty=2)

		allow_overproduction("overproduction_percentage_for_sales_order", 0)
		wo_order = make_wo_order_test_record(
			planned_start_date=now(), sales_order=so.name, qty=3, do_not_save=True
		)

		self.assertRaises(OverProductionError, wo_order.save)

		allow_overproduction("overproduction_percentage_for_sales_order", 50)
		wo_order = make_wo_order_test_record(planned_start_date=now(), sales_order=so.name, qty=3)

		self.assertEqual(wo_order.docstatus, 1)

		allow_overproduction("overproduction_percentage_for_sales_order", 0)

	def test_work_order_with_non_stock_item(self):
		items = {
			"Finished Good Test Item For non stock": 1,
			"_Test FG Item": 1,
			"_Test FG Non Stock Item": 0,
		}
		for item, is_stock_item in items.items():
			make_item(item, {"is_stock_item": is_stock_item})

		if not frappe.db.get_value("Item Price", {"item_code": "_Test FG Non Stock Item"}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": "_Test FG Non Stock Item",
					"price_list_rate": 1000,
					"price_list": "_Test Price List India",
				}
			).insert(ignore_permissions=True)

		fg_item = "Finished Good Test Item For non stock"
		test_stock_entry.make_stock_entry(
			item_code="_Test FG Item", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)

		if not frappe.db.get_value("BOM", {"item": fg_item, "docstatus": 1}):
			bom = make_bom(
				item=fg_item,
				rate=1000,
				raw_materials=["_Test FG Item", "_Test FG Non Stock Item"],
				do_not_save=True,
			)
			bom.rm_cost_as_per = "Price List"  # non stock item won't have valuation rate
			bom.buying_price_list = "_Test Price List India"
			bom.currency = "INR"
			bom.save()

		wo = make_wo_order_test_record(production_item=fg_item)

		se = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
		se.insert()
		se.submit()

		ste = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
		ste.insert()
		self.assertEqual(len(ste.additional_costs), 1)
		self.assertEqual(ste.total_additional_costs, 1000)

	@timeout(seconds=60)
	def test_job_card(self):
		stock_entries = []
		bom = frappe.get_doc("BOM", {"docstatus": 1, "with_operations": 1, "company": "_Test Company"})

		work_order = make_wo_order_test_record(
			item=bom.item, qty=1, bom_no=bom.name, source_warehouse="_Test Warehouse - _TC"
		)

		for row in work_order.required_items:
			stock_entry_doc = test_stock_entry.make_stock_entry(
				item_code=row.item_code, target="_Test Warehouse - _TC", qty=row.required_qty, basic_rate=100
			)
			stock_entries.append(stock_entry_doc)

		ste = frappe.get_doc(make_stock_entry(work_order.name, "Material Transfer for Manufacture", 1))
		ste.submit()
		stock_entries.append(ste)

		job_cards = frappe.get_all(
			"Job Card", filters={"work_order": work_order.name}, order_by="creation asc"
		)
		self.assertEqual(len(job_cards), len(bom.operations))

		for _i, job_card in enumerate(job_cards):
			doc = frappe.get_doc("Job Card", job_card)
			for row in doc.scheduled_time_logs:
				doc.append(
					"time_logs",
					{
						"from_time": row.from_time,
						"to_time": row.to_time,
						"time_in_mins": row.time_in_mins,
					},
				)

			doc.time_logs[0].completed_qty = 1
			doc.submit()

		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 1))
		ste1.submit()
		stock_entries.append(ste1)

		for job_card in job_cards:
			doc = frappe.get_doc("Job Card", job_card)
			self.assertRaises(JobCardCancelError, doc.cancel)

		stock_entries.reverse()
		for stock_entry in stock_entries:
			stock_entry.cancel()

	def test_skip_transfer_work_order_completed_with_fractional_process_loss(self):
		# 11.2 + 0.2 == 11.399999999999999 in float, which must still complete 11.4
		work_order = frappe.new_doc("Work Order")
		work_order.update(
			{"docstatus": 1, "skip_transfer": 1, "qty": 11.4, "produced_qty": 11.2, "process_loss_qty": 0.2}
		)

		self.assertEqual(work_order.get_status(), "Completed")

	def test_work_order_material_transferred_qty_with_process_loss(self):
		stock_entries = []
		item_code = make_item("_Test Item For Process Loss", {"is_stock_item": 1}).name
		rm_item_code = make_item("Test Item For Process Loss RM", {"is_stock_item": 1}).name

		bom = make_bom(
			item=item_code,
			raw_materials=[rm_item_code],
			with_operations=1,
			do_not_save=True,
		)

		operation_name = "_Test Custom Operation"
		workstation_name = "_Test Custom Workstation"

		if not frappe.db.exists("Workstation", workstation_name):
			doc = frappe.new_doc("Workstation")
			doc.workstation_name = workstation_name
			doc.save()

		if not frappe.db.exists("Operation", operation_name):
			doc = frappe.new_doc("Operation")
			doc.name = operation_name
			doc.workstation = workstation_name
			doc.save()

		operation = {
			"operation": operation_name,
			"workstation": workstation_name,
			"description": "Test Data",
			"operating_cost": 100,
			"time_in_mins": 40,
		}

		bom.append("operations", operation)
		bom.save()
		bom.submit()

		work_order = make_wo_order_test_record(
			item=bom.item,
			qty=2,
			bom_no=bom.name,
			source_warehouse="_Test Warehouse - _TC",
			transfer_material_against="Job Card",
		)

		self.assertEqual(work_order.qty, 2)

		for row in work_order.required_items:
			stock_entry_doc = test_stock_entry.make_stock_entry(
				item_code=row.item_code, target="_Test Warehouse - _TC", qty=row.required_qty, basic_rate=100
			)
			stock_entries.append(stock_entry_doc)

		job_cards = frappe.get_all(
			"Job Card", filters={"work_order": work_order.name}, order_by="creation asc"
		)

		for row in job_cards:
			transfer_entry_1 = make_stock_entry_from_jc(row.name)
			transfer_entry_1.submit()

			doc = frappe.get_doc("Job Card", row.name)
			for row in doc.scheduled_time_logs:
				doc.append(
					"time_logs",
					{
						"from_time": row.from_time,
						"to_time": row.to_time,
						"time_in_mins": row.time_in_mins,
						"completed_qty": 1,
					},
				)

			doc.save()
			doc.submit()

			self.assertEqual(doc.total_completed_qty, 1)
			self.assertEqual(doc.process_loss_qty, 1)

		work_order.reload()

		self.assertEqual(work_order.material_transferred_for_manufacturing, 2)

		for row in work_order.operations:
			self.assertEqual(row.completed_qty, 1)
			self.assertEqual(row.process_loss_qty, 1)

	def test_capcity_planning(self):
		frappe.db.set_single_value(
			"Manufacturing Settings", {"disable_capacity_planning": 0, "capacity_planning_for_days": 1}
		)

		data = frappe.get_cached_value(
			"BOM",
			{"docstatus": 1, "item": "_Test FG Item 2", "with_operations": 1, "company": "_Test Company"},
			["name", "item"],
		)

		if data:
			bom, bom_item = data

			planned_start_date = add_months(today(), months=-1)
			work_order = make_wo_order_test_record(
				item=bom_item, qty=10, bom_no=bom, planned_start_date=planned_start_date
			)

			work_order1 = make_wo_order_test_record(
				item=bom_item, qty=30, bom_no=bom, planned_start_date=planned_start_date, do_not_submit=1
			)

			self.assertRaises(CapacityError, work_order1.submit)

			frappe.db.set_single_value("Manufacturing Settings", {"capacity_planning_for_days": 30})

			work_order1.reload()
			work_order1.submit()
			self.assertTrue(work_order1.docstatus, 1)

			work_order1.cancel()
			work_order.cancel()

	def test_planned_qty_updates_after_closing_work_order(self):
		item_code = "_Test FG Item"
		fg_warehouse = "_Test Warehouse 1 - _TC"

		planned_before = (
			frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": fg_warehouse}, "planned_qty")
			or 0
		)

		wo = make_wo_order_test_record(item=item_code, fg_warehouse=fg_warehouse, qty=10)

		planned_after_submit = (
			frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": fg_warehouse}, "planned_qty")
			or 0
		)
		self.assertEqual(planned_after_submit, planned_before + 10)

		close_work_order(wo.name, "Closed")

		self.assertEqual(frappe.db.get_value("Work Order", wo.name, "status"), "Closed")

		planned_after_close = (
			frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": fg_warehouse}, "planned_qty")
			or 0
		)
		self.assertEqual(planned_after_close, planned_before)

	def test_work_order_with_non_transfer_item(self):
		frappe.db.set_single_value("Manufacturing Settings", "backflush_raw_materials_based_on", "BOM")

		items = {"Finished Good Transfer Item": 1, "_Test FG Item": 1, "_Test FG Item 1": 0}
		for item, allow_transfer in items.items():
			make_item(item, {"include_item_in_manufacturing": allow_transfer})

		fg_item = "Finished Good Transfer Item"
		test_stock_entry.make_stock_entry(
			item_code="_Test FG Item", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test FG Item 1", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)

		if not frappe.db.get_value("BOM", {"item": fg_item}):
			make_bom(item=fg_item, raw_materials=["_Test FG Item", "_Test FG Item 1"])

		wo = make_wo_order_test_record(production_item=fg_item)
		ste = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
		ste.insert()
		ste.submit()
		self.assertEqual(len(ste.items), 1)
		ste1 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
		self.assertEqual(len(ste1.items), 3)

	def test_cost_center_for_manufacture(self):
		wo_order = make_wo_order_test_record()
		ste = make_stock_entry(wo_order.name, "Material Transfer for Manufacture", wo_order.qty)
		self.assertEqual(ste.get("items")[0].get("cost_center"), "_Test Cost Center - _TC")

	@change_settings("Manufacturing Settings", {"make_serial_no_batch_from_work_order": 0})
	def test_cost_center_for_manufacture_falls_back_to_item_group_default(self):
		# "_Test Item Group" is master data with buying_cost_center already set to
		# "_Test Cost Center 2 - _TC" for "_Test Company"; only the FG item and its
		# BOM need to be created, since no existing item in that group has one.
		fg_item = make_item(
			"_Test FG Item For Item Group Cost Center",
			{"is_stock_item": 1, "item_group": "_Test Item Group", "include_item_in_manufacturing": 1},
		)

		if not frappe.db.exists("BOM", {"item": fg_item.name, "is_active": 1, "is_default": 1}):
			make_bom(item=fg_item.name, raw_materials=["_Test Item"])

		wo_order = make_wo_order_test_record(
			production_item=fg_item.name, skip_transfer=1, source_warehouse="_Test Warehouse - _TC"
		)
		ste = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", wo_order.qty))
		ste.insert()

		fg_row = next(d for d in ste.items if d.is_finished_item)
		self.assertEqual(fg_row.cost_center, "_Test Cost Center 2 - _TC")

	def test_default_fg_warehouse_prefers_settings_over_item(self):
		fg_item = make_item(
			properties={
				"is_stock_item": 1,
				"item_defaults": [
					{"company": "_Test Company", "default_warehouse": "_Test Warehouse 1 - _TC"}
				],
			}
		).name
		bom = make_bom(item=fg_item, raw_materials=["_Test Item"])
		frappe.db.set_single_value("Manufacturing Settings", "default_fg_warehouse", "_Test Warehouse - _TC")

		def get_fg_warehouse():
			wo = frappe.new_doc(
				"Work Order", company="_Test Company", production_item=fg_item, bom_no=bom.name, qty=1
			)
			wo.get_items_and_operations_from_bom()
			return wo.fg_warehouse

		self.assertEqual(get_fg_warehouse(), "_Test Warehouse - _TC")

		frappe.db.set_single_value("Manufacturing Settings", "default_fg_warehouse", None)
		self.assertEqual(get_fg_warehouse(), "_Test Warehouse 1 - _TC")

	def test_operation_time_with_batch_size(self):
		fg_item = "Test Batch Size Item For BOM"
		rm1 = "Test Batch Size Item RM 1 For BOM"

		for item in ["Test Batch Size Item For BOM", "Test Batch Size Item RM 1 For BOM"]:
			make_item(item, {"include_item_in_manufacturing": 1, "is_stock_item": 1})

		bom_name = frappe.db.get_value("BOM", {"item": fg_item, "is_active": 1, "with_operations": 1}, "name")

		if not bom_name:
			bom = make_bom(item=fg_item, rate=1000, raw_materials=[rm1], do_not_save=True)
			bom.with_operations = 1
			bom.append(
				"operations",
				{
					"operation": "_Test Operation 1",
					"workstation": "_Test Workstation 1",
					"description": "Test Data",
					"operating_cost": 100,
					"time_in_mins": 40,
					"batch_size": 5,
				},
			)

			bom.save()
			bom.submit()
			bom_name = bom.name

		work_order = make_wo_order_test_record(
			item=fg_item, planned_start_date=now(), qty=1, do_not_save=True
		)

		work_order.set_work_order_operations()
		work_order.save()
		self.assertEqual(work_order.operations[0].time_in_mins, 8.0)

		work_order1 = make_wo_order_test_record(
			item=fg_item, planned_start_date=now(), qty=5, do_not_save=True
		)

		work_order1.set_work_order_operations()
		work_order1.save()
		self.assertEqual(work_order1.operations[0].time_in_mins, 40.0)

	def test_batch_size_for_fg_item(self):
		fg_item = "Test Batch Size Item For BOM 3"
		rm1 = "Test Batch Size Item RM 1 For BOM 3"

		frappe.db.set_single_value("Manufacturing Settings", "make_serial_no_batch_from_work_order", 0)
		for item in ["Test Batch Size Item For BOM 3", "Test Batch Size Item RM 1 For BOM 3"]:
			item_args = {"include_item_in_manufacturing": 1, "is_stock_item": 1}

			if item == fg_item:
				item_args["has_batch_no"] = 1
				item_args["create_new_batch"] = 1
				item_args["batch_number_series"] = "TBSI3.#####"

			make_item(item, item_args)

		bom_name = frappe.db.get_value("BOM", {"item": fg_item, "is_active": 1, "with_operations": 1}, "name")

		if not bom_name:
			bom = make_bom(item=fg_item, rate=1000, raw_materials=[rm1], do_not_save=True)
			bom.save()
			bom.submit()
			bom_name = bom.name

		ste1 = test_stock_entry.make_stock_entry(
			item_code=rm1, target="_Test Warehouse - _TC", qty=32, basic_rate=5000.0
		)

		work_order = make_wo_order_test_record(
			item=fg_item, skip_transfer=True, planned_start_date=now(), qty=1
		)
		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 1))
		for row in ste1.get("items"):
			if row.is_finished_item:
				self.assertEqual(row.item_code, fg_item)

		work_order = make_wo_order_test_record(
			item=fg_item, skip_transfer=True, planned_start_date=now(), qty=1
		)
		frappe.db.set_single_value("Manufacturing Settings", "make_serial_no_batch_from_work_order", 1)
		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 1))
		for row in ste1.get("items"):
			if row.is_finished_item:
				self.assertEqual(row.item_code, fg_item)

		work_order = make_wo_order_test_record(
			item=fg_item,
			skip_transfer=True,
			planned_start_date=now(),
			qty=30,
			do_not_save=True,
			source_warehouse="_Test Warehouse - _TC",
		)
		work_order.batch_size = 10
		work_order.insert()
		work_order.submit()
		self.assertEqual(work_order.has_batch_no, 1)
		batches = frappe.get_all("Batch", filters={"reference_name": work_order.name})
		self.assertEqual(len(batches), 3)
		batches = [batch.name for batch in batches]

		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 10))
		for row in ste1.get("items"):
			if row.is_finished_item:
				self.assertEqual(row.item_code, fg_item)
				self.assertEqual(row.qty, 10)

				bundle_id = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
				self.assertEqual(bundle_id.company, ste1.company)
				for bundle_row in bundle_id.get("entries"):
					self.assertTrue(bundle_row.batch_no in batches)
					batches.remove(bundle_row.batch_no)

		ste1.submit()

		remaining_batches = []
		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 20))
		for row in ste1.get("items"):
			if row.is_finished_item:
				self.assertEqual(row.item_code, fg_item)
				self.assertEqual(row.qty, 20)

				bundle_id = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
				self.assertEqual(bundle_id.company, ste1.company)
				for bundle_row in bundle_id.get("entries"):
					self.assertTrue(bundle_row.batch_no in batches)
					remaining_batches.append(bundle_row.batch_no)

		self.assertEqual(sorted(remaining_batches), sorted(batches))

		frappe.db.set_single_value("Manufacturing Settings", "make_serial_no_batch_from_work_order", 0)

	def test_partial_material_consumption(self):
		frappe.db.set_single_value("Manufacturing Settings", "material_consumption", 1)
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=4)

		ste_cancel_list = []
		ste1 = test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=5000.0
		)
		ste2 = test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=20,
			basic_rate=1000.0,
		)

		ste_cancel_list.extend([ste1, ste2])

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 4))
		s.submit()
		ste_cancel_list.append(s)

		ste1 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		ste1.submit()
		ste_cancel_list.append(ste1)

		ste3 = frappe.get_doc(make_stock_entry(wo_order.name, "Material Consumption for Manufacture", 2))
		self.assertEqual(ste3.fg_completed_qty, 2)

		expected_qty = {"_Test Item": 2, "_Test Item Home Desktop 100": 4}
		for row in ste3.items:
			self.assertEqual(row.qty, expected_qty.get(row.item_code))
		ste_cancel_list.reverse()
		for ste_doc in ste_cancel_list:
			ste_doc.cancel()

		frappe.db.set_single_value("Manufacturing Settings", "material_consumption", 0)

	def test_extra_material_transfer(self):
		frappe.db.set_single_value("Manufacturing Settings", "material_consumption", 0)
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=4)

		ste_cancel_list = []
		ste1 = test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=5000.0
		)
		ste2 = test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=20,
			basic_rate=1000.0,
		)

		ste_cancel_list.extend([ste1, ste2])

		itemwise_qty = {}
		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 4))
		for row in s.items:
			row.qty = row.qty + 2
			itemwise_qty.setdefault(row.item_code, row.qty)

		s.submit()
		ste_cancel_list.append(s)

		ste3 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		for ste_row in ste3.items:
			if itemwise_qty.get(ste_row.item_code) and ste_row.s_warehouse:
				self.assertEqual(ste_row.qty, itemwise_qty.get(ste_row.item_code) / 2)

		ste3.submit()
		ste_cancel_list.append(ste3)

		ste2 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		for ste_row in ste2.items:
			if itemwise_qty.get(ste_row.item_code) and ste_row.s_warehouse:
				self.assertEqual(ste_row.qty, itemwise_qty.get(ste_row.item_code) / 2)
		ste_cancel_list.reverse()
		for ste_doc in ste_cancel_list:
			ste_doc.cancel()

		frappe.db.set_single_value("Manufacturing Settings", "backflush_raw_materials_based_on", "BOM")

	def test_make_stock_entry_for_customer_provided_item(self):
		finished_item = "Test Item for Make Stock Entry 1"
		make_item(finished_item, {"include_item_in_manufacturing": 1, "is_stock_item": 1})

		customer_provided_item = "CUST-0987"
		make_item(
			customer_provided_item,
			{
				"is_purchase_item": 0,
				"is_customer_provided_item": 1,
				"is_stock_item": 1,
				"include_item_in_manufacturing": 1,
				"customer": "_Test Customer",
			},
		)

		if not frappe.db.exists("BOM", {"item": finished_item}):
			make_bom(item=finished_item, raw_materials=[customer_provided_item], rm_qty=1)

		company = "_Test Company with perpetual inventory"
		customer_warehouse = create_warehouse("Test Customer Provided Warehouse", company=company)
		wo = make_wo_order_test_record(
			item=finished_item, qty=1, source_warehouse=customer_warehouse, company=company
		)

		ste = frappe.get_doc(make_stock_entry(wo.name, purpose="Material Transfer for Manufacture"))
		ste.insert()

		self.assertEqual(len(ste.items), 1)
		for item in ste.items:
			self.assertEqual(item.allow_zero_valuation_rate, 1)
			self.assertEqual(item.valuation_rate, 0)

	def test_valuation_rate_missing_on_make_stock_entry(self):
		item_name = "Test Valuation Rate Missing"
		rm_item = "_Test raw material item"
		make_item(
			item_name,
			{
				"is_stock_item": 1,
				"include_item_in_manufacturing": 1,
			},
		)
		make_item(
			"_Test raw material item",
			{
				"is_stock_item": 1,
				"include_item_in_manufacturing": 1,
			},
		)

		if not frappe.db.get_value("BOM", {"item": item_name}):
			make_bom(item=item_name, raw_materials=[rm_item], rm_qty=1)

		company = "_Test Company with perpetual inventory"
		source_warehouse = create_warehouse("Test Valuation Rate Missing Warehouse", company=company)
		wo = make_wo_order_test_record(
			item=item_name, qty=1, source_warehouse=source_warehouse, company=company
		)

		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture"))
		self.assertRaises(frappe.ValidationError, stock_entry.save)

	def test_wo_completion_with_pl_bom(self):
		from erpnext.manufacturing.doctype.bom.test_bom import (
			create_bom_with_process_loss_item,
			create_process_loss_bom_items,
		)

		qty = 10
		source_warehouse = "Stores - _TC"
		wip_warehouse = "_Test Warehouse - _TC"
		fg_item_non_whole, _, bom_item = create_process_loss_bom_items()

		test_stock_entry.make_stock_entry(
			item_code=bom_item.item_code, target=source_warehouse, qty=qty, basic_rate=100
		)

		bom_no = f"BOM-{fg_item_non_whole.item_code}-001"
		if not frappe.db.exists("BOM", bom_no):
			bom_doc = create_bom_with_process_loss_item(
				fg_item_non_whole, bom_item, fg_qty=1, process_loss_percentage=10
			)
			bom_doc.submit()

		wo = make_wo_order_test_record(
			production_item=fg_item_non_whole.item_code,
			bom_no=bom_no,
			wip_warehouse=wip_warehouse,
			qty=qty,
			skip_transfer=1,
			source_warehouse=wip_warehouse,
			stock_uom=fg_item_non_whole.stock_uom,
		)

		se = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", qty))
		se.get("items")[0].s_warehouse = "Stores - _TC"
		se.get("items")[0].t_warehouse = wip_warehouse
		se.insert()
		se.submit()

		se = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", qty))
		se.insert()
		se.submit()

		# Testing stock entry values
		items = se.get("items")
		self.assertEqual(len(items), 2, "There should be 3 items including process loss.")
		fg_item = items[1]

		self.assertEqual(fg_item.qty, qty - 1)
		self.assertEqual(se.process_loss_percentage, 10)
		self.assertEqual(se.process_loss_qty, 1)

		wo.load_from_db()
		self.assertEqual(wo.status, "Completed")

		from erpnext.stock.stock_balance import get_planned_qty

		completed_planned_qty = get_bin(wo.production_item, wo.fg_warehouse).planned_qty
		expected_completed_qty = get_planned_qty(wo.production_item, wo.fg_warehouse)

		se.cancel()
		wo.reload()
		self.assertEqual(wo.status, "In Process")
		cancelled_planned_qty = get_bin(wo.production_item, wo.fg_warehouse).planned_qty
		expected_cancelled_qty = get_planned_qty(wo.production_item, wo.fg_warehouse)

		self.assertEqual(completed_planned_qty, expected_completed_qty)
		self.assertEqual(cancelled_planned_qty, expected_cancelled_qty)

	@timeout(seconds=60)
	def test_job_card_scrap_item(self):
		items = [
			"Test FG Item for Scrap Item Test",
			"Test RM Item 1 for Scrap Item Test",
			"Test RM Item 2 for Scrap Item Test",
		]

		job_cards = frappe.get_all(
			"Job Card Time Log",
			fields=["distinct parent as name", "docstatus"],
			order_by="creation asc",
		)

		for job_card in job_cards:
			if job_card.docstatus == 1:
				frappe.get_doc("Job Card", job_card.name).cancel()

			frappe.delete_doc("Job Card Time Log", job_card.name)

		company = "_Test Company with perpetual inventory"
		for item_code in items:
			create_item(
				item_code=item_code,
				is_stock_item=1,
				is_purchase_item=1,
				opening_stock=100,
				valuation_rate=10,
				company=company,
				warehouse="Stores - TCP1",
			)

		item = "Test FG Item for Scrap Item Test"
		raw_materials = ["Test RM Item 1 for Scrap Item Test", "Test RM Item 2 for Scrap Item Test"]
		if not frappe.db.get_value("BOM", {"item": item}):
			bom = make_bom(
				item=item, source_warehouse="Stores - TCP1", raw_materials=raw_materials, do_not_save=True
			)
			bom.with_operations = 1
			bom.append(
				"operations",
				{
					"operation": "_Test Operation 1",
					"workstation": "_Test Workstation 1",
					"hour_rate": 20,
					"time_in_mins": 60,
				},
			)

			bom.submit()

		wo_order = make_wo_order_test_record(
			item=item,
			company=company,
			planned_start_date=now(),
			qty=20,
			skip_transfer=1,
			from_wip_warehouse=1,
		)
		job_card = frappe.db.get_value("Job Card", {"work_order": wo_order.name}, "name")
		update_job_card(job_card)

		stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
		for row in stock_entry.items:
			if row.is_scrap_item:
				self.assertEqual(row.qty, 1)

		# Partial Job Card 1 with qty 10
		wo_order = make_wo_order_test_record(
			item=item,
			company=company,
			planned_start_date=add_days(now(), 60),
			qty=20,
			skip_transfer=1,
			from_wip_warehouse=1,
		)
		job_card = frappe.db.get_value("Job Card", {"work_order": wo_order.name}, "name")
		update_job_card(job_card, 10, 1)

		stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
		for row in stock_entry.items:
			if row.is_scrap_item:
				self.assertEqual(row.qty, 2)

		# Partial Job Card 2 with qty 10
		operations = []
		wo_order.load_from_db()
		for row in wo_order.operations:
			n_dict = row.as_dict()
			n_dict["qty"] = 10
			n_dict["pending_qty"] = 10
			operations.append(n_dict)

		make_job_card(wo_order.name, operations)
		job_card = frappe.db.get_value("Job Card", {"work_order": wo_order.name, "docstatus": 0}, "name")

	def test_close_work_order(self):
		items = [
			"Test FG Item for Closed WO",
			"Test RM Item 1 for Closed WO",
			"Test RM Item 2 for Closed WO",
		]

		company = "_Test Company with perpetual inventory"
		for item_code in items:
			create_item(
				item_code=item_code,
				is_stock_item=1,
				is_purchase_item=1,
				opening_stock=100,
				valuation_rate=10,
				company=company,
				warehouse="Stores - TCP1",
			)

		item = "Test FG Item for Closed WO"
		raw_materials = ["Test RM Item 1 for Closed WO", "Test RM Item 2 for Closed WO"]
		if not frappe.db.get_value("BOM", {"item": item}):
			bom = make_bom(
				item=item, source_warehouse="Stores - TCP1", raw_materials=raw_materials, do_not_save=True
			)
			bom.with_operations = 1
			bom.append(
				"operations",
				{
					"operation": "_Test Operation 1",
					"workstation": "_Test Workstation 1",
					"hour_rate": 20,
					"time_in_mins": 60,
				},
			)

			bom.submit()

		wo_order = make_wo_order_test_record(
			item=item, company=company, planned_start_date=now(), qty=20, skip_transfer=1
		)
		job_cards = frappe.db.get_value("Job Card", {"work_order": wo_order.name}, "name")

		if len(job_cards) == len(bom.operations):
			for jc in job_cards:
				job_card_doc = frappe.get_doc("Job Card", jc)
				job_card_doc.append(
					"time_logs",
					{"from_time": now(), "time_in_mins": 60, "completed_qty": job_card_doc.for_quantity},
				)

				job_card_doc.submit()

			close_work_order(wo_order, "Closed")
			self.assertEqual(wo_order.get("status"), "Closed")

	def test_fix_time_operations(self):
		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"item": "_Test FG Item 2",
				"is_active": 1,
				"is_default": 1,
				"quantity": 1.0,
				"with_operations": 1,
				"operations": [
					{
						"operation": "_Test Operation 1",
						"description": "_Test",
						"workstation": "_Test Workstation 1",
						"time_in_mins": 60,
						"operating_cost": 140,
						"fixed_time": 1,
					}
				],
				"items": [
					{
						"amount": 5000.0,
						"doctype": "BOM Item",
						"item_code": "_Test Item",
						"parentfield": "items",
						"qty": 1.0,
						"rate": 5000.0,
					},
				],
			}
		)
		bom.save()
		bom.submit()

		wo1 = make_wo_order_test_record(
			item=bom.item, bom_no=bom.name, qty=1, skip_transfer=1, do_not_submit=1
		)
		wo2 = make_wo_order_test_record(
			item=bom.item, bom_no=bom.name, qty=2, skip_transfer=1, do_not_submit=1
		)

		self.assertEqual(wo1.operations[0].time_in_mins, wo2.operations[0].time_in_mins)

	def test_partial_manufacture_entries(self):
		cancel_stock_entry = []

		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=100)
		ste1 = test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=120, basic_rate=5000.0
		)
		ste2 = test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=240,
			basic_rate=1000.0,
		)

		cancel_stock_entry.extend([ste1.name, ste2.name])

		sm = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 100))
		for row in sm.get("items"):
			if row.get("item_code") == "_Test Item":
				row.qty = 120

		sm.submit()
		cancel_stock_entry.append(sm.name)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 90))
		for row in s.get("items"):
			if row.get("item_code") == "_Test Item":
				self.assertEqual(row.get("qty"), 108)
		s.submit()
		cancel_stock_entry.append(s.name)

		s1 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 5))
		for row in s1.get("items"):
			if row.get("item_code") == "_Test Item":
				self.assertEqual(row.get("qty"), 6)
		s1.submit()
		cancel_stock_entry.append(s1.name)

		s2 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 5))
		for row in s2.get("items"):
			if row.get("item_code") == "_Test Item":
				self.assertEqual(row.get("qty"), 6)

		cancel_stock_entry.reverse()
		for ste in cancel_stock_entry:
			doc = frappe.get_doc("Stock Entry", ste)
			doc.cancel()

		frappe.db.set_single_value("Manufacturing Settings", "backflush_raw_materials_based_on", "BOM")

	@change_settings("Manufacturing Settings", {"make_serial_no_batch_from_work_order": 1})
	def test_auto_batch_creation(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		fg_item = frappe.generate_hash(length=20)
		child_item = frappe.generate_hash(length=20)

		bom_tree = {fg_item: {child_item: {}}}

		create_nested_bom(bom_tree, prefix="")

		item = frappe.get_doc("Item", fg_item)
		item.has_batch_no = 1
		item.create_new_batch = 0
		item.save()

		try:
			make_wo_order_test_record(item=fg_item)
		except frappe.MandatoryError:
			self.fail("Batch generation causing failing in Work Order")

	@change_settings("Manufacturing Settings", {"make_serial_no_batch_from_work_order": 1})
	def test_auto_serial_no_creation(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		fg_item = frappe.generate_hash(length=20)
		child_item = frappe.generate_hash(length=20)

		bom_tree = {fg_item: {child_item: {}}}

		create_nested_bom(bom_tree, prefix="")

		item = frappe.get_doc("Item", fg_item)
		item.has_serial_no = 1
		item.serial_no_series = f"{item.name}.#####"
		item.save()

		try:
			wo_order = make_wo_order_test_record(item=fg_item, qty=2, skip_transfer=True)
			serial_nos = self.get_serial_nos_for_fg(wo_order.name)

			stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
			stock_entry.set_work_order_details()
			stock_entry.set_serial_no_batch_for_finished_good()
			for row in stock_entry.items:
				if row.item_code == fg_item:
					self.assertTrue(row.serial_and_batch_bundle)
					self.assertEqual(
						sorted(get_serial_nos_from_bundle(row.serial_and_batch_bundle)), sorted(serial_nos)
					)

		except frappe.MandatoryError:
			self.fail("Batch generation causing failing in Work Order")

	@change_settings("Manufacturing Settings", {"make_serial_no_batch_from_work_order": 1})
	def test_auto_serial_no_batch_creation(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		fg_item = frappe.generate_hash(length=20)
		child_item = frappe.generate_hash(length=20)

		bom_tree = {fg_item: {child_item: {}}}

		create_nested_bom(bom_tree, prefix="")

		item = frappe.get_doc("Item", fg_item)
		item.update(
			{
				"has_serial_no": 1,
				"has_batch_no": 1,
				"serial_no_series": f"SN-TEST-{item.name}.#####",
				"create_new_batch": 1,
				"batch_number_series": f"BATCH-TEST-{item.name}.#####",
			}
		)
		item.save()

		try:
			wo_order = make_wo_order_test_record(item=fg_item, batch_size=5, qty=10, skip_transfer=True)
			serial_nos = self.get_serial_nos_for_fg(wo_order.name)

			stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
			stock_entry.set_work_order_details()
			stock_entry.set_serial_no_batch_for_finished_good()
			for row in stock_entry.items:
				if row.item_code == fg_item:
					self.assertTrue(row.serial_and_batch_bundle)
					self.assertEqual(
						sorted(get_serial_nos_from_bundle(row.serial_and_batch_bundle)), sorted(serial_nos)
					)

					sn_doc = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
					for row in sn_doc.entries:
						self.assertTrue(row.serial_no)
						self.assertTrue(row.batch_no)

		except frappe.MandatoryError:
			self.fail("Batch generation causing failing in Work Order")

	def get_serial_nos_for_fg(self, work_order):
		serial_nos = []
		for row in frappe.get_all("Serial No", filters={"work_order": work_order}):
			serial_nos.append(row.name)

		return serial_nos

	@change_settings(
		"Manufacturing Settings",
		{"backflush_raw_materials_based_on": "Material Transferred for Manufacture"},
	)
	def test_manufacture_entry_mapped_idx_with_exploded_bom(self):
		"""Test if WO containing BOM with partial exploded items and scrap items, maps idx correctly."""
		test_stock_entry.make_stock_entry(
			item_code="_Test Item",
			target="_Test Warehouse - _TC",
			basic_rate=5000.0,
			qty=2,
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			basic_rate=1000.0,
			qty=2,
		)

		wo_order = make_wo_order_test_record(
			qty=1,
			use_multi_level_bom=1,
			skip_transfer=1,
		)

		ste_manu = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 1))

		for index, row in enumerate(ste_manu.get("items"), start=1):
			self.assertEqual(index, row.idx)

	@change_settings(
		"Manufacturing Settings",
		{"backflush_raw_materials_based_on": "Material Transferred for Manufacture"},
	)
	def test_work_order_multiple_material_transfer(self):
		"""
		Test transferring multiple RMs in separate Stock Entries.
		"""
		work_order = make_wo_order_test_record(planned_start_date=now(), qty=1)
		test_stock_entry.make_stock_entry(  # stock up RM
			item_code="_Test Item",
			target="_Test Warehouse - _TC",
			qty=1,
			basic_rate=5000.0,
		)
		test_stock_entry.make_stock_entry(  # stock up RM
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=2,
			basic_rate=1000.0,
		)

		transfer_entry = frappe.get_doc(
			make_stock_entry(work_order.name, "Material Transfer for Manufacture", 1)
		)
		del transfer_entry.get("items")[0]  # transfer only one RM
		transfer_entry.submit()

		# WO's "Material Transferred for Mfg" shows all is transferred, one RM is pending
		work_order.reload()
		self.assertEqual(work_order.material_transferred_for_manufacturing, 1)
		self.assertEqual(work_order.required_items[0].transferred_qty, 0)
		self.assertEqual(work_order.required_items[1].transferred_qty, 2)

		final_transfer_entry = frappe.get_doc(  # transfer last RM with For Quantity = 0
			make_stock_entry(work_order.name, "Material Transfer for Manufacture", 0)
		)
		final_transfer_entry.save()

		self.assertEqual(final_transfer_entry.fg_completed_qty, 0.0)
		self.assertEqual(final_transfer_entry.items[0].qty, 1)

		final_transfer_entry.submit()
		work_order.reload()

		# WO's "Material Transferred for Mfg" shows all is transferred, no RM is pending
		self.assertEqual(work_order.material_transferred_for_manufacturing, 1)
		self.assertEqual(work_order.required_items[0].transferred_qty, 1)
		self.assertEqual(work_order.required_items[1].transferred_qty, 2)

	def test_material_transferred_min_fraction_on_partial_pick_list(self):
		"""Pick-list flow (fg_completed_qty = 0): 'Material Transferred for Manufacturing'
		must reflect the least-transferred required item (the bottleneck), instead of being
		marked fully transferred prematurely when only some materials are transferred.
		"""
		work_order = make_wo_order_test_record(planned_start_date=now(), qty=2)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=10, basic_rate=5000.0
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=10, basic_rate=1000.0
		)

		required_qty = {row.item_code: flt(row.required_qty) for row in work_order.required_items}

		# pick-list transfer: For Quantity = 0
		transfer_entry = frappe.get_doc(
			make_stock_entry(work_order.name, "Material Transfer for Manufacture", 0)
		)
		self.assertEqual(transfer_entry.fg_completed_qty, 0.0)

		for item in transfer_entry.items:
			full_qty = required_qty[item.item_code]
			item.qty = full_qty if item.item_code == "_Test Item" else full_qty / 2
			item.transfer_qty = item.qty
		transfer_entry.submit()

		work_order.reload()
		transferred_qty = {row.item_code: flt(row.transferred_qty) for row in work_order.required_items}
		self.assertEqual(transferred_qty["_Test Item"], required_qty["_Test Item"])
		self.assertEqual(
			transferred_qty["_Test Item Home Desktop 100"],
			required_qty["_Test Item Home Desktop 100"] / 2,
		)
		# bottleneck fraction = 0.5 -> 0.5 * qty(2) = 1.0
		self.assertEqual(work_order.material_transferred_for_manufacturing, 1.0)

	def test_material_transferred_full_via_pick_list_flow(self):
		"""Pick-list flow with every required item fully transferred marks the work order
		as fully transferred (min fraction = 1.0)."""
		work_order = make_wo_order_test_record(planned_start_date=now(), qty=2)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=10, basic_rate=5000.0
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=10, basic_rate=1000.0
		)

		required_qty = {row.item_code: flt(row.required_qty) for row in work_order.required_items}

		transfer_entry = frappe.get_doc(
			make_stock_entry(work_order.name, "Material Transfer for Manufacture", 0)
		)
		self.assertEqual(transfer_entry.fg_completed_qty, 0.0)
		for item in transfer_entry.items:
			item.qty = required_qty[item.item_code]
			item.transfer_qty = item.qty
		transfer_entry.submit()

		work_order.reload()
		self.assertEqual(work_order.material_transferred_for_manufacturing, 2.0)

	def test_status_in_process_when_only_one_required_item_transferred(self):
		"""Stock Entry created from a Pick List that picked only one of the required items:
		min-fraction keeps material_transferred_for_manufacturing at 0, but the work order must
		still move to In Process because material is already in WIP."""
		from erpnext.manufacturing.doctype.work_order.work_order import create_pick_list
		from erpnext.stock.doctype.pick_list.pick_list import create_stock_entry

		work_order = make_wo_order_test_record(
			planned_start_date=now(), qty=2, source_warehouse="Stores - _TC"
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="Stores - _TC", qty=10, basic_rate=5000.0
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, basic_rate=1000.0
		)

		pick_list = create_pick_list(work_order.name, for_qty=work_order.qty)
		# pick only _Test Item; the other required item is left out of this pick list
		pick_list.pick_manually = 1
		pick_list.locations = [loc for loc in pick_list.locations if loc.item_code == "_Test Item"]
		pick_list.save()
		pick_list.submit()

		stock_entry = frappe.get_doc(create_stock_entry(frappe.as_json(pick_list.as_dict())))
		self.assertEqual(stock_entry.fg_completed_qty, 0.0)
		stock_entry.submit()

		work_order.reload()
		self.assertEqual(work_order.material_transferred_for_manufacturing, 0.0)
		self.assertEqual(work_order.status, "In Process")

	def test_backflushed_batch_raw_materials_based_on_transferred(self):
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		batch_item = "Test Batch MCC Keyboard"
		fg_item = "Test FG Item with Batch Raw Materials"

		ste_doc = test_stock_entry.make_stock_entry(
			item_code=batch_item, target="Stores - _TC", qty=4, basic_rate=100, do_not_save=True
		)

		# Inward raw materials in Stores warehouse
		ste_doc.insert()
		ste_doc.submit()
		ste_doc.load_from_db()

		batch_no = get_batch_from_bundle(ste_doc.items[0].serial_and_batch_bundle)

		wo_doc = make_wo_order_test_record(production_item=fg_item, qty=4)
		transferred_ste_doc = frappe.get_doc(
			make_stock_entry(wo_doc.name, "Material Transfer for Manufacture", 4)
		)

		transferred_ste_doc.items[0].qty = 4
		transferred_ste_doc.items[0].serial_and_batch_bundle = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": batch_item,
					"warehouse": "Stores - _TC",
					"company": transferred_ste_doc.company,
					"qty": 4,
					"voucher_type": "Stock Entry",
					"batches": frappe._dict({batch_no: 4}),
					"posting_date": transferred_ste_doc.posting_date,
					"posting_time": transferred_ste_doc.posting_time,
					"type_of_transaction": "Outward",
					"do_not_submit": True,
				}
			)
		).name

		transferred_ste_doc.submit()
		transferred_ste_doc.load_from_db()

		# First Manufacture stock entry
		manufacture_ste_doc1 = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 1))
		manufacture_ste_doc1.submit()
		manufacture_ste_doc1.load_from_db()

		# Batch no should be same as transferred Batch no
		self.assertEqual(
			get_batch_from_bundle(manufacture_ste_doc1.items[0].serial_and_batch_bundle), batch_no
		)
		self.assertEqual(manufacture_ste_doc1.items[0].qty, 1)

		# Second Manufacture stock entry
		manufacture_ste_doc2 = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 2))
		manufacture_ste_doc2.submit()
		manufacture_ste_doc2.load_from_db()

		self.assertTrue(manufacture_ste_doc2.items[0].serial_and_batch_bundle)
		bundle_doc = frappe.get_doc(
			"Serial and Batch Bundle", manufacture_ste_doc2.items[0].serial_and_batch_bundle
		)

		for d in bundle_doc.entries:
			self.assertEqual(d.batch_no, batch_no)
			self.assertEqual(abs(d.qty), 2)

	def test_backflushed_serial_no_raw_materials_based_on_transferred(self):
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		sn_item = "Test Serial No BTT Headphone"
		fg_item = "Test FG Item with Serial No Raw Materials"

		ste_doc = test_stock_entry.make_stock_entry(
			item_code=sn_item, target="Stores - _TC", qty=4, basic_rate=100, do_not_save=True
		)

		# Inward raw materials in Stores warehouse
		ste_doc.submit()
		ste_doc.reload()

		serial_nos_list = sorted(get_serial_nos_from_bundle(ste_doc.items[0].serial_and_batch_bundle))

		wo_doc = make_wo_order_test_record(production_item=fg_item, qty=4)
		transferred_ste_doc = frappe.get_doc(
			make_stock_entry(wo_doc.name, "Material Transfer for Manufacture", 4)
		)

		transferred_ste_doc.items[0].serial_no = "\n".join(serial_nos_list)
		transferred_ste_doc.submit()

		# First Manufacture stock entry
		manufacture_ste_doc1 = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 1))
		manufacture_ste_doc1.submit()
		manufacture_ste_doc1.reload()

		# Serial nos should be same as transferred Serial nos
		self.assertEqual(
			sorted(get_serial_nos_from_bundle(manufacture_ste_doc1.items[0].serial_and_batch_bundle)),
			serial_nos_list[0:1],
		)
		self.assertEqual(manufacture_ste_doc1.items[0].qty, 1)

		# Second Manufacture stock entry
		manufacture_ste_doc2 = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 3))

		# Serial nos should be same as transferred Serial nos
		self.assertEqual(get_serial_nos(manufacture_ste_doc2.items[0].serial_no), serial_nos_list[1:4])
		self.assertEqual(manufacture_ste_doc2.items[0].qty, 3)

	def test_backflushed_serial_no_batch_raw_materials_based_on_transferred(self):
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		sn_batch_item = "Test Batch Serial No WebCam"
		fg_item = "Test FG Item with Serial & Batch No Raw Materials"

		ste_doc = test_stock_entry.make_stock_entry(
			item_code=sn_batch_item, target="Stores - _TC", qty=4, basic_rate=100, do_not_save=True
		)

		# Inward raw materials in Stores warehouse
		ste_doc.insert()
		ste_doc.submit()
		ste_doc.load_from_db()

		serial_nos = []
		for row in ste_doc.items:
			bundle_doc = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)

			for d in bundle_doc.entries:
				serial_nos.append(d.serial_no)

		wo_doc = make_wo_order_test_record(production_item=fg_item, qty=4)
		transferred_ste_doc = frappe.get_doc(
			make_stock_entry(wo_doc.name, "Material Transfer for Manufacture", 4)
		)

		transferred_ste_doc.items[0].qty = 4
		transferred_ste_doc.items[0].serial_and_batch_bundle = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": transferred_ste_doc.get("items")[0].item_code,
					"warehouse": transferred_ste_doc.get("items")[0].s_warehouse,
					"company": transferred_ste_doc.company,
					"qty": 4,
					"type_of_transaction": "Outward",
					"voucher_type": "Stock Entry",
					"serial_nos": serial_nos,
					"posting_date": transferred_ste_doc.posting_date,
					"posting_time": transferred_ste_doc.posting_time,
					"do_not_submit": True,
				}
			)
		).name

		transferred_ste_doc.submit()
		transferred_ste_doc.load_from_db()

		# First Manufacture stock entry
		manufacture_ste_doc1 = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 1))
		manufacture_ste_doc1.submit()
		manufacture_ste_doc1.load_from_db()

		# Batch no & Serial Nos should be same as transferred Batch no & Serial Nos
		bundle = manufacture_ste_doc1.items[0].serial_and_batch_bundle
		self.assertTrue(bundle)

		bundle_doc = frappe.get_doc("Serial and Batch Bundle", bundle)
		for d in bundle_doc.entries:
			self.assertTrue(d.serial_no)
			self.assertTrue(d.batch_no)
			batch_no = frappe.get_cached_value("Serial No", d.serial_no, "batch_no")
			self.assertEqual(d.batch_no, batch_no)
			serial_nos.remove(d.serial_no)

		# Second Manufacture stock entry
		manufacture_ste_doc2 = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 3))
		manufacture_ste_doc2.submit()
		manufacture_ste_doc2.load_from_db()

		bundle = manufacture_ste_doc2.items[0].serial_and_batch_bundle
		self.assertTrue(bundle)

		bundle_doc = frappe.get_doc("Serial and Batch Bundle", bundle)
		for d in bundle_doc.entries:
			self.assertTrue(d.serial_no)
			self.assertTrue(d.batch_no)
			serial_nos.remove(d.serial_no)

		self.assertFalse(serial_nos)

	def test_backflushed_batch_raw_materials_based_on_transferred_autosabb(self):
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		batch_item = "Test Batch MCC Keyboard"
		fg_item = "Test FG Item with Batch Raw Materials"

		ste_doc = test_stock_entry.make_stock_entry(
			item_code=batch_item, target="Stores - _TC", qty=8, basic_rate=100, do_not_save=True
		)

		# Inward raw materials in Stores warehouse
		ste_doc.submit()
		ste_doc.reload()

		batch_no = get_batch_from_bundle(ste_doc.items[0].serial_and_batch_bundle)

		wo_doc = make_wo_order_test_record(production_item=fg_item, qty=4)
		# action taken upon Start button:
		transferred_ste_doc = frappe.get_doc(
			make_stock_entry(wo_doc.name, "Material Transfer for Manufacture", 4)
		)

		transferred_ste_doc.submit()
		transferred_ste_doc.reload()

		self.assertTrue(transferred_ste_doc.items[0].serial_and_batch_bundle)
		self.assertEqual(
			get_batch_from_bundle(transferred_ste_doc.items[0].serial_and_batch_bundle), batch_no
		)
		self.assertEqual(transferred_ste_doc.items[0].qty, 4.0)

		# Make additional consumption and link to WO
		test_stock_entry.make_stock_entry(
			item_code="Test Batch Battery Consumable",
			target="Stores - _TC",
			qty=8,
			basic_rate=2.33,
		)
		consume_use_doc = test_stock_entry.make_stock_entry(
			item_code="Test Batch Battery Consumable",  # consumable not linked to BOM
			source="Stores - _TC",
			qty=4,
			purpose="Material Consumption for Manufacture",
			do_not_save=True,
		)
		consume_use_doc.work_order = wo_doc.name
		consume_use_doc.fg_completed_qty = 4
		consume_use_doc.submit()
		consume_use_doc.reload()

		manufacture_ste_doc = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 4))
		mfr_items = [i.as_dict() for i in manufacture_ste_doc.items]
		manufacture_ste_doc.submit()
		manufacture_ste_doc.reload()

		self.assertTrue(len(mfr_items), 2)
		self.assertTrue(manufacture_ste_doc.items[0].serial_and_batch_bundle)
		self.assertEqual(
			get_batch_from_bundle(manufacture_ste_doc.items[0].serial_and_batch_bundle), batch_no
		)
		self.assertEqual(manufacture_ste_doc.items[0].qty, 4.0)

	def test_backflushed_serial_no_raw_materials_based_on_transferred_autosabb(self):
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		sn_item = "Test Serial No BTT Headphone"
		fg_item = "Test FG Item with Serial No Raw Materials"

		ste_doc = test_stock_entry.make_stock_entry(
			item_code=sn_item, target="Stores - _TC", qty=4, basic_rate=100, do_not_save=True
		)

		# Inward raw materials in Stores warehouse
		ste_doc.submit()
		ste_doc.reload()

		serial_nos_list = sorted(get_serial_nos_from_bundle(ste_doc.items[0].serial_and_batch_bundle))

		wo_doc = make_wo_order_test_record(production_item=fg_item, qty=4)
		transferred_ste_doc = frappe.get_doc(
			make_stock_entry(wo_doc.name, "Material Transfer for Manufacture", 4)
		)

		transferred_ste_doc.submit()
		transferred_ste_doc.reload()

		self.assertTrue(transferred_ste_doc.items[0].serial_and_batch_bundle)
		self.assertEqual(
			sorted(get_serial_nos_from_bundle(transferred_ste_doc.items[0].serial_and_batch_bundle)),
			serial_nos_list,
		)
		self.assertEqual(transferred_ste_doc.items[0].qty, 4.0)

		# Make additional consumption and link to WO
		test_stock_entry.make_stock_entry(
			item_code="Test Serial Battery Consumable",
			target="Stores - _TC",
			qty=8,
			basic_rate=3.33,
		)
		consume_use_doc = test_stock_entry.make_stock_entry(
			item_code="Test Serial Battery Consumable",  # consumable not linked to BOM
			source="Stores - _TC",
			qty=4,
			purpose="Material Consumption for Manufacture",
			do_not_save=True,
		)
		consume_use_doc.work_order = wo_doc.name
		consume_use_doc.fg_completed_qty = 4
		consume_use_doc.submit()
		consume_use_doc.reload()

		manufacture_ste_doc = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 4))
		mfr_items = [i.as_dict() for i in manufacture_ste_doc.items]
		manufacture_ste_doc.submit()
		manufacture_ste_doc.reload()

		self.assertTrue(len(mfr_items), 2)
		self.assertTrue(manufacture_ste_doc.items[0].serial_and_batch_bundle)
		self.assertEqual(
			sorted(get_serial_nos_from_bundle(manufacture_ste_doc.items[0].serial_and_batch_bundle)),
			serial_nos_list,
		)
		self.assertEqual(manufacture_ste_doc.items[0].qty, 4.0)

	def test_backflushed_serial_no_batch_raw_materials_based_on_transferred_autosabb(self):
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		sn_batch_item = "Test Batch Serial No WebCam"
		fg_item = "Test FG Item with Serial & Batch No Raw Materials"

		ste_doc = test_stock_entry.make_stock_entry(
			item_code=sn_batch_item, target="Stores - _TC", qty=4, basic_rate=100, do_not_save=True
		)

		ste_doc.submit()
		ste_doc.reload()

		serial_nos_list = sorted(get_serial_nos_from_bundle(ste_doc.items[0].serial_and_batch_bundle))
		batch_no = get_batch_from_bundle(ste_doc.items[0].serial_and_batch_bundle)

		wo_doc = make_wo_order_test_record(production_item=fg_item, qty=4)
		transferred_ste_doc = frappe.get_doc(
			make_stock_entry(wo_doc.name, "Material Transfer for Manufacture", 4)
		)

		transferred_ste_doc.submit()
		transferred_ste_doc.reload()

		self.assertTrue(transferred_ste_doc.items[0].serial_and_batch_bundle)
		self.assertEqual(
			sorted(get_serial_nos_from_bundle(transferred_ste_doc.items[0].serial_and_batch_bundle)),
			serial_nos_list,
		)
		self.assertEqual(
			get_batch_from_bundle(transferred_ste_doc.items[0].serial_and_batch_bundle), batch_no
		)
		self.assertEqual(transferred_ste_doc.items[0].qty, 4.0)

		manufacture_ste_doc = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 4))
		manufacture_ste_doc.submit()
		manufacture_ste_doc.reload()

		self.assertTrue(manufacture_ste_doc.items[0].serial_and_batch_bundle)
		self.assertEqual(
			sorted(get_serial_nos_from_bundle(manufacture_ste_doc.items[0].serial_and_batch_bundle)),
			serial_nos_list,
		)
		self.assertEqual(
			get_batch_from_bundle(manufacture_ste_doc.items[0].serial_and_batch_bundle), batch_no
		)
		self.assertEqual(manufacture_ste_doc.items[0].qty, 4.0)

		bundle = manufacture_ste_doc.items[0].serial_and_batch_bundle
		bundle_doc = frappe.get_doc("Serial and Batch Bundle", bundle)
		qty = sum(e.qty for e in bundle_doc.entries)
		self.assertEqual(qty, -4.0)

	###
	def test_non_consumed_material_return_against_work_order(self):
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		item = make_item(
			"Test FG Item To Test Return Case",
			{
				"is_stock_item": 1,
			},
		)

		item_code = item.name
		bom_doc = make_bom(
			item=item_code,
			source_warehouse="Stores - _TC",
			raw_materials=["Test Batch MCC Keyboard", "Test Serial No BTT Headphone"],
		)

		# Create a work order
		wo_doc = make_wo_order_test_record(production_item=item_code, qty=5)
		wo_doc.save()

		self.assertEqual(wo_doc.bom_no, bom_doc.name)

		# Transfer material for manufacture
		ste_doc = frappe.get_doc(make_stock_entry(wo_doc.name, "Material Transfer for Manufacture", 5))
		for row in ste_doc.items:
			row.qty += 2
			row.transfer_qty += 2
			test_stock_entry.make_stock_entry(
				item_code=row.item_code, target="Stores - _TC", qty=row.qty, basic_rate=100
			)

		ste_doc.save()
		ste_doc.submit()
		ste_doc.load_from_db()

		# Create a stock entry to manufacture the item
		ste_doc = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 5))
		for row in ste_doc.items:
			if row.s_warehouse and not row.t_warehouse:
				row.qty -= 2
				row.transfer_qty -= 2

			if row.serial_no:
				serial_nos = get_serial_nos(row.serial_no)
				row.serial_no = "\n".join(serial_nos[:5])

		ste_doc.save()
		ste_doc.submit()

		wo_doc.load_from_db()
		for row in wo_doc.required_items:
			self.assertEqual(row.transferred_qty, 7)
			self.assertEqual(row.consumed_qty, 5)

		self.assertEqual(wo_doc.status, "Completed")
		return_ste_doc = make_stock_return_entry(wo_doc.name)
		return_ste_doc.save()

		self.assertTrue(return_ste_doc.is_return)
		for row in return_ste_doc.items:
			self.assertEqual(row.qty, 2)

	def test_workstation_type_for_work_order(self):
		prepare_data_for_workstation_type_check()

		workstation_types = ["Workstation Type 1", "Workstation Type 2", "Workstation Type 3"]
		planned_start_date = "2022-11-14 10:00:00"

		wo_order = make_wo_order_test_record(
			item="Test FG Item For Workstation Type", planned_start_date=planned_start_date, qty=2
		)

		job_cards = frappe.get_all(
			"Job Card",
			fields=[
				"`tabJob Card`.`name`",
				"`tabJob Card`.`workstation_type`",
				"`tabJob Card`.`workstation`",
				"`tabJob Card Time Log`.`from_time`",
				"`tabJob Card Time Log`.`to_time`",
				"`tabJob Card Time Log`.`time_in_mins`",
			],
			filters=[
				["Job Card", "work_order", "=", wo_order.name],
				["Job Card Time Log", "docstatus", "=", 1],
			],
			order_by="`tabJob Card`.`creation` desc",
		)

		workstations_to_check = ["Workstation 1", "Workstation 3", "Workstation 5"]
		for index, row in enumerate(job_cards):
			if index != 0:
				planned_start_date = add_to_date(planned_start_date, minutes=40)

			self.assertEqual(row.workstation_type, workstation_types[index])
			self.assertEqual(row.from_time, planned_start_date)
			self.assertEqual(row.to_time, add_to_date(planned_start_date, minutes=30))
			self.assertEqual(row.workstation, workstations_to_check[index])

		planned_start_date = "2022-11-14 10:00:00"

		wo_order = make_wo_order_test_record(
			item="Test FG Item For Workstation Type", planned_start_date=planned_start_date, qty=2
		)

		job_cards = frappe.get_all(
			"Job Card",
			fields=[
				"`tabJob Card`.`name`",
				"`tabJob Card`.`workstation_type`",
				"`tabJob Card`.`workstation`",
				"`tabJob Card Time Log`.`from_time`",
				"`tabJob Card Time Log`.`to_time`",
				"`tabJob Card Time Log`.`time_in_mins`",
			],
			filters=[
				["Job Card", "work_order", "=", wo_order.name],
				["Job Card Time Log", "docstatus", "=", 1],
			],
			order_by="`tabJob Card`.`creation` desc",
		)

		workstations_to_check = ["Workstation 2", "Workstation 4", "Workstation 6"]
		for index, row in enumerate(job_cards):
			if index != 0:
				planned_start_date = add_to_date(planned_start_date, minutes=40)

			self.assertEqual(row.workstation_type, workstation_types[index])
			self.assertEqual(row.from_time, planned_start_date)
			self.assertEqual(row.to_time, add_to_date(planned_start_date, minutes=30))
			self.assertEqual(row.workstation, workstations_to_check[index])

	def test_job_card_extra_qty(self):
		items = [
			"Test FG Item for Scrap Item Test 1",
			"Test RM Item 1 for Scrap Item Test 1",
			"Test RM Item 2 for Scrap Item Test 1",
		]

		company = "_Test Company with perpetual inventory"
		for item_code in items:
			create_item(
				item_code=item_code,
				is_stock_item=1,
				is_purchase_item=1,
				opening_stock=100,
				valuation_rate=10,
				company=company,
				warehouse="Stores - TCP1",
			)

		item = "Test FG Item for Scrap Item Test 1"
		raw_materials = ["Test RM Item 1 for Scrap Item Test 1", "Test RM Item 2 for Scrap Item Test 1"]
		if not frappe.db.get_value("BOM", {"item": item}):
			bom = make_bom(
				item=item, source_warehouse="Stores - TCP1", raw_materials=raw_materials, do_not_save=True
			)
			bom.with_operations = 1
			bom.append(
				"operations",
				{
					"operation": "_Test Operation 1",
					"workstation": "_Test Workstation 1",
					"hour_rate": 20,
					"time_in_mins": 60,
				},
			)

			bom.submit()

		wo_order = make_wo_order_test_record(
			item=item,
			company=company,
			planned_start_date=now(),
			qty=20,
		)
		job_card = frappe.db.get_value("Job Card", {"work_order": wo_order.name}, "name")
		job_card_doc = frappe.get_doc("Job Card", job_card)
		for row in job_card_doc.scheduled_time_logs:
			job_card_doc.append(
				"time_logs",
				{
					"from_time": row.from_time,
					"to_time": row.to_time,
					"time_in_mins": row.time_in_mins,
					"completed_qty": 20,
				},
			)

		job_card_doc.save()

		# Make another Job Card for the same Work Order
		job_card2 = frappe.copy_doc(job_card_doc)
		job_card2.append(
			"time_logs",
			{
				"from_time": row.from_time,
				"to_time": row.to_time,
				"time_in_mins": row.time_in_mins,
			},
		)

		job_card2.time_logs[0].completed_qty = 20

		self.assertRaises(frappe.ValidationError, job_card2.save)

		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 100)

		job_card2 = frappe.copy_doc(job_card_doc)
		job_card2.time_logs = []
		job_card2.save()

	def test_operating_cost_account(self):
		operating_cost_account = "Test Operating Cost Account - _TC"
		company = "_Test Company"
		if not frappe.db.exists("Account", operating_cost_account):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Test Operating Cost Account",
					"account_type": "Expense Account",
					"company": company,
					"parent_account": "Expenses - _TC",
					"root_type": "Expense",
				}
			).insert()

		frappe.db.set_value("Company", company, "default_operating_cost_account", operating_cost_account)

		for item in ["TEST RM OP COST Item 1", "TEST FG OP COST Item"]:
			if not frappe.db.exists("Item", item):
				make_item(item_code=item, properties={"is_stock_item": 1})

		fg_item = "TEST FG OP COST Item"
		bom_doc = make_bom(
			item=fg_item,
			raw_materials=["TEST RM OP COST Item 1"],
			rate=150,
			with_operations=1,
			do_not_save=True,
		)

		workstation = "Test Workstation For Capacity Planning 1"
		if not frappe.db.exists("Workstation", workstation):
			make_workstation(workstation=workstation, production_capacity=1)

		operation = "Test Operation For Capacity Planning 1"
		if not frappe.db.exists("Operation", operation):
			make_operation(operation=operation, workstation=workstation)

		bom_doc.append(
			"operations",
			{"operation": operation, "time_in_mins": 60, "hour_rate": 100, "workstation": workstation},
		)

		bom_doc.save()
		bom_doc.submit()

		wo = make_wo_order_test_record(
			production_item=fg_item,
			bom_no=bom_doc.name,
			qty=1,
			skip_transfer=1,
			from_wip_warehouse=1,
			source_warehouse="_Test Warehouse - _TC",
		)

		job_cards = frappe.get_all("Job Card", filters={"work_order": wo.name})
		for job_card in job_cards:
			job_card_doc = frappe.get_doc("Job Card", job_card.name)
			job_card_doc.time_logs = []
			job_card_doc.append(
				"time_logs",
				{
					"from_time": now(),
					"to_time": add_to_date(now(), minutes=60),
					"time_in_mins": 60,
					"completed_qty": 1,
				},
			)

			job_card_doc.submit()

		se_doc = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
		se_doc.save()

		for row in se_doc.additional_costs:
			self.assertEqual(row.expense_account, operating_cost_account)

	def test_op_cost_and_scrap_based_on_sub_assemblies(self):
		# Make Sub Assembly BOM 1

		frappe.db.set_single_value("Manufacturing Settings", "set_op_cost_and_scrap_from_sub_assemblies", 1)

		items = {
			"Test Final FG Item": 0,
			"Test Final SF Item 1": 0,
			"Test Final SF Item 2": 0,
			"Test Final RM Item 1": 100,
			"Test Final RM Item 2": 200,
			"Test Final Scrap Item 1": 50,
			"Test Final Scrap Item 2": 60,
		}

		for item in items:
			if not frappe.db.exists("Item", item):
				item_properties = {"is_stock_item": 1, "valuation_rate": items[item]}

				(make_item(item_code=item, properties=item_properties),)

		prepare_boms_for_sub_assembly_test()

		wo_order = make_wo_order_test_record(
			production_item="Test Final FG Item",
			qty=10,
			use_multi_level_bom=1,
			skip_transfer=1,
			from_wip_warehouse=1,
		)

		se_doc = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
		se_doc.save()

		self.assertTrue(se_doc.additional_costs)
		scrap_items = []
		for item in se_doc.items:
			if item.is_scrap_item:
				scrap_items.append(item.item_code)

		self.assertEqual(sorted(scrap_items), sorted(["Test Final Scrap Item 1", "Test Final Scrap Item 2"]))
		for row in se_doc.additional_costs:
			self.assertEqual(row.amount, 3000)

		frappe.db.set_single_value("Manufacturing Settings", "set_op_cost_and_scrap_from_sub_assemblies", 0)

	@change_settings(
		"Manufacturing Settings", {"material_consumption": 1, "get_rm_cost_from_consumption_entry": 1}
	)
	def test_get_rm_cost_from_consumption_entry(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		rm = make_item(properties={"is_stock_item": 1}).name
		fg = make_item(properties={"is_stock_item": 1}).name

		make_stock_entry_test_record(
			purpose="Material Receipt",
			item_code=rm,
			target="Stores - _TC",
			qty=10,
			basic_rate=100,
		)
		make_stock_entry_test_record(
			purpose="Material Receipt",
			item_code=rm,
			target="Stores - _TC",
			qty=10,
			basic_rate=200,
		)

		bom = make_bom(item=fg, raw_materials=[rm], rate=150).name
		wo = make_wo_order_test_record(
			production_item=fg,
			bom_no=bom,
			qty=10,
		)

		mte = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
		mte.items[0].s_warehouse = "Stores - _TC"
		mte.insert().submit()

		mce = frappe.get_doc(make_stock_entry(wo.name, "Material Consumption for Manufacture", 10))
		mce.insert().submit()

		me = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		me.insert().submit()

		valuation_rate = sum([item.valuation_rate * item.transfer_qty for item in mce.items]) / 10
		self.assertEqual(me.items[0].valuation_rate, valuation_rate)

	def test_capcity_planning_for_workstation(self):
		frappe.db.set_single_value(
			"Manufacturing Settings",
			{
				"disable_capacity_planning": 0,
				"capacity_planning_for_days": 1,
				"mins_between_operations": 10,
			},
		)

		properties = {"is_stock_item": 1, "valuation_rate": 100}
		fg_item = make_item("Test FG Item For Capacity Planning", properties).name

		rm_item = make_item("Test RM Item For Capacity Planning", properties).name

		workstation = "Test Workstation For Capacity Planning"
		if not frappe.db.exists("Workstation", workstation):
			make_workstation(workstation=workstation, production_capacity=1)

		operation = "Test Operation For Capacity Planning"
		if not frappe.db.exists("Operation", operation):
			make_operation(operation=operation, workstation=workstation)

		bom_doc = make_bom(
			item=fg_item,
			source_warehouse="Stores - _TC",
			raw_materials=[rm_item],
			with_operations=1,
			do_not_submit=True,
		)

		bom_doc.append(
			"operations",
			{"operation": operation, "time_in_mins": 1420, "hour_rate": 100, "workstation": workstation},
		)
		bom_doc.submit()

		# 1st Work Order,
		# Capacity to run parallel the operation 'Test Operation For Capacity Planning' is 2
		wo_doc = make_wo_order_test_record(
			production_item=fg_item, qty=1, planned_start_date="2024-02-25 00:00:00", do_not_submit=1
		)

		wo_doc.submit()
		job_cards = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name},
		)

		self.assertEqual(len(job_cards), 1)

		# 2nd Work Order,
		wo_doc = make_wo_order_test_record(
			production_item=fg_item, qty=1, planned_start_date="2024-02-25 00:00:00", do_not_submit=1
		)

		wo_doc.submit()
		job_cards = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name},
		)

		self.assertEqual(len(job_cards), 1)

		# 3rd Work Order, capacity is full
		wo_doc = make_wo_order_test_record(
			production_item=fg_item, qty=1, planned_start_date="2024-02-25 00:00:00", do_not_submit=1
		)

		self.assertRaises(CapacityError, wo_doc.submit)

		frappe.db.set_single_value(
			"Manufacturing Settings", {"disable_capacity_planning": 1, "mins_between_operations": 0}
		)

	def test_partial_material_consumption_with_batch(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		frappe.db.set_single_value("Manufacturing Settings", "material_consumption", 1)
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		fg_item = make_item(
			"Test FG Item For Partial Material Consumption",
			{"is_stock_item": 1},
		).name

		rm_item = make_item(
			"Test RM Item For Partial Material Consumption",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TST-BATCH-PMCC-.####",
			},
		).name

		make_bom(
			item=fg_item,
			source_warehouse="Stores - _TC",
			raw_materials=[rm_item],
		)

		make_stock_entry_test_record(
			purpose="Material Receipt",
			item_code=rm_item,
			target="Stores - _TC",
			qty=10,
			basic_rate=100,
		)

		wo_order = make_wo_order_test_record(item=fg_item, qty=10)

		stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 10))
		stock_entry.submit()
		stock_entry.reload()

		batch_no = get_batch_from_bundle(stock_entry.items[0].serial_and_batch_bundle)

		stock_entry = frappe.get_doc(
			make_stock_entry(wo_order.name, "Material Consumption for Manufacture", 10)
		)

		self.assertEqual(stock_entry.items[0].batch_no, batch_no)
		self.assertEqual(stock_entry.items[0].use_serial_batch_fields, 1)

		frappe.db.set_single_value("Manufacturing Settings", "material_consumption", 0)
		frappe.db.set_single_value(
			"Manufacturing Settings",
			"backflush_raw_materials_based_on",
			"BOM",
		)

	def test_disassemby_order(self):
		fg_item = "Test Disassembly Item"
		source_warehouse = "Stores - _TC"
		raw_materials = ["Test Disassembly RM Item 1", "Test Disassembly RM Item 2"]

		make_item(fg_item, {"is_stock_item": 1})
		for item in raw_materials:
			make_item(item, {"is_stock_item": 1})
			test_stock_entry.make_stock_entry(
				item_code=item,
				target=source_warehouse,
				qty=1,
				basic_rate=100,
			)

		make_bom(item=fg_item, source_warehouse=source_warehouse, raw_materials=raw_materials)

		wo = make_wo_order_test_record(
			item=fg_item,
			qty=1,
			source_warehouse=source_warehouse,
			skip_transfer=1,
		)

		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
		for row in stock_entry.items:
			if row.item_code in raw_materials:
				row.s_warehouse = source_warehouse

		stock_entry.submit()

		wo.reload()
		self.assertEqual(wo.status, "Completed")

		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Disassemble", 1))
		stock_entry.save()

		self.assertEqual(stock_entry.purpose, "Disassemble")

		for row in stock_entry.items:
			if row.item_code == fg_item:
				self.assertTrue(row.s_warehouse)
				self.assertFalse(row.t_warehouse)
			else:
				self.assertFalse(row.s_warehouse)
				self.assertTrue(row.t_warehouse)

		stock_entry.submit()

	def test_disassembly_order_with_qty_from_wo_behavior(self):
		# Create raw material and FG item
		raw_item = make_item("Test Raw for Disassembly", {"is_stock_item": 1}).name
		fg_item = make_item("Test FG for Disassembly", {"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, quantity=10, raw_materials=[raw_item], rm_qty=5)

		# Create and submit a Work Order for 10 qty
		wo = make_wo_order_test_record(production_item=fg_item, qty=10, bom_no=bom.name, status="Not Started")

		# create material receipt stock entry for raw material
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		make_stock_entry_test_record(
			item_code=raw_item,
			purpose="Material Receipt",
			target=wo.wip_warehouse,
			qty=10,
			basic_rate=100,
		)
		make_stock_entry_test_record(
			item_code=raw_item,
			purpose="Material Receipt",
			target=wo.fg_warehouse,
			qty=10,
			basic_rate=100,
		)

		# create material transfer for manufacture stock entry
		se_for_material_tranfer_mfr = frappe.get_doc(
			make_stock_entry(wo.name, "Material Transfer for Manufacture", wo.qty)
		)
		se_for_material_tranfer_mfr.items[0].s_warehouse = wo.wip_warehouse
		se_for_material_tranfer_mfr.save()
		se_for_material_tranfer_mfr.submit()

		se_for_manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", wo.qty))
		se_for_manufacture.submit()

		# Disassembly via WO required_items path (no source_stock_entry)
		disassemble_qty = 4
		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Disassemble", disassemble_qty))

		wo.reload()
		stock_entry.save()
		stock_entry.submit()

		# Assert FG item is present with correct qty
		finished_good_entry = next((item for item in stock_entry.items if item.item_code == fg_item), None)
		self.assertIsNotNone(finished_good_entry, "Finished good item missing from stock entry")
		self.assertEqual(
			finished_good_entry.qty,
			disassemble_qty,
			f"Expected FG qty {disassemble_qty}, found {finished_good_entry.qty}",
		)

		# Assert raw materials - qty scaled from WO required_items
		for item in stock_entry.items:
			if item.item_code == fg_item:
				continue
			bom_item = next((i for i in bom.items if i.item_code == item.item_code), None)
			if bom_item:
				expected_qty = (bom_item.qty / bom.quantity) * disassemble_qty
				self.assertAlmostEqual(
					item.qty,
					expected_qty,
					places=3,
					msg=f"Raw item {item.item_code} qty mismatch: expected {expected_qty}, got {item.qty}",
				)
			else:
				self.fail(f"Unexpected item {item.item_code} found in stock entry")

		wo.reload()
		# Assert disassembled_qty field updated in Work Order
		self.assertEqual(
			wo.disassembled_qty,
			disassemble_qty,
			f"Work Order disassembled_qty mismatch: expected {disassemble_qty}, got {wo.disassembled_qty}",
		)

		# Second disassembly: explicitly linked to manufacture SE — verifies SE-linked path
		# (first disassembly auto-set source_stock_entry since there's only one manufacture entry)
		disassemble_qty_2 = 2
		stock_entry_2 = frappe.get_doc(
			make_stock_entry(
				wo.name, "Disassemble", disassemble_qty_2, source_stock_entry=se_for_manufacture.name
			)
		)
		stock_entry_2.save()
		stock_entry_2.submit()

		# All rows must trace back to se_for_manufacture
		for item in stock_entry_2.items:
			self.assertEqual(item.against_stock_entry, se_for_manufacture.name)
			self.assertTrue(item.ste_detail)

		# RM qty scaled from the manufacture SE rows
		rm_row = next((i for i in stock_entry_2.items if i.item_code == raw_item), None)
		expected_rm_qty = (bom.items[0].qty / bom.quantity) * disassemble_qty_2
		self.assertAlmostEqual(rm_row.qty, expected_rm_qty, places=3)

		wo.reload()
		self.assertEqual(wo.disassembled_qty, disassemble_qty + disassemble_qty_2)

	def test_disassembly_with_multiple_manufacture_entries(self):
		"""
		Test that disassembly does not create duplicate items when manufacturing
		is done in multiple batches (multiple manufacture stock entries), including
		secondary/scrap items.

		Scenario:
		1. Create Work Order for 10 units
		2. Transfer raw materials
		3. Manufacture in 2 parts (3 units, then 7 units) - creates 2 stock entries
		4. Create Disassembly for 4 units
		5. Verify no duplicate items in the disassembly stock entry
		"""
		# Create RM, scrap and FG item
		raw_item1 = make_item("Test Raw for Multi Batch Disassembly 1", {"is_stock_item": 1}).name
		raw_item2 = make_item("Test Raw for Multi Batch Disassembly 2", {"is_stock_item": 1}).name
		scrap_item = make_item("Test Scrap for Multi Batch Disassembly", {"is_stock_item": 1}).name
		fg_item = make_item("Test FG for Multi Batch Disassembly", {"is_stock_item": 1}).name
		bom = make_bom(
			item=fg_item, quantity=1, raw_materials=[raw_item1, raw_item2], rm_qty=2, do_not_submit=True
		)
		# add scrap item
		bom.append("scrap_items", {"item_code": scrap_item, "stock_qty": 10})
		bom.submit()

		# Create WO
		wo = make_wo_order_test_record(production_item=fg_item, qty=10, bom_no=bom.name, status="Not Started")

		# Ensure enough stock
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		make_stock_entry_test_record(
			item_code=raw_item1,
			purpose="Material Receipt",
			target=wo.wip_warehouse,
			qty=50,
			basic_rate=100,
		)
		make_stock_entry_test_record(
			item_code=raw_item2,
			purpose="Material Receipt",
			target=wo.wip_warehouse,
			qty=50,
			basic_rate=100,
		)

		# Transfer for manufacture
		se_for_material_transfer = frappe.get_doc(
			make_stock_entry(wo.name, "Material Transfer for Manufacture", wo.qty)
		)
		for item in se_for_material_transfer.items:
			item.s_warehouse = wo.wip_warehouse
		se_for_material_transfer.save()
		se_for_material_transfer.submit()

		# First Manufacture Entry - 3 units
		se_manufacture1 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 3))
		se_manufacture1.submit()

		# Second Manufacture Entry - 7 units
		se_manufacture2 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 7))
		se_manufacture2.submit()

		wo.reload()
		self.assertEqual(wo.produced_qty, 10)

		# Count manufacture entries
		manufacture_entries = frappe.get_all(
			"Stock Entry",
			filters={
				"work_order": wo.name,
				"purpose": "Manufacture",
				"docstatus": 1,
			},
		)
		self.assertEqual(len(manufacture_entries), 2, "Expected 2 manufacture entries")

		# Disassembly for 4 units
		disassemble_qty = 4
		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Disassemble", disassemble_qty))
		stock_entry.save()
		stock_entry.submit()

		item_counts = {}
		for item in stock_entry.items:
			item_code = item.item_code
			item_counts[item_code] = item_counts.get(item_code, 0) + 1

		# No duplicates
		duplicates = {k: v for k, v in item_counts.items() if v > 1}
		self.assertEqual(
			len(duplicates),
			0,
			f"Found duplicate items in disassembly stock entry: {duplicates}",
		)

		expected_items = 4  # FG item + 2 raw materials + 1 scrap item
		self.assertEqual(
			len(stock_entry.items),
			expected_items,
			f"Expected {expected_items} items, found {len(stock_entry.items)}",
		)

		# FG item qty
		fg_item_row = next((i for i in stock_entry.items if i.item_code == fg_item), None)
		self.assertEqual(fg_item_row.qty, disassemble_qty)

		# Scrap item: should be taken from scrap warehouse in disassembly
		scrap_row = next((i for i in stock_entry.items if i.item_code == scrap_item), None)
		self.assertIsNotNone(scrap_row)
		self.assertEqual(scrap_row.is_scrap_item, 1)
		self.assertTrue(scrap_row.s_warehouse)
		self.assertFalse(scrap_row.t_warehouse)
		self.assertEqual(scrap_row.s_warehouse, wo.scrap_warehouse)
		# BOM has scrap_qty=10/FG, total produced = 10*10 = 100, disassemble 4/10 → 40
		self.assertEqual(scrap_row.qty, 40)

		# RM quantities
		for bom_item in bom.items:
			expected_qty = (bom_item.qty / bom.quantity) * disassemble_qty
			rm_row = next((i for i in stock_entry.items if i.item_code == bom_item.item_code), None)
			self.assertAlmostEqual(
				rm_row.qty,
				expected_qty,
				places=3,
				msg=f"Raw material {bom_item.item_code} qty mismatch",
			)

		# -- BOM-path disassembly (no source_stock_entry, no work_order) --

		make_stock_entry_test_record(
			item_code=scrap_item,
			purpose="Material Receipt",
			target=wo.fg_warehouse,
			qty=50,
			basic_rate=10,
		)

		bom_disassemble_qty = 2
		bom_se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Disassemble",
				"purpose": "Disassemble",
				"from_bom": 1,
				"bom_no": bom.name,
				"fg_completed_qty": bom_disassemble_qty,
				"from_warehouse": wo.fg_warehouse,
				"to_warehouse": wo.wip_warehouse,
				"company": wo.company,
				"posting_date": nowdate(),
				"posting_time": nowtime(),
			}
		)
		bom_se.get_items()
		bom_se.save()
		bom_se.submit()

		bom_scrap_row = next((i for i in bom_se.items if i.item_code == scrap_item), None)
		self.assertIsNotNone(bom_scrap_row, "Scrap item must appear in BOM-path disassembly")
		# v15: BOM scrap_qty=10/FG, no process_loss_per field → qty = 10 * 2 = 20
		self.assertEqual(
			bom_scrap_row.qty,
			20,
			f"BOM-path disassembly scrap qty mismatch; expected 20, got {bom_scrap_row.qty}",
		)

	def test_disassembly_with_additional_rm_not_in_bom(self):
		"""
		Test that SE-linked disassembly includes additional raw materials
		that were manually added during manufacturing (not part of the BOM).

		Scenario:
		1. Create Work Order for 10 units with 2 raw materials in BOM
		2. Transfer raw materials for manufacture
		3. Manufacture in 2 parts (3 units, then 7 units)
		4. In each manufacture entry, manually add an extra consumable item
		5. Disassemble 3 units linked to first manufacture entry
		6. Verify additional RM is included with correct proportional qty from SE1
		"""
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		# Create RM and FG item
		raw_item1 = make_item("Test BOM Raw 1 for Additional RM Disassembly", {"is_stock_item": 1}).name
		raw_item2 = make_item("Test BOM Raw 2 for Additional RM Disassembly", {"is_stock_item": 1}).name
		additional_rm = make_item("Test Additional RM for Disassembly", {"is_stock_item": 1}).name
		fg_item = make_item("Test FG for Additional RM Disassembly", {"is_stock_item": 1}).name

		bom = make_bom(item=fg_item, quantity=1, raw_materials=[raw_item1, raw_item2], rm_qty=2)

		# Create WO
		wo = make_wo_order_test_record(production_item=fg_item, qty=10, bom_no=bom.name, status="Not Started")

		# Ensure enough stock
		for item in [raw_item1, raw_item2, additional_rm]:
			make_stock_entry_test_record(
				item_code=item,
				purpose="Material Receipt",
				target=wo.wip_warehouse,
				qty=100,
				basic_rate=100,
			)

		# Transfer for manufacture
		se_for_material_transfer = frappe.get_doc(
			make_stock_entry(wo.name, "Material Transfer for Manufacture", wo.qty)
		)
		for item in se_for_material_transfer.items:
			item.s_warehouse = wo.wip_warehouse
		se_for_material_transfer.save()
		se_for_material_transfer.submit()

		# First Manufacture Entry - 3 units with additional RM
		se_manufacture1 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 3))
		se_manufacture1.append(
			"items",
			{
				"item_code": additional_rm,
				"qty": 3,  # 1 per unit
				"s_warehouse": wo.wip_warehouse,
				"is_finished_item": 0,
			},
		)
		se_manufacture1.save()
		se_manufacture1.submit()

		# Second Manufacture Entry - 7 units with additional RM
		se_manufacture2 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 7))
		se_manufacture2.append(
			"items",
			{
				"item_code": additional_rm,
				"qty": 7,  # 1 per unit
				"s_warehouse": wo.wip_warehouse,
				"is_finished_item": 0,
			},
		)
		se_manufacture2.save()
		se_manufacture2.submit()

		wo.reload()
		self.assertEqual(wo.produced_qty, 10)

		# Disassemble 3 units linked to first manufacture entry
		disassemble_qty = 3
		stock_entry = frappe.get_doc(
			make_stock_entry(wo.name, "Disassemble", disassemble_qty, source_stock_entry=se_manufacture1.name)
		)
		stock_entry.save()
		stock_entry.submit()

		# No duplicates
		item_counts = {}
		for item in stock_entry.items:
			item_code = item.item_code
			item_counts[item_code] = item_counts.get(item_code, 0) + 1

		duplicates = {k: v for k, v in item_counts.items() if v > 1}
		self.assertEqual(
			len(duplicates),
			0,
			f"Found duplicate items in disassembly stock entry: {duplicates}",
		)

		# Additional RM should be included — qty proportional to SE1 (3 units -> 3 additional RM)
		additional_rm_row = next((i for i in stock_entry.items if i.item_code == additional_rm), None)
		self.assertIsNotNone(
			additional_rm_row,
			f"Additional raw material {additional_rm} not found in disassembly",
		)

		# SE1 had 3 additional RM for 3 manufactured units, disassembling all 3
		expected_additional_rm_qty = 3
		self.assertAlmostEqual(
			additional_rm_row.qty,
			expected_additional_rm_qty,
			places=3,
			msg=f"Additional RM qty mismatch: expected {expected_additional_rm_qty}, got {additional_rm_row.qty}",
		)

		# BOM RM qty — scaled from SE1's rows
		for bom_item in bom.items:
			expected_qty = (bom_item.qty / bom.quantity) * disassemble_qty
			rm_row = next((i for i in stock_entry.items if i.item_code == bom_item.item_code), None)
			self.assertIsNotNone(rm_row, f"BOM raw material {bom_item.item_code} not found")
			self.assertAlmostEqual(
				rm_row.qty,
				expected_qty,
				places=3,
				msg=f"BOM raw material {bom_item.item_code} qty mismatch",
			)

		# FG qty
		fg_item_row = next((i for i in stock_entry.items if i.item_code == fg_item), None)
		self.assertEqual(fg_item_row.qty, disassemble_qty)

		# FG + 2 BOM RM + 1 additional RM = 4 items
		expected_items = 4
		self.assertEqual(
			len(stock_entry.items),
			expected_items,
			f"Expected {expected_items} items, found {len(stock_entry.items)}",
		)

		# Verify traceability
		for item in stock_entry.items:
			self.assertEqual(item.against_stock_entry, se_manufacture1.name)
			self.assertTrue(item.ste_detail)

	def test_disassembly_auto_sets_source_stock_entry(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		raw_item = make_item("Test Raw Auto Set Disassembly", {"is_stock_item": 1}).name
		fg_item = make_item("Test FG Auto Set Disassembly", {"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, quantity=1, raw_materials=[raw_item], rm_qty=2)

		wo = make_wo_order_test_record(production_item=fg_item, qty=5, bom_no=bom.name, status="Not Started")

		make_stock_entry_test_record(
			item_code=raw_item, purpose="Material Receipt", target=wo.wip_warehouse, qty=50, basic_rate=100
		)

		se_transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", wo.qty))
		for item in se_transfer.items:
			item.s_warehouse = wo.wip_warehouse
		se_transfer.save()
		se_transfer.submit()

		se_manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", wo.qty))
		se_manufacture.submit()

		# Disassemble without specifying source_stock_entry
		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Disassemble", 3))
		stock_entry.save()

		# source_stock_entry should be auto-set since only one manufacture entry
		self.assertEqual(stock_entry.source_stock_entry, se_manufacture.name)

		# All items should have against_stock_entry linked
		for item in stock_entry.items:
			self.assertEqual(item.against_stock_entry, se_manufacture.name)
			self.assertTrue(item.ste_detail)

		stock_entry.submit()

	def test_disassembly_batch_tracked_items(self):
		from erpnext.stock.doctype.batch.batch import make_batch
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		wip_wh = "_Test Warehouse - _TC"

		rm_item = make_item(
			"Test Batch RM for Disassembly SB",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBRD-RM-.###",
			},
		).name
		fg_item = make_item(
			"Test Batch FG for Disassembly SB",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBRD-FG-.###",
			},
		).name

		bom = make_bom(item=fg_item, quantity=1, raw_materials=[rm_item], rm_qty=2)
		wo = make_wo_order_test_record(
			production_item=fg_item,
			qty=6,
			bom_no=bom.name,
			skip_transfer=1,
			source_warehouse=wip_wh,
			status="Not Started",
		)

		# Two separate RM receipts → two distinct batches (batch_1, batch_2)
		rm_receipt_1 = make_stock_entry_test_record(
			item_code=rm_item, purpose="Material Receipt", target=wip_wh, qty=6, basic_rate=100
		)
		rm_batch_1 = get_batch_from_bundle(
			frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": rm_receipt_1.name, "item_code": rm_item},
				"serial_and_batch_bundle",
			)
		)

		rm_receipt_2 = make_stock_entry_test_record(
			item_code=rm_item, purpose="Material Receipt", target=wip_wh, qty=6, basic_rate=100
		)
		rm_batch_2 = get_batch_from_bundle(
			frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": rm_receipt_2.name, "item_code": rm_item},
				"serial_and_batch_bundle",
			)
		)

		self.assertNotEqual(rm_batch_1, rm_batch_2, "Two receipts must create two distinct RM batches")

		fg_batch_1 = make_batch(frappe._dict(item=fg_item))
		fg_batch_2 = make_batch(frappe._dict(item=fg_item))

		# Manufacture entry 1 — 3 FG using batch_1 RM/FG
		se_manufacture_1 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 3))
		for row in se_manufacture_1.items:
			if row.item_code == rm_item:
				row.batch_no = rm_batch_1
				row.use_serial_batch_fields = 1
			elif row.item_code == fg_item:
				row.batch_no = fg_batch_1
				row.use_serial_batch_fields = 1
		se_manufacture_1.save()
		se_manufacture_1.submit()

		# Manufacture entry 2 — 3 FG using batch_2 RM/FG
		se_manufacture_2 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 3))
		for row in se_manufacture_2.items:
			if row.item_code == rm_item:
				row.batch_no = rm_batch_2
				row.use_serial_batch_fields = 1
			elif row.item_code == fg_item:
				row.batch_no = fg_batch_2
				row.use_serial_batch_fields = 1
		se_manufacture_2.save()
		se_manufacture_2.submit()

		# Disassemble 2 units from SE_1 only — must use SE_1's batches, not SE_2's
		disassemble_qty = 2
		stock_entry = frappe.get_doc(
			make_stock_entry(
				wo.name, "Disassemble", disassemble_qty, source_stock_entry=se_manufacture_1.name
			)
		)
		stock_entry.save()
		stock_entry.submit()

		# FG row: must use fg_batch_1 exclusively (fg_batch_2 must not appear)
		fg_row = next((i for i in stock_entry.items if i.item_code == fg_item), None)
		self.assertIsNotNone(fg_row)
		self.assertTrue(fg_row.serial_and_batch_bundle, "FG row must have a serial_and_batch_bundle")
		self.assertEqual(get_batch_from_bundle(fg_row.serial_and_batch_bundle), fg_batch_1)
		self.assertNotEqual(get_batch_from_bundle(fg_row.serial_and_batch_bundle), fg_batch_2)

		# RM row: must use rm_batch_1 exclusively (rm_batch_2 must not appear)
		rm_row = next((i for i in stock_entry.items if i.item_code == rm_item), None)
		self.assertIsNotNone(rm_row)
		self.assertTrue(rm_row.serial_and_batch_bundle, "RM row must have a serial_and_batch_bundle")
		self.assertEqual(get_batch_from_bundle(rm_row.serial_and_batch_bundle), rm_batch_1)
		self.assertNotEqual(get_batch_from_bundle(rm_row.serial_and_batch_bundle), rm_batch_2)

		# RM qty: 2 FG disassembled x 2 RM per FG = 4
		self.assertAlmostEqual(rm_row.qty, 4.0, places=3)

	def test_disassembly_serial_tracked_items(self):
		from frappe.model.naming import make_autoname

		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		wip_wh = "_Test Warehouse - _TC"

		rm_item = make_item(
			"Test Serial RM for Disassembly SB",
			{"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "TSRD-RM-.####"},
		).name
		fg_item = make_item(
			"Test Serial FG for Disassembly SB",
			{"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "TSRD-FG-.####"},
		).name

		bom = make_bom(item=fg_item, quantity=1, raw_materials=[rm_item], rm_qty=2)
		wo = make_wo_order_test_record(
			production_item=fg_item,
			qty=6,
			bom_no=bom.name,
			skip_transfer=1,
			source_warehouse=wip_wh,
			status="Not Started",
		)

		# Two separate RM receipts → two disjoint sets of serial numbers
		rm_receipt_1 = make_stock_entry_test_record(
			item_code=rm_item, purpose="Material Receipt", target=wip_wh, qty=6, basic_rate=100
		)
		rm_serials_1 = get_serial_nos_from_bundle(
			frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": rm_receipt_1.name, "item_code": rm_item},
				"serial_and_batch_bundle",
			)
		)
		self.assertEqual(len(rm_serials_1), 6)

		rm_receipt_2 = make_stock_entry_test_record(
			item_code=rm_item, purpose="Material Receipt", target=wip_wh, qty=6, basic_rate=100
		)
		rm_serials_2 = get_serial_nos_from_bundle(
			frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": rm_receipt_2.name, "item_code": rm_item},
				"serial_and_batch_bundle",
			)
		)
		self.assertEqual(len(rm_serials_2), 6)
		self.assertFalse(
			set(rm_serials_1) & set(rm_serials_2), "Two receipts must produce disjoint RM serial sets"
		)

		# Pre-generate two sets of FG serial numbers
		series = frappe.db.get_value("Item", fg_item, "serial_no_series")
		fg_serials_1 = [make_autoname(series) for _ in range(3)]
		fg_serials_2 = [make_autoname(series) for _ in range(3)]

		# Manufacture entry 1 — consumes rm_serials_1, produces fg_serials_1
		se_manufacture_1 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 3))
		for row in se_manufacture_1.items:
			if row.item_code == rm_item:
				row.serial_no = "\n".join(rm_serials_1)
				row.use_serial_batch_fields = 1
			elif row.item_code == fg_item:
				row.serial_no = "\n".join(fg_serials_1)
				row.use_serial_batch_fields = 1
		se_manufacture_1.save()
		se_manufacture_1.submit()

		# Manufacture entry 2 — consumes rm_serials_2, produces fg_serials_2
		se_manufacture_2 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 3))
		for row in se_manufacture_2.items:
			if row.item_code == rm_item:
				row.serial_no = "\n".join(rm_serials_2)
				row.use_serial_batch_fields = 1
			elif row.item_code == fg_item:
				row.serial_no = "\n".join(fg_serials_2)
				row.use_serial_batch_fields = 1
		se_manufacture_2.save()
		se_manufacture_2.submit()

		# Disassemble 2 units from SE_1 only — must use SE_1's serials, not SE_2's
		disassemble_qty = 2
		stock_entry = frappe.get_doc(
			make_stock_entry(
				wo.name, "Disassemble", disassemble_qty, source_stock_entry=se_manufacture_1.name
			)
		)
		stock_entry.save()
		stock_entry.submit()

		# FG row: 2 serials consumed — must be subset of fg_serials_1, disjoint from fg_serials_2
		fg_row = next((i for i in stock_entry.items if i.item_code == fg_item), None)
		self.assertIsNotNone(fg_row)
		self.assertTrue(fg_row.serial_and_batch_bundle, "FG row must have a serial_and_batch_bundle")
		fg_dasm_serials = get_serial_nos_from_bundle(fg_row.serial_and_batch_bundle)
		self.assertEqual(len(fg_dasm_serials), disassemble_qty)
		self.assertTrue(set(fg_dasm_serials).issubset(set(fg_serials_1)))
		self.assertFalse(
			set(fg_dasm_serials) & set(fg_serials_2), "Disassembly must not use SE_2's FG serials"
		)

		# RM row: 4 serials returned (2 FG x 2 RM each) — subset of rm_serials_1, disjoint from rm_serials_2
		rm_row = next((i for i in stock_entry.items if i.item_code == rm_item), None)
		self.assertIsNotNone(rm_row)
		self.assertTrue(rm_row.serial_and_batch_bundle, "RM row must have a serial_and_batch_bundle")
		rm_dasm_serials = get_serial_nos_from_bundle(rm_row.serial_and_batch_bundle)
		self.assertEqual(len(rm_dasm_serials), disassemble_qty * 2)
		self.assertTrue(set(rm_dasm_serials).issubset(set(rm_serials_1)))
		self.assertFalse(
			set(rm_dasm_serials) & set(rm_serials_2), "Disassembly must not use SE_2's RM serials"
		)

	def test_components_alternate_item_for_bom_based_manufacture_entry(self):
		frappe.db.set_single_value("Manufacturing Settings", "backflush_raw_materials_based_on", "BOM")
		frappe.db.set_single_value("Manufacturing Settings", "validate_components_quantities_per_bom", 1)

		fg_item = "Test FG Item For Component Validation for alternate item"
		source_warehouse = "Stores - _TC"
		raw_materials = ["Test Component Validation RM Item 112", "Test Component Validation RM Item 22"]
		alternate_item = ["Alternate Test Component Validation RM Item 1"]

		make_item(fg_item, {"is_stock_item": 1})
		for item in raw_materials + alternate_item:
			make_item(item, {"is_stock_item": 1, "allow_alternative_item": 1})
			test_stock_entry.make_stock_entry(
				item_code=item,
				target=source_warehouse,
				qty=10,
				basic_rate=100,
			)

		frappe.get_doc(
			{
				"doctype": "Item Alternative",
				"item_code": raw_materials[0],
				"alternative_item_code": alternate_item[0],
				"two_way": 1,
			}
		).insert()

		make_bom(item=fg_item, source_warehouse=source_warehouse, raw_materials=raw_materials)

		wo = make_wo_order_test_record(
			item=fg_item,
			qty=10,
			source_warehouse=source_warehouse,
		)

		transfer_entry = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
		transfer_entry.save()
		transfer_entry.items[0].item_code = alternate_item[0]
		transfer_entry.items[0].original_item = raw_materials[0]
		transfer_entry.submit()

		self.assertTrue(transfer_entry.docstatus == 1)

		manufacture_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		manufacture_entry.save()
		self.assertTrue(manufacture_entry.items[0].item_code == alternate_item[0])
		self.assertTrue(manufacture_entry.items[0].original_item == raw_materials[0])

		manufacture_entry.submit()

		frappe.db.set_single_value("Manufacturing Settings", "validate_components_quantities_per_bom", 0)

	def test_transferred_qty_sums_item_and_its_alternate(self):
		# Base item + its alternate transfers must sum onto the required row, not overwrite.
		fg_item = "Test FG Item For Alternate Transferred Qty"
		source_warehouse = "Stores - _TC"
		raw_material = "Test RM For Alternate Transferred Qty"
		alternate_item = "Alternate Test RM For Alternate Transferred Qty"

		make_item(fg_item, {"is_stock_item": 1})
		for item in [raw_material, alternate_item]:
			make_item(item, {"is_stock_item": 1, "allow_alternative_item": 1})
			test_stock_entry.make_stock_entry(item_code=item, target=source_warehouse, qty=10, basic_rate=100)

		frappe.get_doc(
			{
				"doctype": "Item Alternative",
				"item_code": raw_material,
				"alternative_item_code": alternate_item,
				"two_way": 1,
			}
		).insert()

		make_bom(item=fg_item, source_warehouse=source_warehouse, raw_materials=[raw_material])
		wo = make_wo_order_test_record(item=fg_item, qty=10, source_warehouse=source_warehouse)

		# 6 as the base item
		frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 6)).submit()
		# 4 as the alternate item, linked back to the base
		alt_transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 4))
		alt_transfer.items[0].item_code = alternate_item
		alt_transfer.items[0].original_item = raw_material
		alt_transfer.submit()

		wo.reload()
		self.assertEqual(wo.required_items[0].transferred_qty, 10)
		self.assertEqual(wo.material_transferred_for_manufacturing, 10)

	def test_components_qty_for_bom_based_manufacture_entry(self):
		frappe.db.set_single_value("Manufacturing Settings", "backflush_raw_materials_based_on", "BOM")
		frappe.db.set_single_value("Manufacturing Settings", "validate_components_quantities_per_bom", 1)

		fg_item = "Test FG Item For Component Validation"
		source_warehouse = "Stores - _TC"
		raw_materials = ["Test Component Validation RM Item 1", "Test Component Validation RM Item 2"]

		make_item(fg_item, {"is_stock_item": 1})
		for item in raw_materials:
			make_item(item, {"is_stock_item": 1})
			test_stock_entry.make_stock_entry(
				item_code=item,
				target=source_warehouse,
				qty=10,
				basic_rate=100,
			)

		make_bom(item=fg_item, source_warehouse=source_warehouse, raw_materials=raw_materials)

		wo = make_wo_order_test_record(
			item=fg_item,
			qty=10,
			source_warehouse=source_warehouse,
		)

		transfer_entry = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
		transfer_entry.save()
		for row in transfer_entry.items:
			row.qty = 5

		self.assertRaises(frappe.ValidationError, transfer_entry.save)

		transfer_entry.reload()
		for row in transfer_entry.items:
			self.assertEqual(row.qty, 10)

		transfer_entry.submit()

		manufacture_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		manufacture_entry.save()
		for row in manufacture_entry.items:
			if not row.s_warehouse:
				continue

			row.qty = 5

		self.assertRaises(frappe.ValidationError, manufacture_entry.save)
		manufacture_entry.reload()
		manufacture_entry.submit()

		frappe.db.set_single_value("Manufacturing Settings", "validate_components_quantities_per_bom", 0)

	def test_components_as_per_bom_for_manufacture_entry(self):
		frappe.db.set_single_value("Manufacturing Settings", "backflush_raw_materials_based_on", "BOM")
		frappe.db.set_single_value("Manufacturing Settings", "validate_components_quantities_per_bom", 1)

		fg_item = "Test FG Item For Component Validation 1"
		source_warehouse = "Stores - _TC"
		raw_materials = ["Test Component Validation RM Item 11", "Test Component Validation RM Item 12"]

		make_item(fg_item, {"is_stock_item": 1})
		for item in raw_materials:
			make_item(item, {"is_stock_item": 1})
			test_stock_entry.make_stock_entry(
				item_code=item,
				target=source_warehouse,
				qty=10,
				basic_rate=100,
			)

		make_bom(item=fg_item, source_warehouse=source_warehouse, raw_materials=raw_materials)

		wo = make_wo_order_test_record(
			item=fg_item,
			qty=10,
			source_warehouse=source_warehouse,
		)

		transfer_entry = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
		transfer_entry.save()
		transfer_entry.remove(transfer_entry.items[0])

		self.assertRaises(frappe.ValidationError, transfer_entry.save)

		transfer_entry = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
		transfer_entry.save()
		transfer_entry.submit()

		manufacture_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		manufacture_entry.save()

		manufacture_entry.remove(manufacture_entry.items[0])

		self.assertRaises(frappe.ValidationError, manufacture_entry.save)
		manufacture_entry.delete()

		manufacture_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		manufacture_entry.save()
		manufacture_entry.submit()

		frappe.db.set_single_value("Manufacturing Settings", "validate_components_quantities_per_bom", 0)

	def test_wip_skip(self):
		wo = make_wo_order_test_record(
			item="_Test FG Item",
			qty=10,
			source_warehouse="_Test Warehouse - _TC",
			wip_warehouse="Stores - _TC",
		)
		manufacture_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		self.assertEqual(manufacture_entry.items[0].s_warehouse, "Stores - _TC")

		wo = make_wo_order_test_record(
			item="_Test FG Item",
			qty=10,
			source_warehouse="_Test Warehouse - _TC",
			wip_warehouse="Stores - _TC",
			skip_transfer=1,
		)
		manufacture_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		self.assertEqual(manufacture_entry.items[0].s_warehouse, "_Test Warehouse - _TC")

		wo = make_wo_order_test_record(
			item="_Test FG Item",
			qty=10,
			source_warehouse="_Test Warehouse - _TC",
			wip_warehouse="Stores - _TC",
			skip_transfer=1,
			from_wip_warehouse=1,
		)
		manufacture_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		self.assertEqual(manufacture_entry.items[0].s_warehouse, "Stores - _TC")

	def test_serial_no_status_for_stock_entry(self):
		items = {
			"Finished Good Test Item 1": {"is_stock_item": 1},
			"_Test RM Item with Serial No": {
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SN-FCG-NO-.####",
			},
		}
		for item, properties in items.items():
			make_item(item, properties)

		fg_item = "Finished Good Test Item 1"
		rec_se = test_stock_entry.make_stock_entry(
			item_code="_Test RM Item with Serial No", target="_Test Warehouse - _TC", qty=4, basic_rate=100
		)

		if not frappe.db.get_value("BOM", {"item": fg_item, "docstatus": 1}):
			bom = make_bom(
				item=fg_item,
				rate=1000,
				raw_materials=["_Test RM Item with Serial No"],
				do_not_save=True,
			)
			bom.rm_cost_as_per = "Price List"  # non stock item won't have valuation rate
			bom.buying_price_list = "_Test Price List India"
			bom.currency = "INR"
			bom.save()

		wo = make_wo_order_test_record(
			production_item=fg_item, skip_transfer=1, source_warehouse="_Test Warehouse - _TC"
		)

		ste = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 4))
		ste.items[0].use_serial_batch_fields = 1
		ste.items[0].serial_no = "\n".join(
			get_serial_nos_from_bundle(rec_se.items[0].serial_and_batch_bundle)
		)
		ste.insert()
		ste.submit()

		ste.reload()
		serial_nos = get_serial_nos_from_bundle(ste.items[0].serial_and_batch_bundle)
		for row in serial_nos:
			status = frappe.db.get_value("Serial No", row, "status")
			self.assertEqual(status, "Consumed")

	def test_work_order_valuation_auto_pick(self):
		fg_item = "Test FG Item For Non Transfer Item Batch"
		rm_item = "Test RM Item For Non Transfer Item Batch"

		make_item(fg_item, {"is_stock_item": 1})
		make_item(
			rm_item,
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TST-BATCH-NTI-.###",
			},
		)

		source_warehouse = "_Test Warehouse - _TC"
		wip_warehouse = "Stores - _TC"
		finished_goods_warehouse = create_warehouse("_Test Finished Goods Warehouse", company="_Test Company")

		batches = make_stock_in_entries_and_get_batches(rm_item, source_warehouse, wip_warehouse)

		if not frappe.db.get_value("BOM", {"item": fg_item}):
			make_bom(item=fg_item, raw_materials=[rm_item])

		wo = make_wo_order_test_record(
			item=fg_item,
			qty=5,
			source_warehouse=source_warehouse,
			wip_warehouse=wip_warehouse,
			fg_warehouse=finished_goods_warehouse,
		)

		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 5))
		stock_entry.items[0].batch_no = batches[1]
		stock_entry.items[0].use_serial_batch_fields = 1
		stock_entry.submit()
		stock_entry.reload()

		self.assertEqual(stock_entry.items[0].valuation_rate, 200)

		original_value = frappe.db.get_single_value(
			"Stock Settings", "auto_create_serial_and_batch_bundle_for_outward"
		)
		original_based_on = frappe.db.get_single_value("Stock Settings", "pick_serial_and_batch_based_on")

		frappe.db.set_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", 1)
		frappe.db.set_single_value("Stock Settings", "pick_serial_and_batch_based_on", "Expiry")

		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 5))
		stock_entry.items[0].use_serial_batch_fields = 1
		stock_entry.submit()
		stock_entry.reload()

		batch_no = get_batch_from_bundle(stock_entry.items[0].serial_and_batch_bundle)
		self.assertEqual(batch_no, batches[1])
		self.assertEqual(stock_entry.items[0].valuation_rate, 200)
		self.assertEqual(stock_entry.items[1].valuation_rate, 200)

		frappe.db.set_single_value(
			"Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", original_value
		)
		frappe.db.set_single_value("Stock Settings", "pick_serial_and_batch_based_on", original_based_on)

	def test_operations_time_planning_calculation(self):
		from erpnext.manufacturing.doctype.routing.test_routing import create_routing, setup_operations

		operations = [
			{"operation": "Test Operation A", "workstation": "Test Workstation A", "time_in_mins": 1},
			{"operation": "Test Operation B", "workstation": "Test Workstation A", "time_in_mins": 4},
			{"operation": "Test Operation C", "workstation": "Test Workstation A", "time_in_mins": 3},
			{"operation": "Test Operation D", "workstation": "Test Workstation A", "time_in_mins": 2},
		]
		setup_operations(operations)
		routing_doc = create_routing(routing_name="Testing Route", operations=operations)
		bom = make_bom(
			item="_Test FG Item", raw_materials=["_Test Item"], with_operations=1, routing=routing_doc.name
		)

		wo = make_wo_order_test_record(
			item="_Test FG Item",
			bom_no=bom.name,
			qty=5,
			source_warehouse="_Test Warehouse 1 - _TC",
			skip_transfer=1,
			fg_warehouse="_Test Warehouse 2 - _TC",
		)

		wo = frappe.copy_doc(wo)
		wo.operations[3].sequence_id = None

		# Test 1 : If any one operation does not have sequence ID then error will be thrown
		self.assertRaises(frappe.ValidationError, wo.submit)

		for op in wo.operations:
			op.sequence_id = None
		wo.submit()

		# Test 2 : If none of the operations have sequence ID then they will be sequenced as per their idx
		for op in wo.operations:
			self.assertEqual(op.sequence_id, op.idx)

		wo = frappe.copy_doc(wo)
		wo.operations[0].sequence_id = 2

		# Test 3 : Sequence IDs should not miss the correct sequence of numbers
		self.assertRaises(frappe.ValidationError, wo.submit)

		wo.operations[1].sequence_id = 1

		# Test 4 : Sequence IDs should be in the correct ascending order
		self.assertRaises(frappe.ValidationError, wo.submit)

		workstation = frappe.get_doc("Workstation", "Test Workstation A")
		workstation.production_capacity = 4
		workstation.save()
		wo = frappe.copy_doc(wo)
		wo.operations[0].sequence_id = 1
		wo.operations[1].sequence_id = 2
		wo.operations[2].sequence_id = 2
		wo.operations[3].sequence_id = 3
		wo.submit()

		# Test 5 : If two operations have the same sequence ID then the next operation will start 10 mins after the longest previous operation ends
		self.assertEqual(
			wo.operations[3].planned_start_time, add_to_date(wo.operations[1].planned_end_time, minutes=10)
		)

	def test_req_qty_clamping_in_manufacture_entry(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		fg_item = "Test Unconsumed RM FG Item"
		rm_item_1 = "Test Unconsumed RM Item 1"
		rm_item_2 = "Test Unconsumed RM Item 2"

		source_warehouse = "_Test Warehouse - _TC"
		wip_warehouse = "Stores - _TC"
		fg_warehouse = create_warehouse("_Test Finished Goods Warehouse", company="_Test Company")

		make_item(fg_item, {"is_stock_item": 1})
		make_item(rm_item_1, {"is_stock_item": 1})
		make_item(rm_item_2, {"is_stock_item": 1})

		# create a BOM: 1 FG = 1 RM1 + 1 RM2
		bom = make_bom(
			item=fg_item,
			source_warehouse=source_warehouse,
			raw_materials=[rm_item_1, rm_item_2],
			operating_cost_per_bom_quantity=1,
			do_not_submit=True,
		)

		for row in bom.exploded_items:
			make_stock_entry_test_record(
				item_code=row.item_code,
				target=source_warehouse,
				qty=100,
				basic_rate=100,
			)

		wo = make_wo_order_test_record(
			item=fg_item,
			qty=50,
			source_warehouse=source_warehouse,
			wip_warehouse=wip_warehouse,
		)
		wo.submit()

		# first partial transfer & manufacture (6 units)
		se_transfer_1 = frappe.get_doc(
			make_stock_entry(wo.name, "Material Transfer for Manufacture", 6, wip_warehouse)
		)
		se_transfer_1.insert()
		se_transfer_1.submit()

		stock_entry_1 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 6, fg_warehouse))

		# remove rm_2 from the items to simulate unconsumed RM scenario
		stock_entry_1.items = [row for row in stock_entry_1.items if row.item_code != rm_item_2]
		stock_entry_1.save()
		stock_entry_1.submit()

		wo.reload()

		se_transfer_2 = frappe.get_doc(
			make_stock_entry(wo.name, "Material Transfer for Manufacture", 20, wip_warehouse)
		)
		se_transfer_2.insert()
		se_transfer_2.submit()

		stock_entry_2 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 20, fg_warehouse))

		# validate rm_item_2 quantity is clamped correctly (per-unit BOM = 1 → max 20)
		for row in stock_entry_2.items:
			if row.item_code == rm_item_2:
				self.assertLessEqual(row.qty, 20)
				self.assertGreaterEqual(row.qty, 0)

	def test_overproduction_allowed_qty(self):
		"""Test overproduction allowed qty in work order"""
		allow_overproduction("overproduction_percentage_for_work_order", 50)

		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=10)

		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="Stores - _TC", qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=100,
			basic_rate=1000.0,
		)

		mt_stock_entry = frappe.get_doc(
			make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 10)
		)
		mt_stock_entry.submit()

		fg_stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
		fg_stock_entry.items[2].qty = 15
		fg_stock_entry.fg_completed_qty = 15
		fg_stock_entry.submit()

		wo_order.reload()

		self.assertEqual(wo_order.produced_qty, 15)
		self.assertEqual(wo_order.status, "Completed")

		allow_overproduction("overproduction_percentage_for_work_order", 0)

	def test_reserved_qty_for_pp_with_extra_material_transfer(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			make_stock_entry as make_stock_entry_test_record,
		)

		rm_item_code = make_item(
			"_Test Reserved Qty PP Item",
			{
				"is_stock_item": 1,
			},
		).name

		fg_item_code = make_item(
			"_Test Reserved Qty PP FG Item",
			{
				"is_stock_item": 1,
			},
		).name

		make_stock_entry_test_record(
			item_code=rm_item_code, target="_Test Warehouse - _TC", qty=10, basic_rate=100
		)

		make_bom(
			item=fg_item_code,
			raw_materials=[rm_item_code],
		)

		wo_order = make_wo_order_test_record(
			item=fg_item_code,
			qty=1,
			source_warehouse="_Test Warehouse - _TC",
			skip_transfer=0,
			target_warehouse="_Test Warehouse - _TC",
		)

		bin1_at_completion = get_bin(rm_item_code, "_Test Warehouse - _TC")
		self.assertEqual(bin1_at_completion.reserved_qty_for_production, 1)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 1))
		s.items[0].qty += 2  # extra material transfer
		s.submit()

		bin1_at_completion = get_bin(rm_item_code, "_Test Warehouse - _TC")

		self.assertEqual(bin1_at_completion.reserved_qty_for_production, 0)

	@change_settings(
		"Manufacturing Settings",
		{"allow_editing_of_items_and_quantities_in_work_order": 1},
	)
	def test_manufacture_se_fetches_edited_qty_from_work_order(self):
		"""When a raw material qty is edited on the Work Order, the Manufacture Stock Entry
		must consume the edited quantity (scaled to fg_completed_qty) from the Work Order,
		not the original BOM quantity."""
		warehouse = "_Test Warehouse - _TC"
		wo_order = make_wo_order_test_record(
			item="_Test FG Item", qty=10, skip_transfer=1, source_warehouse=warehouse
		)

		# edit a required item's qty
		wo_order.required_items[0].db_set("required_qty", flt(wo_order.required_items[0].required_qty) + 7)
		wo_order.reload()
		edited_row = wo_order.required_items[0]

		fg_qty = 5
		se = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", fg_qty))
		se_qty = {row.item_code: row.qty for row in se.items if row.s_warehouse}

		precision = frappe.get_precision("Stock Entry Detail", "qty")
		expected = flt(edited_row.required_qty / wo_order.qty * fg_qty, precision)
		self.assertEqual(flt(se_qty.get(edited_row.item_code)), expected)

	@change_settings(
		"Manufacturing Settings",
		{"allow_editing_of_items_and_quantities_in_work_order": 1},
	)
	def test_manufacture_se_fetches_item_not_in_bom_from_work_order(self):
		"""A raw material that is present on the Work Order but not on the BOM must still be
		fetched into the Manufacture Stock Entry, proving items are sourced from the Work
		Order's required_items rather than re-derived from the BOM."""
		extra_item = make_item(
			"_Test WO Extra Raw Material", {"is_stock_item": 1, "valuation_rate": 100}
		).name
		warehouse = "_Test Warehouse - _TC"
		wo_order = make_wo_order_test_record(
			item="_Test FG Item", qty=10, skip_transfer=1, source_warehouse=warehouse
		)

		original_item = wo_order.required_items[0].item_code
		wo_order.required_items[0].db_set("item_code", extra_item)
		wo_order.reload()

		se = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 5))
		se_items = [row.item_code for row in se.items if row.s_warehouse]

		self.assertIn(extra_item, se_items)
		self.assertNotIn(original_item, se_items)

	@change_settings(
		"Manufacturing Settings",
		{"backflush_raw_materials_based_on": "BOM", "validate_components_quantities_per_bom": 1},
	)
	def test_partial_alternative_item_transfer_for_bom_based_manufacture(self):
		source_warehouse = "Stores - _TC"
		fg_item = make_item("Test WO Partial Alt FG", {"is_stock_item": 1}).name
		item_a = make_item("Test WO Partial Alt RM A", {"is_stock_item": 1, "allow_alternative_item": 1}).name
		item_b = make_item("Test WO Partial Alt RM B", {"is_stock_item": 1, "allow_alternative_item": 1}).name

		if not frappe.db.exists("Item Alternative", {"item_code": item_a, "alternative_item_code": item_b}):
			frappe.get_doc(
				{"doctype": "Item Alternative", "item_code": item_a, "alternative_item_code": item_b}
			).insert()

		for item in (item_a, item_b):
			test_stock_entry.make_stock_entry(item_code=item, target=source_warehouse, qty=20, basic_rate=100)

		make_bom(item=fg_item, source_warehouse=source_warehouse, raw_materials=[item_a])
		wo = make_wo_order_test_record(
			item=fg_item, qty=10, source_warehouse=source_warehouse, do_not_save=True
		)
		wo.allow_alternative_item = 1
		wo.insert()
		wo.submit()

		# 5 qty transferred as the alternative RM B
		transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 5))
		self.assertEqual(transfer.items[0].allow_alternative_item, 1)
		transfer.items[0].item_code = item_b
		transfer.items[0].original_item = item_a
		transfer.items[0].allow_alternative_item = 0
		transfer.insert()
		# the flag is restored from the work order and the original item on save
		self.assertEqual(transfer.items[0].allow_alternative_item, 1)
		transfer.submit()

		# remaining 5 qty transferred as RM A itself
		transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 5))
		self.assertEqual(transfer.items[0].item_code, item_a)
		transfer.insert()
		transfer.submit()

		def get_rm_qty(stock_entry):
			rm_qty = defaultdict(float)
			for row in stock_entry.items:
				if row.s_warehouse:
					rm_qty[(row.item_code, row.original_item or None)] += flt(row.qty)
			return dict(rm_qty)

		manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 4))
		self.assertEqual(get_rm_qty(manufacture), {(item_b, item_a): 2.0, (item_a, None): 2.0})
		manufacture.insert()
		manufacture.submit()

		manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 6))
		self.assertEqual(get_rm_qty(manufacture), {(item_b, item_a): 3.0, (item_a, None): 3.0})
		manufacture.insert()
		manufacture.submit()

		wo.reload()
		self.assertEqual(wo.produced_qty, 10)
		self.assertEqual(len(wo.required_items), 1)
		self.assertEqual(wo.required_items[0].item_code, item_a)
		self.assertEqual(wo.required_items[0].transferred_qty, 10)
		self.assertEqual(wo.required_items[0].consumed_qty, 10)

	@change_settings(
		"Manufacturing Settings",
		{"backflush_raw_materials_based_on": "BOM", "material_consumption": 1},
	)
	def test_partial_alternative_item_transfer_with_material_consumption(self):
		source_warehouse = "Stores - _TC"
		fg_item = make_item("Test WO Partial Alt Consumption FG", {"is_stock_item": 1}).name
		item_a = make_item("Test WO Partial Alt RM A", {"is_stock_item": 1, "allow_alternative_item": 1}).name
		item_b = make_item("Test WO Partial Alt RM B", {"is_stock_item": 1, "allow_alternative_item": 1}).name

		if not frappe.db.exists("Item Alternative", {"item_code": item_a, "alternative_item_code": item_b}):
			frappe.get_doc(
				{"doctype": "Item Alternative", "item_code": item_a, "alternative_item_code": item_b}
			).insert()

		for item in (item_a, item_b):
			test_stock_entry.make_stock_entry(item_code=item, target=source_warehouse, qty=20, basic_rate=100)

		make_bom(item=fg_item, source_warehouse=source_warehouse, raw_materials=[item_a])
		wo = make_wo_order_test_record(
			item=fg_item, qty=10, source_warehouse=source_warehouse, do_not_save=True
		)
		wo.allow_alternative_item = 1
		wo.insert()
		wo.submit()

		transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
		transfer.items[0].qty = 6
		transfer.items[0].item_code = item_b
		transfer.items[0].original_item = item_a
		transfer.append("items", {**transfer.items[0].as_dict(), "name": None, "idx": None})
		transfer.items[1].item_code = item_a
		transfer.items[1].original_item = None
		transfer.items[1].qty = 4
		transfer.insert()
		transfer.submit()

		manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
		rm_qty = defaultdict(float)
		for row in manufacture.items:
			if row.s_warehouse:
				rm_qty[(row.item_code, row.original_item or None)] += flt(row.qty)

		self.assertEqual(dict(rm_qty), {(item_b, item_a): 6.0, (item_a, None): 4.0})
		manufacture.insert()
		manufacture.submit()

	@change_settings("Manufacturing Settings", {"validate_components_quantities_per_bom": 1})
	def test_bom_quantity_check_compares_alternatives_in_stock_uom(self):
		from unittest.mock import patch

		from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.update({"purpose": "Manufacture", "fg_completed_qty": 1, "bom_no": "_Test BOM"})
		for item_code, qty, conversion_factor, original_item in (
			("_Test RM A", 5, 10, None),
			("_Test RM B", 50, 1, "_Test RM A"),
		):
			stock_entry.append(
				"items",
				{
					"item_code": item_code,
					"original_item": original_item,
					"s_warehouse": "Stores - _TC",
					"qty": qty,
					"conversion_factor": conversion_factor,
					"transfer_qty": qty * conversion_factor,
				},
			)

		raw_materials = {"_Test RM A": frappe._dict(item_code="_Test RM A", qty=10, conversion_factor=10)}
		with patch.object(StockEntry, "get_bom_raw_materials", return_value=raw_materials):
			stock_entry.validate_component_and_quantities()

			stock_entry.items[1].transfer_qty = 40
			self.assertRaises(frappe.ValidationError, stock_entry.validate_component_and_quantities)


def make_stock_in_entries_and_get_batches(rm_item, source_warehouse, wip_warehouse):
	from erpnext.stock.doctype.stock_entry.test_stock_entry import (
		make_stock_entry as make_stock_entry_test_record,
	)

	batches = []
	for qty, rate in ((5, 100), (5, 200)):
		stock_entry = make_stock_entry_test_record(
			item_code=rm_item,
			target=source_warehouse,
			qty=qty,
			basic_rate=rate,
		)
		stock_entry.submit()
		stock_entry.reload()

		batch_no = get_batch_from_bundle(stock_entry.items[0].serial_and_batch_bundle)
		batch_doc = frappe.get_doc("Batch", batch_no)

		# keep early expiry date for the batch having rate 200
		days = 10 if rate == 100 else 1
		batch_doc.db_set("expiry_date", add_to_date(now(), days=days))

		batches.append(batch_no)

		stock_entry = make_stock_entry_test_record(
			item_code=rm_item,
			target=wip_warehouse,
			qty=qty,
			basic_rate=rate,
		)
		stock_entry.submit()
		stock_entry.reload()
		batch_no = get_batch_from_bundle(stock_entry.items[0].serial_and_batch_bundle)
		batch_doc = frappe.get_doc("Batch", batch_no)
		batch_doc.db_set("expiry_date", add_to_date(now(), days=10))

	return batches


def make_operation(**kwargs):
	kwargs = frappe._dict(kwargs)

	operation_doc = frappe.get_doc(
		{
			"doctype": "Operation",
			"name": kwargs.operation,
			"workstation": kwargs.workstation,
		}
	)
	operation_doc.insert()

	return operation_doc


def make_workstation(**kwargs):
	kwargs = frappe._dict(kwargs)

	workstation_doc = frappe.get_doc(
		{
			"doctype": "Workstation",
			"workstation_name": kwargs.workstation,
			"workstation_type": kwargs.workstation_type,
			"production_capacity": kwargs.production_capacity or 0,
			"hour_rate": kwargs.hour_rate or 100,
		}
	)
	workstation_doc.insert()

	return workstation_doc


def prepare_boms_for_sub_assembly_test():
	if not frappe.db.exists("BOM", {"item": "Test Final SF Item 1"}):
		bom = make_bom(
			item="Test Final SF Item 1",
			source_warehouse="Stores - _TC",
			raw_materials=["Test Final RM Item 1"],
			operating_cost_per_bom_quantity=100,
			do_not_submit=True,
		)

		bom.append("scrap_items", {"item_code": "Test Final Scrap Item 1", "qty": 1})

		bom.submit()

	if not frappe.db.exists("BOM", {"item": "Test Final SF Item 2"}):
		bom = make_bom(
			item="Test Final SF Item 2",
			source_warehouse="Stores - _TC",
			raw_materials=["Test Final RM Item 2"],
			operating_cost_per_bom_quantity=200,
			do_not_submit=True,
		)

		bom.append("scrap_items", {"item_code": "Test Final Scrap Item 2", "qty": 1})

		bom.submit()

	if not frappe.db.exists("BOM", {"item": "Test Final FG Item"}):
		bom = make_bom(
			item="Test Final FG Item",
			source_warehouse="Stores - _TC",
			raw_materials=["Test Final SF Item 1", "Test Final SF Item 2"],
		)


def prepare_data_for_workstation_type_check():
	from erpnext.manufacturing.doctype.operation.test_operation import make_operation
	from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
	from erpnext.manufacturing.doctype.workstation_type.test_workstation_type import (
		create_workstation_type,
	)

	workstation_types = ["Workstation Type 1", "Workstation Type 2", "Workstation Type 3"]
	for workstation_type in workstation_types:
		create_workstation_type(workstation_type=workstation_type)

	operations = ["Cutting", "Sewing", "Packing"]
	for operation in operations:
		make_operation(
			{
				"operation": operation,
			}
		)

	workstations = [
		{
			"workstation": "Workstation 1",
			"workstation_type": "Workstation Type 1",
		},
		{
			"workstation": "Workstation 2",
			"workstation_type": "Workstation Type 1",
		},
		{
			"workstation": "Workstation 3",
			"workstation_type": "Workstation Type 2",
		},
		{
			"workstation": "Workstation 4",
			"workstation_type": "Workstation Type 2",
		},
		{
			"workstation": "Workstation 5",
			"workstation_type": "Workstation Type 3",
		},
		{
			"workstation": "Workstation 6",
			"workstation_type": "Workstation Type 3",
		},
	]

	for row in workstations:
		make_workstation(row)

	fg_item = make_item(
		"Test FG Item For Workstation Type",
		{
			"is_stock_item": 1,
		},
	)

	rm_item = make_item(
		"Test RM Item For Workstation Type",
		{
			"is_stock_item": 1,
		},
	)

	if not frappe.db.exists("BOM", {"item": fg_item.name}):
		bom_doc = make_bom(
			item=fg_item.name,
			source_warehouse="Stores - _TC",
			raw_materials=[rm_item.name],
			do_not_submit=True,
		)

		submit_bom = False
		for index, operation in enumerate(operations):
			if not frappe.db.exists("BOM Operation", {"parent": bom_doc.name, "operation": operation}):
				bom_doc.append(
					"operations",
					{
						"operation": operation,
						"time_in_mins": 30,
						"hour_rate": 100,
						"workstation_type": workstation_types[index],
					},
				)

				submit_bom = True

		if submit_bom:
			bom_doc.submit()


def prepare_data_for_backflush_based_on_materials_transferred():
	batch_item_doc = make_item(
		"Test Batch MCC Keyboard",
		{
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "TBMK.#####",
			"valuation_rate": 100,
			"stock_uom": "Nos",
		},
	)

	item = make_item(
		"Test FG Item with Batch Raw Materials",
		{
			"is_stock_item": 1,
		},
	)

	make_bom(item=item.name, source_warehouse="Stores - _TC", raw_materials=[batch_item_doc.name])

	# Make additional items not attached to a BOM
	make_item(
		"Test Batch Battery Consumable",
		{
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "TBMK.#####",
			"valuation_rate": 2.33,
			"stock_uom": "Nos",
		},
	)
	make_item(
		"Test Serial Battery Consumable",
		{
			"is_stock_item": 1,
			"has_serial_no": 1,
			"serial_no_series": "TSBH.#####",
			"valuation_rate": 3.33,
			"stock_uom": "Nos",
		},
	)

	sn_item_doc = make_item(
		"Test Serial No BTT Headphone",
		{
			"is_stock_item": 1,
			"has_serial_no": 1,
			"serial_no_series": "TSBH.#####",
			"valuation_rate": 100,
			"stock_uom": "Nos",
		},
	)

	item = make_item(
		"Test FG Item with Serial No Raw Materials",
		{
			"is_stock_item": 1,
		},
	)

	make_bom(item=item.name, source_warehouse="Stores - _TC", raw_materials=[sn_item_doc.name])

	sn_batch_item_doc = make_item(
		"Test Batch Serial No WebCam",
		{
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "TBSW.#####",
			"has_serial_no": 1,
			"serial_no_series": "TBSWC.#####",
			"valuation_rate": 100,
			"stock_uom": "Nos",
		},
	)

	item = make_item(
		"Test FG Item with Serial & Batch No Raw Materials",
		{
			"is_stock_item": 1,
		},
	)

	make_bom(item=item.name, source_warehouse="Stores - _TC", raw_materials=[sn_batch_item_doc.name])


def update_job_card(job_card, jc_qty=None, days=None):
	employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
	job_card_doc = frappe.get_doc("Job Card", job_card)
	job_card_doc.set(
		"scrap_items",
		[
			{"item_code": "Test RM Item 1 for Scrap Item Test", "stock_qty": 2},
			{"item_code": "Test RM Item 2 for Scrap Item Test", "stock_qty": 2},
		],
	)

	if jc_qty:
		job_card_doc.for_quantity = jc_qty

	for row in job_card_doc.scheduled_time_logs:
		job_card_doc.append(
			"time_logs",
			{
				"from_time": row.from_time,
				"to_time": row.to_time,
				"employee": employee,
				"time_in_mins": 60,
				"completed_qty": 0.0,
			},
		)

	if not job_card_doc.time_logs and days:
		planned_start_time = add_days(now(), days=days)
		job_card_doc.append(
			"time_logs",
			{
				"from_time": planned_start_time,
				"to_time": add_to_date(planned_start_time, minutes=60),
				"employee": employee,
				"time_in_mins": 60,
				"completed_qty": 0.0,
			},
		)

	job_card_doc.time_logs[0].completed_qty = job_card_doc.for_quantity

	job_card_doc.submit()


def get_scrap_item_details(bom_no):
	scrap_items = {}
	for item in frappe.db.sql(
		"""select item_code, stock_qty from `tabBOM Scrap Item`
		where parent = %s""",
		bom_no,
		as_dict=1,
	):
		scrap_items[item.item_code] = item.stock_qty

	return scrap_items


def allow_overproduction(fieldname, percentage):
	doc = frappe.get_doc("Manufacturing Settings")
	doc.update({fieldname: percentage})
	doc.save()


def make_wo_order_test_record(**args):
	args = frappe._dict(args)
	if args.company and args.company != "_Test Company":
		warehouse_map = {"fg_warehouse": "_Test FG Warehouse", "wip_warehouse": "_Test WIP Warehouse"}

		for attr, wh_name in warehouse_map.items():
			if not args.get(attr):
				args[attr] = create_warehouse(wh_name, company=args.company)

	wo_order = frappe.new_doc("Work Order")
	wo_order.production_item = args.production_item or args.item or args.item_code or "_Test FG Item"
	wo_order.bom_no = args.bom_no or frappe.db.get_value(
		"BOM", {"item": wo_order.production_item, "is_active": 1, "is_default": 1}
	)
	wo_order.qty = args.qty or 10
	wo_order.wip_warehouse = args.wip_warehouse or "_Test Warehouse - _TC"
	wo_order.fg_warehouse = args.fg_warehouse or "_Test Warehouse 1 - _TC"
	wo_order.scrap_warehouse = args.fg_warehouse or "_Test Scrap Warehouse - _TC"
	wo_order.company = args.company or "_Test Company"
	wo_order.stock_uom = args.stock_uom or "_Test UOM"
	wo_order.use_multi_level_bom = args.use_multi_level_bom or 0
	wo_order.skip_transfer = args.skip_transfer or 0
	wo_order.get_items_and_operations_from_bom()
	wo_order.sales_order = args.sales_order or None
	wo_order.planned_start_date = args.planned_start_date or now()
	wo_order.expected_delivery_date = args.expected_delivery_date
	wo_order.transfer_material_against = args.transfer_material_against or "Work Order"
	wo_order.from_wip_warehouse = args.from_wip_warehouse or 0
	wo_order.batch_size = args.batch_size or 0
	wo_order.status = args.status or "Draft"

	if args.source_warehouse:
		wo_order.source_warehouse = args.source_warehouse
		for item in wo_order.get("required_items"):
			item.source_warehouse = args.source_warehouse

	if not args.do_not_save:
		wo_order.insert()

		if not args.do_not_submit:
			wo_order.submit()
	return wo_order


test_records = frappe.get_test_records("Work Order")


class TestWorkOrderExplicitDetails(FrappeTestCase):
	"""CASE-01 default empty draft and real human-confirmation boundary."""

	def setUp(self):
		from frappe.permissions import add_permission
		self.f = TestWorkOrderApproval("test_00_fixture_runnable")
		self.addCleanup(self.f.doCleanups)
		self.f.setUp()
		frappe.set_user("Administrator")
		add_permission("BOM", self.f.roles[0], ptype="read")
		bom = frappe.copy_doc(frappe.get_doc("BOM", self.f.order_args["bom_no"]))
		bom.docstatus = 0
		bom.is_default = 0
		bom.with_operations = 1
		unit = frappe.get_doc({"doctype": "UOM", "uom_name": self.f.prefix + "-小数单位", "must_be_whole_number": 0}).insert().name
		raw = create_item(self.f.prefix + "-decimal-raw", stock_uom=unit, company=bom.company, warehouse=self.f.order.source_warehouse)
		for row in bom.items:
			row.item_code = raw.name
			row.uom = row.stock_uom = unit
			row.conversion_factor = 1
			row.qty = 0.5
		bom.set("operations", [])
		for i, operation in enumerate(self.f.operations, 1):
			bom.append("operations", {"operation": operation, "workstation": self.f.workstation,
				"time_in_mins": 1, "sequence_id": i})
		bom.insert().submit()
		self.bom = bom
		frappe.set_user(self.f.users["operator"])
		self.order = frappe.get_doc({"doctype": "Work Order", "production_item": bom.item,
			"bom_no": bom.name, "qty": 10, "company": bom.company, "stock_uom": "Nos",
			"production_team": self.f.teams[0], "planned_start_date": now(),
			"expected_delivery_date": self.f.order_args["expected_delivery_date"],
			"source_warehouse": self.f.order.source_warehouse,
			"wip_warehouse": self.f.order.wip_warehouse, "fg_warehouse": self.f.order.fg_warehouse,
			"transfer_material_against": "Work Order"}).insert()

	def preview(self, version=None):
		from erpnext.manufacturing.doctype.work_order import work_order as api
		self.assertTrue(callable(getattr(api, "preview_production_order_details", None)), "Missing read-only details preview")
		return api.preview_production_order_details(self.order.name, str(version or self.order.modified))

	def confirm(self, preview, version=None):
		from erpnext.manufacturing.doctype.work_order import work_order as api
		self.assertTrue(callable(getattr(api, "confirm_production_order_details", None)), "Missing human details confirmation")
		return api.confirm_production_order_details(self.order.name, str(version or self.order.modified), preview["fingerprint"])

	def test_empty_draft_stays_empty(self):
		self.order.save().reload()
		self.assertEqual(len(self.order.operations), 0)
		self.assertEqual(len(self.order.required_items), 0)
		self.assertFalse(frappe.db.exists("Job Card", {"work_order": self.order.name}))
		self.assertFalse(frappe.db.exists("Stock Entry", {"work_order": self.order.name}))
		self.f.order = self.order
		with self.assertRaises(frappe.ValidationError):
			self.f.act("operator", "送审")

	def test_preview_confirm_replay(self):
		preview = self.preview()
		self.assertEqual(len(preview["operations"]), 3)
		self.assertEqual(len(preview["items"]), 1)
		self.assertEqual(preview["items"][0]["required_qty"], 5)
		self.order.reload()
		self.assertEqual((len(self.order.operations), len(self.order.required_items)), (0, 0))
		version = str(self.order.modified)
		self.confirm(preview, version)
		self.order.reload()
		self.assertEqual([r.operation for r in self.order.operations], self.f.operations)
		self.assertEqual(self.order.required_items[0].required_qty, 5)
		identities = ([r.name for r in self.order.operations], [r.name for r in self.order.required_items], self.order.modified)
		self.confirm(preview, version)
		self.order.reload()
		self.assertEqual(identities, ([r.name for r in self.order.operations], [r.name for r in self.order.required_items], self.order.modified))
		self.assertFalse(frappe.db.exists("Job Card", {"work_order": self.order.name}))
		self.assertFalse(frappe.db.exists("Stock Entry", {"work_order": self.order.name}))

	def test_stale_basis_and_order_rejected(self):
		preview = self.preview()
		version = str(self.order.modified)
		self.order.qty = 11
		self.order.save()
		with self.assertRaises(frappe.TimestampMismatchError):
			self.confirm(preview, version)
		preview = self.preview()
		frappe.set_user("Administrator")
		frappe.db.set_value("BOM Operation", self.bom.operations[0].name, "time_in_mins", 2)
		frappe.set_user(self.f.users["operator"])
		with self.assertRaises(frappe.TimestampMismatchError):
			self.confirm(preview)
		self.order.reload()
		self.assertEqual((len(self.order.operations), len(self.order.required_items)), (0, 0))

	def test_scope_and_frozen_rejected(self):
		from frappe.permissions import add_user_permission
		preview = self.preview()
		frappe.set_user("Administrator")
		permission = frappe.db.get_value("User Permission", {
			"user": self.f.users["operator"], "allow": "Company", "for_value": self.order.company,
		}, "name")
		frappe.delete_doc("User Permission", permission)
		frappe.set_user(self.f.users["operator"])
		with self.assertRaises(frappe.PermissionError):
			self.preview()
		with self.assertRaises(frappe.PermissionError):
			self.confirm(preview)
		self.order.reload()
		self.assertEqual((len(self.order.operations), len(self.order.required_items)), (0, 0))
		frappe.set_user("Administrator")
		add_user_permission("Company", self.order.company, self.f.users["operator"])
		frappe.set_user(self.f.users["other"])
		with self.assertRaises(frappe.PermissionError):
			self.confirm(preview)
		frappe.set_user(self.f.users["operator"])
		self.confirm(preview)
		self.order.reload()
		self.f.order = self.order
		self.f.act("operator", "送审")
		with self.assertRaises(frappe.PermissionError):
			self.preview()
		with self.assertRaises(frappe.PermissionError):
			self.confirm(preview)
		self.assertEqual(frappe.db.count("Work Order Operation", {"parent": self.order.name}), 3)

	def test_confirmation_save_failure_rolls_back(self):
		from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
		preview = self.preview()
		frappe.db.savepoint("details_failure")
		original = WorkOrder.save
		class InjectedDetailsFailure(Exception):
			pass
		def save_then_fail(doc, *args, **kwargs):
			result = original(doc, *args, **kwargs)
			self.assertEqual(frappe.db.count("Work Order Operation", {"parent": self.order.name}), 3)
			raise InjectedDetailsFailure("after native save")
		with patch.object(WorkOrder, "save", save_then_fail), self.assertRaises(InjectedDetailsFailure):
			self.confirm(preview)
		frappe.db.rollback(save_point="details_failure")
		self.order.reload()
		self.assertEqual((len(self.order.operations), len(self.order.required_items)), (0, 0))
		self.confirm(self.preview())
		self.order.reload()
		self.assertEqual((len(self.order.operations), len(self.order.required_items)), (3, 1))

	def test_switch_explosion_does_not_generate(self):
		self.order.use_multi_level_bom = 1 - int(self.order.use_multi_level_bom or 0)
		self.order.save().reload()
		self.assertEqual((len(self.order.operations), len(self.order.required_items)), (0, 0))

	def test_confirmed_basis_requires_clearing(self):
		self.confirm(self.preview())
		self.order.reload()
		self.order.qty = 20
		with self.assertRaises(frappe.ValidationError):
			self.order.save()
		self.order.reload()
		self.assertEqual((self.order.qty, self.order.required_items[0].required_qty), (10, 5))
		self.order.set("operations", [])
		self.order.set("required_items", [])
		self.order.qty = 20
		self.order.save().reload()
		self.confirm(self.preview())
		self.order.reload()
		self.assertEqual(self.order.required_items[0].required_qty, 10)

	def test_unsequenced_route_replay(self):
		for row in self.bom.operations:
			frappe.db.set_value("BOM Operation", row.name, "sequence_id", 0)
		preview = self.preview()
		version = str(self.order.modified)
		self.confirm(preview, version)
		self.order.reload()
		identities = [row.name for row in self.order.operations]
		self.confirm(preview, version)
		self.order.reload()
		self.assertEqual([row.name for row in self.order.operations], identities)
		self.assertEqual([row.sequence_id for row in self.order.operations], [1, 2, 3])

	def test_single_operation_replay(self):
		frappe.db.delete("BOM Operation", {"name": ["in", [row.name for row in self.bom.operations[1:]]]})
		preview = self.preview()
		version = str(self.order.modified)
		self.confirm(preview, version)
		self.order.reload()
		identities = ([row.name for row in self.order.operations], [row.name for row in self.order.required_items])
		self.confirm(preview, version)
		self.order.reload()
		self.assertEqual(([row.name for row in self.order.operations], [row.name for row in self.order.required_items]), identities)
		self.assertEqual(self.order.required_items[0].operation, self.f.operations[0])


class TestWorkOrderCloseout(FrappeTestCase):
	"""B05 bounded closing; reuse real approval, timer and report fixtures."""

	def setUp(self):
		from erpnext.manufacturing.doctype.job_card.test_job_card import TestProductionReportConfirmation
		self.report_case = TestProductionReportConfirmation()
		self.addCleanup(self.report_case.doCleanups)
		with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
			self.report_case.setUp()
		self.f = self.report_case.approval
		self.card_name = frappe.db.get_value("Job Card", {"work_order": self.f.order.name,
			"operation_id": self.f.order.operations[0].name, "docstatus": 0}, "name")
		self.assertTrue(self.card_name)
		self.end_time = "2026-10-20 10:00:00"

	def method(self, name):
		from erpnext.manufacturing.doctype.work_order import work_order
		method = getattr(work_order, name, None)
		self.assertTrue(callable(method), name + " is not implemented")
		return method

	def start(self):
		from erpnext.manufacturing.doctype.job_card.job_card import make_time_log
		frappe.set_user(self.f.users["operator"])
		make_time_log({"job_card_id": self.card_name, "start_time": "2026-10-20 09:00:00", "status": "Work In Progress"})
		self.f.order.reload()

	def preview(self):
		frappe.set_user(self.f.users["director"])
		self.f.order.reload()
		return self.method("preview_production_close")(self.f.order.name, str(self.f.order.modified))

	def finish(self, preview=None, **changes):
		preview = preview or self.preview()
		return self.method("finish_production_timers")(**dict({"work_order": self.f.order.name,
			"expected_modified": preview["modified"], "timer_fingerprint": preview["timer_fingerprint"],
			"end_time": self.end_time}, **changes))

	def close(self, reason="客户缩量，保留缺额和原记录", **changes):
		self.f.order.reload()
		return self.method("close_work_order")(**dict({"work_order": self.f.order.name,
			"status": "Closed", "expected_modified": str(self.f.order.modified), "reason": reason}, **changes))

	def facts(self):
		return frappe.as_json({"reports": frappe.get_all("Job Card", filters={"work_order": self.f.order.name,
			"docstatus": [">", 0]}, fields=["*"], order_by="name"),
			"report_logs": frappe.get_all("Job Card Time Log", filters={"parent": ["in", frappe.get_all("Job Card",
				filters={"work_order": self.f.order.name, "docstatus": [">", 0]}, pluck="name") or ["__none__"]]}, fields=["*"], order_by="name"),
			"operations": frappe.get_all("Work Order Operation", filters={"parent": self.f.order.name}, fields=["*"], order_by="name"),
			"stock": frappe.get_all("Stock Entry", filters={"work_order": self.f.order.name}, fields=["*"], order_by="name")})

	def test_00_fixture_runnable(self):
		self.assertEqual(self.f.order.docstatus, 1)
		self.assertEqual(self.f.order.status, "Not Started")
		self.assertEqual(len(self.f.order.operations), 3)
		self.assertEqual(frappe.get_doc("Job Card", self.card_name).docstatus, 0)

	def test_open_draft_timer_is_not_ignored_by_legacy_signature(self):
		self.start()
		card = frappe.get_doc("Job Card", self.card_name)
		self.assertEqual(card.status, "Work In Progress")
		self.assertFalse(card.time_logs[0].to_time)
		frappe.set_user(self.f.users["director"])
		with self.assertRaises(frappe.ValidationError):
			self.method("close_work_order")(self.f.order.name, "Closed")
		self.assertNotEqual(self.f.order.reload().status, "Closed")

	def test_finish_then_close_preserves_gap_reason_and_original_facts(self):
		import html
		import json
		import re
		self.report_case.report(8, 2, hour=7)
		self.start()
		before = self.facts()
		preview = self.preview()
		self.assertEqual(len(preview["open_timers"]), 1)
		self.assertEqual(preview["operations"][0]["unfinished"], 0)
		self.assertEqual(preview["operations"][0]["good"], 8)
		self.assertEqual(preview["operations"][0]["bad"], 2)
		self.assertEqual(preview["stock_unfinished"], 10)
		with self.assertRaisesRegex(frappe.ValidationError, "活动计时"):
			self.close()
		self.finish(preview)
		card = frappe.get_doc("Job Card", self.card_name)
		self.assertEqual(card.docstatus, 0)
		self.assertEqual(card.total_completed_qty, 0)
		self.assertEqual(card.time_logs[0].time_in_mins, 60)
		self.assertEqual(str(card.time_logs[0].to_time), self.end_time)
		self.assertEqual(card.status, "On Hold")
		self.assertFalse(card.started_time)
		self.assertEqual(self.facts(), before)
		reason = "缺件 <确认> & 保留原记录"
		result = self.close(reason)
		self.assertEqual(result["status"], "Closed")
		self.assertEqual(self.f.order.reload().status, "Closed")
		comment = frappe.get_doc("Comment", result["comment"])
		self.assertIn("人工结束时间", comment.content)
		self.assertIn("未入库差额", comment.content)
		snapshot = json.loads(html.unescape(re.search(r"<pre>(.*?)</pre>", comment.content, re.S).group(1)))
		self.assertEqual(snapshot["结束原因"], reason)
		self.assertEqual(snapshot["操作者"], self.f.users["director"])
		self.assertTrue(snapshot["人工结束时间"])
		self.assertEqual(snapshot["工序差额"][0]["良品"], 8)
		self.assertEqual(snapshot["工序差额"][0]["不良"], 2)
		self.assertEqual(snapshot["工序差额"][0]["未清数量"], 0)
		self.assertEqual(snapshot["未入库差额"], 10)
		self.assertEqual(self.facts(), before)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Comment", comment.name)
		with self.assertRaises(frappe.ValidationError):
			self.close("不能改写旧原因")
		self.assertEqual(frappe.get_doc("Comment", comment.name).content, comment.content)
		from erpnext.manufacturing.doctype.job_card.job_card import make_time_log
		frappe.set_user(self.f.users["operator"])
		with self.assertRaises(frappe.PermissionError):
			make_time_log({"job_card_id": self.card_name, "start_time": "2026-10-20 11:00:00", "status": "Work In Progress"})
		self.assertEqual(len(frappe.get_doc("Job Card", self.card_name).time_logs), 1)

	def test_stopped_order_allows_only_existing_timer_finish(self):
		self.start()
		self.f.act("director", "停止执行", reason="需求变更，收尾既有计时")
		from erpnext.manufacturing.doctype.job_card.job_card import make_time_log
		frappe.set_user(self.f.users["operator"])
		with self.assertRaises(frappe.PermissionError):
			make_time_log({"job_card_id": self.card_name, "start_time": self.end_time, "status": "Work In Progress"})
		self.finish()
		self.assertEqual(self.f.order.reload().status, "Stopped")
		self.assertFalse(getattr(frappe.local, "production_timer_finish_context", None))
		self.close()
		self.assertEqual(self.f.order.reload().status, "Closed")

	def test_preview_is_read_only_and_missing_reason_or_version_is_rejected(self):
		self.start()
		before = frappe.get_doc("Job Card", self.card_name).as_json()
		old_modified = str(self.f.order.modified)
		preview = self.preview()
		self.assertEqual(before, frappe.get_doc("Job Card", self.card_name).as_json())
		self.assertEqual(str(self.f.order.reload().modified), old_modified)
		for reason in (None, "", "  "):
			with self.subTest(reason=reason), self.assertRaises(frappe.ValidationError):
				self.close(reason)
		with self.assertRaises(frappe.TimestampMismatchError):
			self.close(expected_modified="2000-01-01 00:00:00")
		with self.assertRaises(frappe.TimestampMismatchError):
			self.finish(preview, expected_modified="2000-01-01 00:00:00")
		self.assertEqual(before, frappe.get_doc("Job Card", self.card_name).as_json())

	def test_invalid_time_or_changed_timer_is_rejected_without_writes(self):
		self.start()
		preview = self.preview()
		before = frappe.get_doc("Job Card", self.card_name).as_json()
		for end in (None, "not-a-time", "2026-10-20 08:59:59", "2999-01-01 00:00:00"):
			with self.subTest(end=end), self.assertRaises(frappe.ValidationError):
				self.finish(preview, end_time=end)
		self.assertEqual(before, frappe.get_doc("Job Card", self.card_name).as_json())
		frappe.db.set_value("Job Card", self.card_name, "modified", "2026-10-20 12:00:00", update_modified=False)
		with self.assertRaises(frappe.TimestampMismatchError):
			self.finish(preview)
		self.assertFalse(frappe.get_doc("Job Card", self.card_name).time_logs[0].to_time)

	def test_other_roles_and_company_revocation_cannot_finish_or_close(self):
		self.start()
		preview = self.preview()
		for key in ("operator", "reviewer", "other", "outsider"):
			frappe.set_user(self.f.users[key])
			with self.subTest(key=key), self.assertRaises(frappe.PermissionError):
				self.method("preview_production_close")(self.f.order.name, preview["modified"])
			with self.assertRaises(frappe.PermissionError):
				self.finish(preview)
			with self.assertRaises(frappe.PermissionError):
				self.close()
		frappe.set_user("Administrator")
		frappe.db.delete("User Permission", {"user": self.f.users["director"], "allow": "Company"})
		frappe.clear_cache(user=self.f.users["director"])
		frappe.set_user(self.f.users["director"])
		with self.assertRaises(frappe.PermissionError):
			self.finish(preview)
		with self.assertRaises(frappe.PermissionError):
			self.close()
		self.assertNotEqual(self.f.order.reload().status, "Closed")

	def test_timer_fingerprint_is_bound_to_parent(self):
		self.start()
		preview = self.preview()
		frappe.set_user(self.f.users["operator"])
		other = make_wo_order_test_record(**self.f.order_args)
		other.production_team = self.f.teams[0]
		for operation in self.f.operations:
			other.append("operations", {"operation": operation, "workstation": self.f.workstation, "time_in_mins": 1})
		other.insert()
		original = self.f.order
		self.f.order = other
		self.f.act("operator", "送审")
		self.f.act("reviewer", "审核通过")
		with change_settings("Manufacturing Settings", {"disable_capacity_planning": 1}):
			self.f.act("director", "签批通过")
		with self.assertRaises(frappe.TimestampMismatchError):
			self.finish(preview, work_order=other.name, expected_modified=str(other.modified))
		self.f.order = original
		self.assertFalse(frappe.get_doc("Job Card", self.card_name).time_logs[0].to_time)

	def test_submitted_open_timer_is_not_rewritten(self):
		result = self.report_case.report(1, 0, hour=7)
		name = result["name"]
		frappe.db.set_value("Job Card Time Log", {"parent": name}, "to_time", None)
		before = self.facts()
		preview = self.preview()
		with self.assertRaisesRegex(frappe.ValidationError, "已生效|已提交"):
			self.finish(preview)
		with self.assertRaisesRegex(frappe.ValidationError, "活动计时"):
			self.close()
		self.assertEqual(before, self.facts())

	def test_finish_and_close_failures_propagate_and_rollback(self):
		from unittest.mock import patch
		from erpnext.manufacturing.doctype.job_card.job_card import JobCard
		from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
		self.start()
		preview = self.preview()
		before = frappe.get_doc("Job Card", self.card_name).as_json()
		real_save = JobCard.save
		def saved_then_fail(card, *args, **kwargs):
			real_save(card, *args, **kwargs)
			raise RuntimeError("B05 controlled failure after timer save")
		frappe.db.savepoint("b05_finish_fault")
		with patch.object(JobCard, "save", saved_then_fail), self.assertRaises(RuntimeError):
			self.finish(preview)
		self.assertFalse(getattr(frappe.local, "production_timer_finish_context", None))
		frappe.db.rollback(save_point="b05_finish_fault")
		self.assertEqual(frappe.get_doc("Job Card", self.card_name).as_json(), before)
		self.finish(preview)
		self.f.order.reload()
		before_status = self.f.order.status
		comment_count = frappe.db.count("Comment", {"reference_name": self.f.order.name})
		frappe.db.savepoint("b05_close_fault")
		with patch.object(WorkOrder, "add_comment", side_effect=RuntimeError("B05 controlled comment failure")), self.assertRaises(RuntimeError):
			self.close()
		frappe.db.rollback(save_point="b05_close_fault")
		self.assertEqual(self.f.order.reload().status, before_status)
		self.assertEqual(frappe.db.count("Comment", {"reference_name": self.f.order.name}), comment_count)
		self.close()
		self.assertEqual(self.f.order.reload().status, "Closed")


class TestWorkOrderHeader(FrappeTestCase):
	"""B05 header/number/prerequisites only, using existing native fields and fixtures."""

	def setUp(self):
		from frappe.permissions import add_permission
		self.f = TestWorkOrderApproval("test_00_fixture_runnable")
		self.addCleanup(self.f.doCleanups)
		self.f.setUp()
		frappe.set_user("Administrator")
		add_permission("BOM", self.f.roles[0], ptype="read")
		frappe.set_user(self.f.users["operator"])

	def draft(self, **changes):
		return frappe.get_doc(dict({"doctype":"Work Order", "production_item":self.f.order.production_item,
			"bom_no":self.f.order.bom_no, "qty":10, "company":self.f.company, "stock_uom":"Nos",
			"production_team":self.f.teams[0], "planned_start_date":now(),
			"expected_delivery_date":self.f.order_args["expected_delivery_date"],
			"source_warehouse":self.f.order.source_warehouse, "wip_warehouse":self.f.order.wip_warehouse,
			"fg_warehouse":self.f.order.fg_warehouse}, **changes))

	def details(self, order):
		from erpnext.manufacturing.doctype.work_order.work_order import preview_production_order_details
		return preview_production_order_details(order.name, str(order.modified))

	def test_00_fixture_runnable(self):
		self.assertEqual(self.f.order.workflow_state, "草稿")
		self.assertTrue(self.f.order.expected_delivery_date)
		self.assertEqual(len(self.f.order.operations),3)
		self.assertFalse(frappe.db.exists("Job Card",{"work_order":self.f.order.name}))

	def test_native_numbers_unique_persisted_and_duplicate_rejected(self):
		first, second = self.draft().insert(), self.draft().insert()
		self.assertNotEqual(first.name,second.name)
		self.assertRegex(first.name,r"^MFG-WO-"+frappe.utils.nowdate()[:4]+r"-\d+$")
		self.assertEqual(first.reload().name,first.name)
		self.assertEqual(first.naming_series,"MFG-WO-.YYYY.-")
		count=frappe.db.count("Work Order")
		with self.assertRaises(frappe.DuplicateEntryError):
			self.draft().insert(set_name=first.name)
		self.assertEqual(frappe.db.count("Work Order"),count)
		self.assertEqual(frappe.get_doc("Work Order",first.name).qty,10)

	def test_draft_without_delivery_saves_but_review_is_blocked(self):
		self.f.order.expected_delivery_date=None
		self.f.order.save()
		before=frappe.db.count("Comment",{"reference_name":self.f.order.name})
		self.assertFalse(self.f.order.reload().expected_delivery_date)
		with self.assertRaisesRegex(frappe.ValidationError,"预计交付日期"):
			self.f.act("operator","送审")
		self.assertEqual(self.f.order.reload().workflow_state,"草稿")
		self.assertEqual(frappe.db.count("Comment",{"reference_name":self.f.order.name}),before)
		self.assertFalse(frappe.db.exists("Job Card",{"work_order":self.f.order.name}))

	def test_delivery_roundtrip_preserves_plan_and_review_freeze(self):
		before={key:[row.name for row in self.f.order.get(key)] for key in ("operations","required_items")}
		due=frappe.utils.add_days(frappe.utils.nowdate(),10)
		self.f.order.expected_delivery_date=due
		self.f.order.save().reload()
		self.assertEqual(str(self.f.order.expected_delivery_date),due)
		self.assertEqual(before,{key:[row.name for row in self.f.order.get(key)] for key in before})
		number=self.f.order.name
		self.f.act("operator","送审")
		self.assertEqual(self.f.order.workflow_state,"待审核")
		self.assertEqual(self.f.order.name,number)
		self.f.order.expected_delivery_date=frappe.utils.add_days(due,1)
		with self.assertRaises(frappe.PermissionError): self.f.order.save()
		self.assertEqual(str(self.f.order.reload().expected_delivery_date),due)

	def test_invalid_delivery_and_date_order_rejected(self):
		count=frappe.db.count("Work Order")
		for due in ("0000-00-00","not-a-date"):
			with self.subTest(due=due),self.assertRaises(frappe.ValidationError):
				self.draft(planned_start_date="2026-01-02 09:00:00",expected_delivery_date=due).insert()
		self.assertEqual(frappe.db.count("Work Order"),count)
		valid=self.draft(planned_start_date="2026-01-02 09:00:00",expected_delivery_date="2026-01-02").insert()
		self.assertEqual(str(valid.reload().expected_delivery_date),"2026-01-02")
		with self.assertRaises(frappe.ValidationError):
			self.draft(planned_start_date="2026-01-02 09:00:00",planned_end_date="2026-01-01 09:00:00").insert()

	def test_overdue_delivery_is_preserved_with_warning(self):
		frappe.local.message_log = []
		order=self.draft(planned_start_date="2026-01-02 09:00:00",expected_delivery_date="2026-01-01").insert()
		self.assertEqual(str(order.reload().expected_delivery_date),"2026-01-01")
		self.assertTrue(any("可能逾期" in str(message) for message in frappe.local.message_log))
		self.assertFalse(order.operations or order.required_items)

	def test_missing_bom_and_route_are_specific_without_details(self):
		count=frappe.db.count("Work Order")
		with self.assertRaises(frappe.MandatoryError):self.draft(bom_no=None).insert()
		self.assertEqual(frappe.db.count("Work Order"),count)
		order=self.draft().insert()
		self.assertFalse(order.operations or order.required_items)
		before=str(order.modified)
		with self.assertRaisesRegex(frappe.ValidationError,"BOM未维护工序路线"):
			self.details(order)
		order.reload()
		self.assertEqual(str(order.modified),before)
		self.assertFalse(order.operations or order.required_items)
		self.assertFalse(frappe.db.exists("Job Card",{"work_order":order.name}))

	def test_missing_material_is_reported_without_partial_plan(self):
		frappe.set_user("Administrator")
		bom=frappe.copy_doc(frappe.get_doc("BOM",self.f.order.bom_no))
		bom.docstatus=0; bom.is_default=0; bom.with_operations=1
		for i,operation in enumerate(self.f.operations,1):
			bom.append("operations",{"operation":operation,"workstation":self.f.workstation,"time_in_mins":1,"sequence_id":i})
		bom.insert().submit()
		# Only this rollback fixture's new BOM: reproduce an incomplete upstream source, never customer data.
		frappe.db.delete("BOM Item",{"parent":bom.name})
		frappe.db.delete("BOM Explosion Item",{"parent":bom.name})
		frappe.set_user(self.f.users["operator"])
		order=self.draft(bom_no=bom.name).insert()
		with self.assertRaisesRegex(frappe.ValidationError,"BOM未维护生产用料"):
			self.details(order)
		self.assertFalse(order.reload().operations or order.required_items)

	def test_header_checks_do_not_bypass_role_or_revoked_scope(self):
		self.f.order.expected_delivery_date=None;self.f.order.save()
		for key in ("other","outsider"):
			with self.subTest(key=key),self.assertRaises(frappe.PermissionError):
				self.f.act(key,"送审")
		frappe.set_user("Administrator")
		frappe.db.delete("User Permission",{"user":self.f.users["operator"],"allow":"Department"})
		frappe.clear_cache(user=self.f.users["operator"])
		frappe.set_user(self.f.users["operator"])
		with self.assertRaises(frappe.PermissionError):self.f.act("operator","送审")
		self.assertEqual(self.f.order.reload().workflow_state,"草稿")
