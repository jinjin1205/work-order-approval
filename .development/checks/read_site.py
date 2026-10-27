import json
import os
import sys
import frappe

site = sys.argv[1]
assert site in {"xgd-dev.localhost", "xgd-test.localhost"}
os.chdir("sites")
frappe.init(site=site)
frappe.connect()
try:
    system = frappe.get_single("System Settings")
    user = frappe.get_doc("User", "b01.operator@example.invalid") if site == "xgd-dev.localhost" else None
    result = {"site": site, "database_name": frappe.conf.db_name, "allow_tests": bool(frappe.conf.get("allow_tests")), "system": {k: system.get(k) for k in ["language", "country", "currency", "time_zone", "date_format", "time_format", "float_precision", "rounding_method"]}, "companies": frappe.get_all("Company", fields=["name", "default_currency", "country"]), "work_orders": frappe.db.count("Work Order"), "job_cards": frappe.db.count("Job Card"), "stock_entries": frappe.db.count("Stock Entry")}
    if user:
        result["login_fixture"] = {"email": user.name, "user_type": user.user_type, "language": user.language, "time_zone": user.time_zone, "explicit_roles": [row.role for row in user.roles]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
