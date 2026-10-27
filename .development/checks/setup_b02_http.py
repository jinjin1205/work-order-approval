"""Prepare, restore or revoke only the synthetic B02 HTTP fixture on the test site."""
import argparse
import json
import os
from pathlib import Path

import frappe
from frappe.core.doctype.user.user import generate_keys

SITE = "xgd-test.localhost"
PRIVATE_FILE = Path("/private/b02-http.json")


def business_snapshot(data):
    return {
        "work_orders": [frappe.db.get_value("Work Order", name,
                        ["name", "docstatus", "qty", "produced_qty"], as_dict=True)
                        for name in data["orders"]],
        "job_cards": [frappe.db.get_value("Job Card", name,
                      ["name", "docstatus", "total_completed_qty", "total_time_in_mins"], as_dict=True)
                      for name in data["cards"]],
        "time_logs": frappe.db.count("Job Card Time Log", {"parent": ["in", data["cards"]]}),
        "stock_entries": frappe.db.count("Stock Entry"),
    }


parser = argparse.ArgumentParser()
parser.add_argument("action", choices=("setup", "restore", "revoke"))
args = parser.parse_args()

if args.action == "setup" and PRIVATE_FILE.exists():
    raise SystemExit("B02 credentials already exist; refusing to replace the fixture")

os.chdir("sites")
frappe.init(site=SITE)
frappe.connect()
try:
    assert frappe.local.site == SITE and frappe.conf.get("allow_tests")
    frappe.set_user("Administrator")
    if args.action == "setup":
        from erpnext.manufacturing.doctype.job_card.test_job_card import TestJobCardReadPermissions

        frappe.flags.in_test = True
        fixture = TestJobCardReadPermissions("test_read_fixture_and_authorized_helpers")
        fixture.setUp()
        frappe.set_user("Administrator")
        users = {}
        for actor, user in (("reader", fixture.reader), ("outsider", fixture.outsider)):
            users[actor] = {"email": user.name, **generate_keys(user.name)}
        data = {
            "site": SITE,
            "base_url": "http://127.0.0.1:18087",
            "prefix": fixture.prefix,
            "role": fixture.role,
            "users": users,
            "orders": [order.name for order in fixture.orders],
            "cards": [card.name for card in fixture.cards],
            "operations": fixture.operations,
            "operation_rows": [order.operations[0].name for order in fixture.orders],
        }
        # Exclusive local output: a failed setup is retained for review, never overwritten.
        descriptor = os.open(PRIVATE_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        frappe.db.commit()
        public = {key: value for key, value in data.items() if key != "users"}
        public["users"] = {
            actor: {
                "email": user["email"],
                "explicit_roles": [row.role for row in frappe.get_doc("User", user["email"]).roles],
            }
            for actor, user in users.items()
        }
        print(frappe.as_json({"action": "setup", "fixture": public, "business_state": business_snapshot(data)},
                            ensure_ascii=False, indent=2))
    else:
        data = json.loads(PRIVATE_FILE.read_text())
        assert data["site"] == SITE and data["prefix"].startswith("B02-")
        assert data["role"] == data["prefix"]
        email = data["users"]["reader"]["email"]
        assert email == data["prefix"].lower() + "@example.invalid"
        user = frappe.get_doc("User", email)
        original_roles = [row.role for row in user.roles]
        if args.action == "restore":
            assert data["role"] not in original_roles, "Fixture role already present; inspect prior evidence"
            user.append("roles", {"role": data["role"]})
        else:
            assert data["role"] in original_roles, "Fixture role is already absent; inspect prior evidence"
            user.set("roles", [{"role": role} for role in original_roles if role != data["role"]])
        user.save()
        frappe.db.commit()
        print(frappe.as_json({
            "action": args.action, "site": SITE, "email": email,
            "changed_role": data["role"], "explicit_roles": [row.role for row in user.roles],
            "api_token_changed": False, "business_state": business_snapshot(data),
        }, ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
