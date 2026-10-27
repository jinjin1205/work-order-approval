"""Prepare a retained HTTP-only copy of the synthetic test database; never overwrite a site."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import frappe

SOURCE = "xgd-test.localhost"
TARGET = "xgd-b19-http.localhost"
DATABASE = "xgd_b19_http"
PRIVATE = Path("/private/b19-http")
TABLES = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log",
          "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment"]


def snapshot():
    result = {}
    for dt in TABLES:
        rows = frappe.get_all(dt, fields=["*"], order_by="name")
        result[dt] = {"count": len(rows), "sha256": hashlib.sha256(
            json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()}
    return result


def save_private(name, value):
    with (PRIVATE / name).open("x") as output:
        json.dump(value, output, ensure_ascii=False, indent=2, default=str)
        output.write("\n")


parser = argparse.ArgumentParser()
parser.add_argument("action", choices=("clone", "setup", "source-check", "copy-check", "snapshot", "ui-setup"))
parser.add_argument("--reuse-backup", action="store_true", help="Resume only after inspecting a failed clone before target creation")
args = parser.parse_args()
os.umask(0o077)
os.chdir("sites")

if args.action == "clone":
    from frappe.database.db_manager import DbManager
    from frappe.database.mariadb.setup_db import get_root_connection
    from frappe.installer import _new_site
    from frappe.utils.backups import BackupGenerator

    assert not Path(TARGET).exists(), "Target site exists; never overwrite"
    assert args.reuse_backup or not (PRIVATE / "source.sql.gz").exists(), "Backup exists; inspect previous run before retry"
    frappe.init(site=SOURCE)
    frappe.connect()
    try:
        assert frappe.conf.allow_tests and frappe.conf.db_name != DATABASE
        assert not frappe.db.exists("Workflow", {"document_type": "Work Order"})
        frappe.set_user("Administrator")
        baseline = snapshot()
        encryption_key = frappe.conf.get("encryption_key")
        root_db = get_root_connection("root", os.environ["B01_DB_PASSWORD"])
        try:
            assert DATABASE not in DbManager(root_db).get_database_list(), "Target database exists"
            assert not root_db.sql("select User from mysql.user where User=%s", (DATABASE,)), "Target database user exists"
        finally:
            root_db.close()
        if args.reuse_backup:
            assert baseline == json.loads((PRIVATE / "source-baseline.json").read_text())
            assert (PRIVATE / "source.sql.gz").stat().st_size > 0
        else:
            save_private("source-baseline.json", baseline)
            backup = BackupGenerator(frappe.conf.db_name, frappe.conf.db_name, frappe.conf.db_password,
                db_type=frappe.conf.db_type, db_host=frappe.conf.db_host, db_port=frappe.conf.db_port,
                backup_path=str(PRIVATE), backup_path_db=str(PRIVATE / "source.sql.gz"), ignore_conf=True)
            backup.get_backup(ignore_files=True, force=True)
        assert snapshot() == baseline, "Backup changed source business records"
    finally:
        frappe.db.rollback()
        frappe.destroy()
    frappe.init(site=TARGET, new_site=True)
    _new_site(db_name=DATABASE, site=TARGET, db_type="mariadb", db_host="db",
        db_root_username="root", db_root_password=os.environ["B01_DB_PASSWORD"],
        admin_password=os.environ["B01_TEST_ADMIN_PASSWORD"], source_sql=str(PRIVATE / "source.sql.gz"),
        force=False, install_apps=[], mariadb_user_host_login_scope="%")
    try:
        assert snapshot() == baseline, "Restored copy differs in the eleven business tables"
        config_path = Path(TARGET) / "site_config.json"
        config = json.loads(config_path.read_text())
        config.update(allow_tests=True, pause_scheduler=True, mute_emails=True, b19_http_only=True)
        if encryption_key:
            config["encryption_key"] = encryption_key
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        config_path.chmod(0o600)
        print(json.dumps({"target": TARGET, "restored_business_tables_match": 11,
            "new_site_only": True, "source_business_records_unchanged": True}))
    finally:
        frappe.db.rollback()
        frappe.destroy()
else:
    frappe.init(site=SOURCE if args.action == "source-check" else TARGET)
    frappe.connect()
    try:
        frappe.set_user("Administrator")
        if args.action == "source-check":
            assert snapshot() == json.loads((PRIVATE / "source-baseline.json").read_text())
            assert not frappe.db.exists("Workflow", {"document_type": "Work Order"})
            print(json.dumps({"source": SOURCE, "business_tables_unchanged": 11, "work_order_workflows": 0}))
        else:
            assert frappe.conf.b19_http_only and frappe.conf.db_name == DATABASE
            if args.action == "copy-check":
                baseline = json.loads((PRIVATE / "source-baseline.json").read_text())
                current = snapshot()
                print(json.dumps({"tables": current, "changed_tables": [dt for dt in TABLES if current[dt] != baseline[dt]],
                    "work_order_workflows": frappe.db.count("Workflow", {"document_type": "Work Order"}),
                    "private_fixture_exists": (PRIVATE / "fixture.json").exists()}))
            elif args.action == "setup":
                assert not (PRIVATE / "fixture.json").exists(), "Fixture exists; do not repeat setup"
                assert not frappe.db.exists("Workflow", {"document_type": "Work Order"})
                frappe.flags.in_test = True
                frappe.flags.skip_test_records = True
                from frappe.core.doctype.user.user import generate_keys
                from frappe.tests.utils import FrappeTestCase
                from erpnext.manufacturing.doctype.work_order.test_work_order import make_approval_execution_fixture
                from erpnext.manufacturing.doctype.work_order.work_order import create_job_card
                from erpnext.stock.doctype.stock_entry.test_stock_entry import TestStockExecutionApproval

                case = FrappeTestCase()
                fixture = make_approval_execution_fixture(case, stock=True)
                frappe.set_user("Administrator")
                frappe.get_doc("User", fixture.users["operator"]).add_roles(fixture.roles[1])
                frappe.get_doc("User", fixture.users["reviewer"]).add_roles(fixture.roles[2])
                frappe.db.set_single_value("Manufacturing Settings", "disable_capacity_planning", 1)
                users = {role: {"email": email, **generate_keys(email)} for role, email in fixture.users.items()}
                card = create_job_card(fixture.order, fixture.order.operations[0].as_dict())
                card.for_quantity = 1
                stock_case = TestStockExecutionApproval()
                stock_case.f = fixture
                direct = stock_case.transfer(fixture.order)
                indirect = stock_case.transfer(job_card=fixture.legacy_card)
                save_private("fixture.json", {"site": TARGET, "base_url": "http://127.0.0.1:18088",
                    "users": users, "order": fixture.order.name, "company": fixture.company,
                    "legacy_order": fixture.legacy_order.name, "legacy_card": fixture.legacy_card.name,
                    "legacy_timer_card": frappe.db.get_value("Job Card", {
                        "work_order": fixture.legacy_order.name, "operation": fixture.operations[1]}, "name"),
                    "raw_item": fixture.raw, "source_warehouse": fixture.order_args["source_warehouse"],
                    "wip_warehouse": fixture.wip, "job_payload": card.as_dict(),
                    "stock_payload": direct.as_dict(), "indirect_stock_payload": indirect.as_dict()})
                frappe.db.commit()
                print(json.dumps({"target": TARGET, "fixture_committed": True, "actors": len(users),
                    "pending_order": fixture.order.workflow_state, "source_site_untouched": True}))
            elif args.action == "ui-setup":
                assert not (PRIVATE / "ui-access.json").exists(), "Chinese fixture already exists; do not repeat preparation"
                from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
                from frappe.permissions import update_permission_property
                from frappe.utils.password import update_password
                import secrets

                fixture = json.loads((PRIVATE / "fixture.json").read_text())
                save_private("ui-before.json", snapshot())
                create_custom_fields({"Work Order": [dict(fieldname="previous_work_order", label="剩余需求来源工单",
                    fieldtype="Link", options="Work Order", no_copy=1)]}, update=False)
                workflow = frappe.get_doc("Workflow", "生产工单两级审批")
                assert workflow.is_active and workflow.document_type == "Work Order"
                for action in ("终止", "取消修订"):
                    if not frappe.db.exists("Workflow Action Master", action):
                        frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert()
                if not frappe.db.exists("Workflow State", "已取消"):
                    frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": "已取消"}).insert()
                if not any(row.state == "已取消" for row in workflow.states):
                    workflow.append("states", dict(state="已取消", doc_status="2", allow_edit="生产工单签批", send_email=0))
                expected = [(state, "终止", "终止", "生产工单发起", 1)
                    for state in ("草稿", "待审核", "待签批", "退回")]
                expected.append(("已批准", "取消修订", "已取消", "生产工单签批", 0))
                for state, action, target, role, own in expected:
                    if not any(row.state == state and row.action == action for row in workflow.transitions):
                        workflow.append("transitions", dict(state=state, action=action, next_state=target,
                            allowed=role, allow_self_approval=own))
                workflow.save()
                update_permission_property("Work Order", "生产工单签批", 0, "cancel", 1)
                access = {"site": TARGET, "base_url": fixture["base_url"], "users": {}}
                labels = dict(operator="操作工", reviewer="班组长", director="生产厂长", warehouse="线边仓管", other="其他班组长", outsider="无权账号")
                for role, credentials in fixture["users"].items():
                    password = secrets.token_urlsafe(24)
                    user = frappe.get_doc("User", credentials["email"])
                    user.first_name = labels[role]
                    user.language = "zh"
                    user.save()
                    update_password(user.name, password, logout_all_sessions=False)
                    access["users"][role] = {"email": user.name, "password": password}
                frappe.set_user(fixture["users"]["operator"]["email"])
                template = frappe.get_doc("Work Order", fixture["order"])
                created = []
                for _ in range(2):
                    draft = frappe.copy_doc(template, ignore_no_copy=False)
                    draft.insert()
                    assert draft.docstatus == 0 and draft.workflow_state == "草稿"
                    created.append(draft.name)
                access["draft_orders"] = created
                frappe.db.commit()
                save_private("ui-access.json", access)
                print(json.dumps({"target": TARGET, "draft_orders_created": len(created), "actors": len(access["users"]),
                    "workflow_updated_only_in_retained_synthetic_copy": True, "credentials_printed": False}))
            else:
                fixture = json.loads((PRIVATE / "fixture.json").read_text())
                result = {"order": frappe.get_doc("Work Order", fixture["order"]).as_dict(),
                    "work_order_rows": frappe.get_all("Work Order", fields=["*"], order_by="name"),
                    "legacy_tasks": [frappe.get_doc("Job Card", name).as_dict() for name in frappe.get_all(
                        "Job Card", filters={"work_order": fixture["legacy_order"]}, pluck="name")],
                    "job_cards": frappe.get_all("Job Card", filters={"work_order": fixture["order"]}, fields=["*"]),
                    "legacy_card": frappe.get_doc("Job Card", fixture["legacy_card"]).as_dict(),
                    "stock_entries": frappe.get_all("Stock Entry", filters={"work_order": ["in", [fixture["order"], fixture["legacy_order"]]]}, fields=["*"]),
                    "source_qty": frappe.db.get_value("Bin", {"item_code": fixture["raw_item"], "warehouse": fixture["source_warehouse"]}, "actual_qty"),
                    "wip_qty": frappe.db.get_value("Bin", {"item_code": fixture["raw_item"], "warehouse": fixture["wip_warehouse"]}, "actual_qty"),
                    "tables": snapshot()}
                print(frappe.as_json(result, ensure_ascii=False))
    finally:
        frappe.db.rollback()
        frappe.destroy()
