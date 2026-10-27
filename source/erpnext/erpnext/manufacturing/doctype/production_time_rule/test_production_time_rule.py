# Copyright (c) 2026, Contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.permissions import add_user_permission



class TestProductionTimeRule(FrappeTestCase):

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(self.cleanup)
		self.prefix = "b14-" + frappe.generate_hash(length=8)
		self.company = self.other_company()
		self.user = self.make_user("config", ["生产配置管理员"])
		add_user_permission("Company", self.company, self.user)
		frappe.defaults.set_user_default("company", self.company, user=self.user)

	def cleanup(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.clear_cache()

	def make_user(self, suffix, roles):
		user = self.prefix + "-" + suffix + "@example.invalid"
		frappe.get_doc({"doctype": "User", "email": user, "first_name": "时段验收",
			"language": "zh", "send_welcome_email": 0,
			"roles": [{"role": role} for role in roles]}).insert()
		return user

	def make_rule(self, **changes):
		return frappe.get_doc({"doctype": "Production Time Rule", "rule_name": "午休与加班",
			"company": self.company, "enabled": 1, "priority": 1,
			"periods": [{"period_type": "Rest", "start_time": "12:00:00", "end_time": "13:00:00"},
				{"period_type": "Overtime", "start_time": "16:00:00", "end_time": "17:00:00"}], **changes})

	def test_minimum_fixture_save_reload(self):
		frappe.set_user(self.user)
		doc = self.make_rule().insert().reload()
		self.assertEqual(doc.company, self.company)
		self.assertEqual(len(doc.periods), 2)
		self.assertEqual(str(doc.periods[0].start_time), "12:00:00")
		doc.priority = 2
		doc.save(ignore_version=False)
		self.assertTrue(frappe.db.exists("Version", {"ref_doctype": doc.doctype, "docname": doc.name}))

	def other_company(self):
		return frappe.get_doc({"doctype": "Company", "company_name": self.prefix + "-" + frappe.generate_hash(length=5),
			"abbr": frappe.generate_hash(length=5), "default_currency": "CNY", "country": "China"}).insert().name

	def loader(self):
		from erpnext.manufacturing.doctype.production_time_rule import production_time_rule
		method = getattr(production_time_rule, "load_report_time_rules", None)
		self.assertTrue(callable(method), "B14 internal rule loader is not implemented")
		return method

	def test_invalid_configuration_is_rejected_before_save(self):
		frappe.set_user(self.user)
		for values in ({"priority": -1}, {"priority": "not-a-number"}, {"priority": 0.5},
			{"enabled": 2}, {"enabled": "invalid"}):
			with self.subTest(values=values), self.assertRaises(frappe.ValidationError):
				self.make_rule(**values).insert()
		for value in ("25:00:00", "-1:00:00", "12:00:01", "12:00:00.500", "2026-10-27 12:00:00"):
			with self.subTest(time=value), self.assertRaises(frappe.ValidationError):
				doc = self.make_rule()
				doc.periods[0].start_time = value
				doc.insert()

	def test_native_mandatory_and_type_validation_remains(self):
		frappe.set_user(self.user)
		self.assertEqual(self.make_rule(company=None).insert().company, self.company)
		with self.assertRaises(frappe.ValidationError):
			self.make_rule(periods=[]).insert()
		with self.assertRaises(frappe.PermissionError):
			self.make_rule(company="").insert()
		doc = self.make_rule()
		doc.periods[0].period_type = "Unknown"
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_saved_rules_feed_existing_calculation(self):
		from erpnext.manufacturing.doctype.job_card.job_card import calculate_report_time
		load = self.loader()
		frappe.set_user(self.user)
		doc = self.make_rule().insert().reload()
		rules = load(self.company, None)
		self.assertEqual([r["name"] for r in rules], [doc.name])
		result = calculate_report_time("2026-10-20 09:00:00", "2026-10-20 17:00:00", rules=rules)
		self.assertEqual(result["effective_seconds"], 25200)
		result = calculate_report_time("2026-10-20 09:00:00", "2026-10-20 17:00:00", rules=rules,
			shutdown_seconds=3600, overtime_seconds=1800)
		self.assertEqual(result["effective_seconds"], 23400)
		doc.periods[0].start_time = "23:00:00"
		doc.periods[0].end_time = "01:00:00"
		doc.save()
		result = calculate_report_time("2026-10-20 22:00:00", "2026-10-21 02:00:00", rules=load(self.company, None))
		self.assertEqual(result["effective_seconds"], 7200)
		doc.periods[0].start_time = "00:00:00"
		doc.save().reload()
		self.assertEqual(load(self.company, None)[0]["rest_periods"], [["00:00", "01:00"]])

	def test_unscoped_config_role_is_not_factory_wide(self):
		from frappe.client import get, get_list
		doc = self.make_rule().insert()
		user = self.make_user("unscoped", ["生产配置管理员"])
		frappe.set_user(user)
		self.assertEqual(get_list("Production Time Rule", fields=["name"]), [])
		with self.assertRaises(frappe.PermissionError):
			get("Production Time Rule", doc.name)
		with self.assertRaises(frappe.PermissionError):
			self.make_rule().insert()

	def test_cross_company_and_company_change_are_rejected(self):
		from frappe.client import get, get_list
		other = self.other_company()
		foreign = self.make_rule(company=other).insert()
		own = self.make_rule().insert()
		frappe.set_user(self.user)
		self.assertEqual([r.name for r in get_list("Production Time Rule", fields=["name"])], [own.name])
		with self.assertRaises(frappe.PermissionError):
			get("Production Time Rule", foreign.name)
		own.company = other
		with self.assertRaises(frappe.PermissionError):
			own.save()
		foreign.company = self.company
		with self.assertRaises(frappe.PermissionError):
			foreign.save()

	def test_removing_last_company_permission_does_not_open_access(self):
		from frappe.client import get, get_list
		from frappe.permissions import remove_user_permission
		frappe.set_user(self.user)
		doc = self.make_rule().insert()
		frappe.set_user("Administrator")
		remove_user_permission("Company", self.company, self.user)
		frappe.set_user(self.user)
		self.assertEqual(get_list("Production Time Rule", fields=["name"]), [])
		with self.assertRaises(frappe.PermissionError):
			get("Production Time Rule", doc.name)
		doc.priority = 9
		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_role_revocation_and_shared_document_are_limited(self):
		from frappe.client import get, get_list
		import frappe.share
		one, two = self.make_rule().insert(), self.make_rule().insert()
		viewer = self.make_user("shared", [])
		frappe.share.add("Production Time Rule", one.name, user=viewer, read=1)
		frappe.set_user(viewer)
		self.assertEqual(get("Production Time Rule", one.name).name, one.name)
		self.assertEqual([r.name for r in get_list("Production Time Rule", fields=["name"])], [one.name])
		with self.assertRaises(frappe.PermissionError):
			get("Production Time Rule", two.name)
		with self.assertRaises(frappe.PermissionError):
			self.make_rule().insert()
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.user).remove_roles("生产配置管理员")
		frappe.set_user(self.user)
		with self.assertRaises(frappe.PermissionError):
			get("Production Time Rule", two.name)

	def test_child_queries_do_not_leak_other_company(self):
		from frappe.client import get, get_list
		own = self.make_rule().insert()
		foreign = self.make_rule(company=self.other_company()).insert()
		frappe.set_user(self.user)
		rows = get_list("Production Time Period", parent="Production Time Rule", fields=["name", "parent"])
		self.assertEqual({row.parent for row in rows}, {own.name})
		with self.assertRaises(frappe.PermissionError):
			get("Production Time Period", foreign.periods[0].name, parent="Production Time Rule")

	def test_internal_reader_is_complete_scoped_and_not_public(self):
		load = self.loader()
		operation = frappe.get_doc({"doctype": "Operation", "__newname": self.prefix + "-本道"}).insert().name
		other_op = frappe.get_doc({"doctype": "Operation", "__newname": self.prefix + "-其他"}).insert().name
		one = self.make_rule(priority=1).insert()
		two = self.make_rule(priority=2, operation=operation).insert()
		self.make_rule(operation=other_op).insert()
		self.make_rule(enabled=0).insert()
		self.make_rule(company=self.other_company()).insert()
		add_user_permission("Production Time Rule", two.name, self.user)
		frappe.set_user(self.user)
		self.assertEqual([r["name"] for r in load(self.company, operation)], [one.name, two.name])
		with self.assertRaises(frappe.PermissionError):
			frappe.is_whitelisted(load)
		frappe.set_user("Administrator")
		frappe.db.set_value("Production Time Rule", one.name, "priority", -1)
		with self.assertRaises(frappe.ValidationError):
			load(self.company, operation)

	def test_no_rules_is_explicit(self):
		self.assertEqual(self.loader()(self.company, None), [])

	def test_native_chinese_translations(self):
		for text, expected in (("Production Time Rule", "报工时段规则"),
			("Production Time Period", "报工规则时段"), ("Rest", "休息"), ("Overtime", "可加班")):
			self.assertEqual(frappe._(text, lang="zh"), expected)

	def test_parent_cannot_adopt_foreign_existing_period(self):
		other = self.other_company()
		foreign = self.make_rule(company=other).insert()
		frappe.set_user(self.user)
		own = self.make_rule().insert()
		own.periods[0].name = foreign.periods[0].name
		with self.assertRaises(frappe.PermissionError):
			own.save()

	def test_direct_child_writes_require_parent_rule(self):
		from frappe.client import save
		frappe.set_user(self.user)
		for action in ("save", "insert", "delete"):
			with self.subTest(action=action):
				parent = self.make_rule().insert()
				child = frappe.get_doc("Production Time Period", parent.periods[0].name)
				with self.assertRaises(frappe.PermissionError):
					if action == "save":
						child.start_time = "12:00:01"
						save(child.as_dict())
					elif action == "insert":
						frappe.get_doc({"doctype": child.doctype, "parent": parent.name,
							"parenttype": parent.doctype, "parentfield": "periods",
							"period_type": "Rest", "start_time": "12:00:01", "end_time": "13:00:00"}).insert()
					else:
						frappe.delete_doc(child.doctype, child.name)

	def test_parent_period_edit_and_delete_remain_native(self):
		frappe.set_user(self.user)
		doc = self.make_rule().insert()
		doc.periods[0].end_time = "14:00:00"
		doc.save(ignore_version=False).reload()
		self.assertEqual(str(doc.periods[0].end_time), "14:00:00")
		self.assertTrue(frappe.db.exists("Version", {"ref_doctype": doc.doctype, "docname": doc.name}))
		frappe.delete_doc(doc.doctype, doc.name)
		self.assertFalse(frappe.db.exists("Production Time Period", {"parent": doc.name}))
