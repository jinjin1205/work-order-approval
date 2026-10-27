"""Retain synthetic B14 configuration only on the isolated test site."""
import json
import os
import secrets
from pathlib import Path
import frappe
import erpnext
from frappe.permissions import add_user_permission
from frappe.utils.password import update_password
os.umask(0o077)
private = Path('/private/b14-ui')
os.chdir('sites')
frappe.init(site='xgd-test.localhost')
frappe.connect()
try:
    assert frappe.conf.allow_tests
    assert not frappe.db.exists('Workflow', {'document_type': 'Work Order'})
    frappe.set_user('Administrator')
    if (private / 'access.json').exists():
        access = json.loads((private / 'access.json').read_text())
        assert frappe.db.exists('User', access['user'])
        print(json.dumps({'reused': True}))
    else:
        user = 'b14.config@example.invalid'
        assert not frappe.db.exists('User', user)
        password = secrets.token_urlsafe(24)
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': '时段配置验收员',
            'language': 'zh', 'time_zone': 'Asia/Shanghai', 'send_welcome_email': 0,
            'roles': [{'role': '生产配置管理员'}]}).insert()
        update_password(user, password)
        company = erpnext.get_default_company()
        add_user_permission('Company', company, user)
        access = {'user': user, 'password': password, 'company': company,
            'site': frappe.local.site, 'base_url': 'http://127.0.0.1:18089'}
        frappe.db.commit()
        (private / 'access.json').write_text(json.dumps(access, ensure_ascii=False))
        print(json.dumps({'created': True, 'ordinary_config_role': True, 'company_scope': True,
            'business_records_created': 0, 'workflow_activated': False}))
finally:
    frappe.db.rollback()
    frappe.destroy()
