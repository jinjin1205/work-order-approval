import json
import os
import sys
import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from frappe.utils.password import update_password

site = sys.argv[1]
company, abbr = {"xgd-dev.localhost": ("小工单开发验证公司", "XGD"), "xgd-test.localhost": ("小工单自动测试公司", "XGT")}[site]
os.chdir("sites")
frappe.init(site=site)
frappe.connect()
try:
    frappe.set_user("Administrator")
    frappe.conf.trigger_site_setup_in_background = False
    result = setup_complete({"language": "简体中文", "lang": "简体中文", "country": "China", "timezone": "Asia/Shanghai", "currency": "CNY", "company_name": company, "company_abbr": abbr, "fy_start_date": "2026-01-01", "fy_end_date": "2026-12-31", "chart_of_accounts": "Standard", "setup_demo": 0, "enable_telemetry": 0})
    assert result == {"status": "ok"}, result
    settings = frappe.get_single("System Settings")
    settings.language = "zh"
    settings.date_format = "yyyy-mm-dd"
    settings.time_format = "HH:mm:ss"
    settings.enable_telemetry = 0
    settings.save()
    administrator = frappe.get_doc("User", "Administrator")
    administrator.language = "zh"
    administrator.time_zone = "Asia/Shanghai"
    administrator.save()
    if site == "xgd-dev.localhost":
        role = "B01 登录验证"
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert()
        email = "b01.operator@example.invalid"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "中文环境验证员", "enabled": 1, "language": "zh", "time_zone": "Asia/Shanghai", "send_welcome_email": 0, "roles": [{"role": role}]}).insert()
            update_password(email, os.environ["B01_OPERATOR_PASSWORD"])
        user = frappe.get_doc("User", email)
        assert user.user_type == "System User"
        assert not any(row.role == "System Manager" for row in user.roles)
    frappe.db.commit()
    frappe.clear_cache()
    settings = frappe.get_single("System Settings")
    output = {"site": site, "setup_complete": frappe.is_setup_complete(), "system": {k: settings.get(k) for k in ["language", "country", "time_zone", "currency", "date_format", "time_format", "float_precision", "rounding_method"]}, "company": frappe.db.get_value("Company", company, ["name", "default_currency", "country"], as_dict=True)}
    assert output["system"]["language"] == "zh"
    assert output["system"]["time_zone"] == "Asia/Shanghai"
    assert output["company"]["default_currency"] == "CNY"
    print(json.dumps(output, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
