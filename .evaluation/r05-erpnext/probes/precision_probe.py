"""One-shot R02 Q02/Q04/Q05 native BOM -> saved Work Order probe.

Run only in the already-connected r05.localhost console:
exec(open('/eval/precision_probe.py').read(), {'__name__': '__main__'})
This is a synthetic evaluation script, not product code or full CASE-02 acceptance.
"""
import json
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import frappe
from frappe.utils import now
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.stock.doctype.item.test_item import make_item

PREFIX = "R02-ERPNext-20261026-P"
OUTPUT = Path("/home/frappe/frappe-bench/sites/r05-precision-result.json")
COMPANY = "_Test Company"
UOM = "R02 件"
SOURCE = "Stores - _TC"
WIP = "_Test Warehouse - _TC"
FINISHED = "_Test Warehouse 1 - _TC"
SETTINGS = {"float_precision": "6", "rounding_method": "Commercial Rounding"}
INPUTS = [
    {"id": "Q02", "planned": 100, "raw_per_bom": "0.083333", "expected_required": "8.3333"},
    {"id": "Q04", "planned": 100, "raw_per_bom": "0.000167", "expected_required": "0.0167"},
    {"id": "Q05", "planned": 3, "raw_per_bom": "0.00005", "expected_required": "0.0002"},
]
report = {
    "probe": PREFIX,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "site": frappe.local.site,
    "user": frappe.session.user,
    "scope": "R02 CASE-02 Q02/Q04/Q05: native BOM submit and Work Order draft insert/reload only",
    "limitations": [
        "No stock entry, inventory posting, unit conversion, UI, export, AI or permission acceptance.",
        "Six-place system precision is an evaluated configuration, not proof of full decimal arithmetic.",
        "Inputs are passed numerically without manual rounding; required_qty is compared directly with the fixed R02 expectation.",
        "Decimal is used only for equality against fixed expected values, never to calculate or overwrite native quantities.",
        "Successful and mismatching cases commit; exceptional cases roll back. Work Orders remain drafts.",
    ],
    "cases": [],
}
old_settings = None
errors = []
mismatches = []


def settings_snapshot():
    doc = frappe.get_doc("System Settings")
    return {
        "fields": {key: doc.get(key) for key in SETTINGS},
        "defaults": {key: frappe.db.get_default(key) for key in SETTINGS},
    }


def execute_case(case, values):
    rm, fg = f"{PREFIX}-{values['id']}-RM", f"{PREFIX}-{values['id']}-FG"
    case["input"] = {**values, "bom_base": 1, "loss": 0, "uom": UOM}
    case["settings"] = settings_snapshot()
    for code in (rm, fg):
        make_item(code, {"is_stock_item": 1, "stock_uom": UOM, "valuation_method": "Moving Average"})
    bom = make_bom(
        item=fg, company=COMPANY,
        currency=frappe.get_cached_value("Company", COMPANY, "default_currency"),
        quantity=1, raw_materials=[rm], rm_qty=float(values["raw_per_bom"]),
        rate=2, source_warehouse=SOURCE, with_operations=False, do_not_save=True,
    )
    case["bom_before_insert"] = bom.as_dict()
    bom.insert()
    bom.submit()
    bom.reload()
    case["bom_reloaded"] = bom.as_dict()
    if len(bom.items) != 1 or bom.items[0].item_code != rm:
        raise AssertionError("Expected exactly the specified raw material in the native BOM")
    case["bom_field_precision"] = {
        field: bom.items[0].precision(field) for field in ("qty", "stock_qty")
    }
    case["bom_database_row"] = frappe.db.get_value(
        "BOM Item", bom.items[0].name, ["qty", "stock_qty", "conversion_factor", "uom", "stock_uom"], as_dict=True,
    )
    wo = make_wo_order_test_record(
        production_item=fg, bom_no=bom.name, qty=values["planned"], stock_uom=UOM,
        source_warehouse=SOURCE, wip_warehouse=WIP, fg_warehouse=FINISHED,
        company=COMPANY, transfer_material_against="Work Order",
        planned_start_date=now(), do_not_save=True,
    )
    case["work_order_before_insert"] = wo.as_dict()
    wo.insert()
    wo.reload()
    case["work_order_reloaded"] = wo.as_dict()
    if len(wo.required_items) != 1 or wo.required_items[0].item_code != rm:
        raise AssertionError("Expected exactly the specified raw material in the saved Work Order")
    row = wo.required_items[0]
    case["required_qty_field_precision"] = row.precision("required_qty")
    case["work_order_database_row"] = frappe.db.get_value(
        "Work Order Item", row.name, ["item_code", "required_qty", "stock_uom"], as_dict=True,
    )
    case["ids"] = {"raw_item": rm, "finished_item": fg, "bom": bom.name, "work_order": wo.name}
    case["observed_required_qty"] = row.required_qty
    case["checks"] = {
        "bom_input_preserved": Decimal(str(bom.items[0].qty)) == Decimal(values["raw_per_bom"]),
        "saved_required_matches_fixed_R02_expected": Decimal(str(row.required_qty)) == Decimal(values["expected_required"]),
        "database_required_matches_reloaded_document": (
            Decimal(str(case["work_order_database_row"].required_qty)) == Decimal(str(row.required_qty))
        ),
        "work_order_is_draft": wo.docstatus == 0,
    }


