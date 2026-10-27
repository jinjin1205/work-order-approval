# Copyright (c) 2026, Contributors
# For license information, please see license.txt

import re

import frappe
from frappe.core.doctype.user_permission.user_permission import get_user_permissions
from frappe.model.document import Document

from erpnext.manufacturing.doctype.job_card.job_card import _whole_non_negative


class ProductionTimeRule(Document):
	def before_validate(self):
		if not self.company:
			frappe.throw("请选择时段规则所属公司。")
		self.check_company_scope()
		for row in self.periods:
			if row.name:
				previous = frappe.db.get_value("Production Time Period", row.name,
					["parent", "parenttype", "parentfield"], as_dict=True)
				if previous and (previous.parent != self.name or previous.parenttype != self.doctype
					or previous.parentfield != "periods"):
					frappe.throw("不能使用其他时段规则的明细行。", frappe.PermissionError)
		self.as_calculation_rule()

	def check_company_scope(self):
		if frappe.session.user == "Administrator":
			return
		allowed = _allowed_companies(frappe.session.user)
		before = self.get_doc_before_save()
		if self.company not in allowed or (before and before.company not in allowed):
			frappe.throw("没有此公司时段规则的维护授权。", frappe.PermissionError)

	def on_trash(self):
		self.check_company_scope()

	def as_calculation_rule(self):
		priority = _whole_non_negative(self.priority, "优先级")
		enabled = _whole_non_negative(self.enabled, "启用状态")
		if enabled not in (0, 1):
			frappe.throw("启用状态只能为0或1。")
		if not self.periods:
			frappe.throw("请至少填写一条休息或可加班时段。")
		rule = {"name": self.name, "rule_name": self.rule_name, "company": self.company,
			"modified": self.modified, "priority": priority, "enabled": enabled,
			"operation": self.operation or None, "rest_periods": [], "overtime_periods": []}
		for row in self.periods:
			if row.period_type not in ("Rest", "Overtime"):
				frappe.throw("时段类型必须为休息或可加班。")
			period = []
			for value in (row.start_time, row.end_time):
				match = re.fullmatch(r"([0-9]{1,2}):([0-5][0-9])(?::00(?:\.0{1,6})?)?", str(value))
				if not match or int(match[1]) > 23:
					frappe.throw("时段须使用00:00至23:59，精确到分钟，不能包含非零秒或日期。")
				period.append(f"{int(match[1]):02}:{match[2]}")
			key = "rest_periods" if row.period_type == "Rest" else "overtime_periods"
			rule[key].append(period)
		return rule


def _allowed_companies(user):
	if "生产配置管理员" not in frappe.get_roles(user):
		return []
	return [p.doc for p in get_user_permissions(user).get("Company", [])
		if p.applicable_for in (None, "", "Production Time Rule")]


def has_permission(doc, ptype, user=None, debug=False):
	user = user or frappe.session.user
	if user != "Administrator" and doc.company not in _allowed_companies(user):
		return False


def get_permission_query_conditions(user, doctype=None):
	if user == "Administrator":
		return ""
	companies = _allowed_companies(user)
	conditions = []
	if companies:
		values = ", ".join(frappe.db.escape(company, percent=False) for company in companies)
		conditions.append(f"`tabProduction Time Rule`.`company` in ({values})")
	shared = frappe.share.get_shared("Production Time Rule", user)
	if shared:
		values = ", ".join(frappe.db.escape(name, percent=False) for name in shared)
		conditions.append(f"`tabProduction Time Rule`.`name` in ({values})")
	return "(" + " or ".join(conditions) + ")" if conditions else "1=0"


def load_report_time_rules(company, operation):
	"""Internal only: caller authorizes the task and derives company/operation before this read."""
	names = frappe.get_all("Production Time Rule", filters={"company": company, "enabled": 1},
		or_filters=[["operation", "is", "not set"], ["operation", "=", operation or ""]],
		order_by="priority asc, name asc", pluck="name")
	return [frappe.get_doc("Production Time Rule", name).as_calculation_rule() for name in names]
