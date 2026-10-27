"""Prepare a retained HTTP-only copy of the synthetic test database; never overwrite a site."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import frappe

SOURCE = "xgd-test.localhost"
TARGET = "xgd-b08-http.localhost"
DATABASE = "xgd_b08_http"
PRIVATE = Path("/tmp/b08-private")
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
PRIVATE.mkdir(exist_ok=True)
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
        config.update(allow_tests=True, pause_scheduler=True, mute_emails=True, b08_http_only=True)
        if encryption_key:
            config["encryption_key"] = encryption_key
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        config_path.chmod(0o600)
        print(json.dumps({"target": TARGET, "restored_business_tables_match": 11,
            "new_site_only": True, "source_business_records_unchanged": True}))
    finally:
        frappe.db.rollback()
        frappe.destroy()