if OUTPUT.exists():
    raise RuntimeError("Result file already exists; preserve it and use an explicitly separate run")

try:
    if frappe.local.site != "r05.localhost" or frappe.session.user != "Administrator":
        raise RuntimeError("Probe is restricted to Administrator in isolated r05.localhost")
    for doctype, name in [("Company", COMPANY), ("UOM", UOM), ("Item Group", "Products"),
                          ("Warehouse", SOURCE), ("Warehouse", WIP), ("Warehouse", FINISHED)]:
        if not frappe.db.exists(doctype, name):
            raise RuntimeError(f"Required fixture is missing: {doctype} {name}")
    if frappe.get_cached_value("UOM", UOM, "must_be_whole_number"):
        raise RuntimeError("The fixture UOM must permit fractional quantities")
    if frappe.get_all("Item", filters={"item_code": ["like", PREFIX + "%"]}, pluck="name"):
        raise RuntimeError("Synthetic prefix already exists; existing records will not be reused or deleted")
    report["settings_before"] = settings_snapshot()
    old_settings = dict(report["settings_before"]["fields"])
    settings = frappe.get_doc("System Settings")
    settings.update(SETTINGS)
    settings.save()  # Native on_update syncs defaults and invalidates system_settings cache.
    frappe.db.commit()
    report["settings_during"] = settings_snapshot()
    for values in INPUTS:
        case = {"case": "CASE-02", "subcase": values["id"]}
        report["cases"].append(case)
        try:
            execute_case(case, values)
            frappe.db.commit()
            case["transaction"] = "committed"
            case["status"] = "quantity_checks_match" if all(case["checks"].values()) else "quantity_mismatch"
            if case["status"] == "quantity_mismatch":
                mismatches.append(values["id"])
        except Exception:
            frappe.db.rollback()
            case["transaction"] = "rolled_back; intermediate observations are not retained documents"
            case["status"] = "error"
            case["traceback"] = traceback.format_exc()
            errors.append(values["id"])
except Exception:
    frappe.db.rollback()
    report["setup_error"] = traceback.format_exc()
    errors.append("setup")
finally:
    if old_settings is not None:
        try:
            settings = frappe.get_doc("System Settings")
            settings.update(old_settings)
            settings.save()
            for key, value in report["settings_before"]["defaults"].items():
                frappe.db.set_default(key, value)
            frappe.db.commit()
            report["settings_after"] = settings_snapshot()
            report["settings_restored"] = report["settings_after"] == report["settings_before"]
            if not report["settings_restored"]:
                errors.append("settings restore mismatch")
        except Exception:
            frappe.db.rollback()
            report["settings_restore_error"] = traceback.format_exc()
            errors.append("settings restore error")
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["errors"] = errors
    report["mismatches"] = mismatches
    report["status"] = "errors" if errors else ("executed_with_mismatches" if mismatches else "executed_quantity_subset_only")
    with OUTPUT.open("x", encoding="utf-8") as result_file:
        json.dump(report, result_file, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({"status": report["status"], "output": str(OUTPUT), "errors": errors, "mismatches": mismatches}))

if errors or mismatches:
    raise RuntimeError("Precision probe recorded errors or target mismatches; inspect the preserved JSON result")
