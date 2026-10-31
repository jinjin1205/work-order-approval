import frappe
from frappe.workflow.doctype.workflow_action.workflow_action import has_permission as native_action_permission

from erpnext.manufacturing.production_quality import _read_match


def workflow_action_query_conditions(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	match = _read_match("Work Order", user, reference_doctype="Work Order")
	return (
		"(`tabWorkflow Action`.`reference_doctype` != 'Work Order' or exists ("
		"select 1 from `tabWork Order` where `tabWork Order`.`name` = "
		"`tabWorkflow Action`.`reference_name` and (" + match + ")))"
	)


def workflow_action_permission(doc, user=None, ptype=None):
	if doc.reference_doctype != "Work Order":
		return None
	user = user or frappe.session.user
	return native_action_permission(doc, user) and frappe.has_permission(
		"Work Order", "read", doc=doc.reference_name, user=user
	)
