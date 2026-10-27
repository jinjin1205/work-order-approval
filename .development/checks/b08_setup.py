"""Persist only the already-tested synthetic fixture on the new B08-only site."""
import json
import os
from pathlib import Path
import frappe
from frappe.core.doctype.user.user import generate_keys
from frappe.utils.password import update_password

os.umask(0o077)
os.chdir('sites')
private = Path('/tmp/b08-private')
assert not (private/'fixture.json').exists(), 'Do not repeat fixture creation'
frappe.init(site='xgd-b08-http.localhost')
frappe.connect()
try:
    assert frappe.conf.b08_http_only
    frappe.flags.in_test = True
    frappe.flags.skip_test_records = True
    from erpnext.manufacturing.doctype.job_card.test_job_card import TestProductionReportConfirmation
    case = TestProductionReportConfirmation()
    case.setUp()
    frappe.set_user('Administrator')
    import secrets
    password = secrets.token_urlsafe(24)
    update_password(case.user, password)
    keys = generate_keys(case.user)
    value = dict(site=frappe.local.site,base_url='http://127.0.0.1:18090', user=case.user, password=password,
        keys=keys, order=case.order.name, operation_id=case.operation_id,
        forbidden_operation=case.order.operations[1].name, employee=case.employee,plans=case.plan_names)
    (private/'fixture.json').write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n')
    frappe.db.commit()
    print(json.dumps(dict(synthetic_fixture_saved=True,plan=10,plan_cards=3,ordinary_report_role=True,work_order_write=False)))
finally:
    frappe.db.rollback()
    frappe.destroy()
