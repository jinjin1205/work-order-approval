"""One-shot CASE-01/06 probe; exec(open('/eval/r02_probe.py').read()) in r05 console.
Requires upstream fixtures. Each successful case commits; a failed case rolls back
with traceback. No product modification, ordinary-role test, or evidence overwrite.
"""
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
import frappe
PREFIX = "R02-ERPNext-20261026-A"
OUTPUT = Path("/home/frappe/frappe-bench/sites/r05-r02-result-attempt2.json")
COMPANY = "_Test Company"
UOM = "R02 件"
SOURCE = "Stores - _TC"
WIP = "_Test Warehouse - _TC"
FINISHED = "_Test Warehouse 1 - _TC"
SETTINGS = {
    "disable_capacity_planning": 1,
    "backflush_raw_materials_based_on": "Material Transferred for Manufacture",
    "material_consumption": 0,
    "overproduction_percentage_for_work_order": 0,
}
report = {
    "probe": PREFIX,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "site": frappe.local.site,
    "user": frappe.session.user,
    "scope": "CASE-01 integer inventory chain and CASE-06 issue/return/draft only",
    "limitations": [
        "Native document/factory quantity subset only; no UI, ordinary-role permission or generation-workflow acceptance.",
        "Employee omitted; execution-date time logs; no payroll or CASE-03 result.",
        "Manufacture input derives from transferred quantities, not measured consumption; unsubmitted draft is not approval-workflow acceptance.",
        "No retry/concurrency, precision, AI, mobile or customer-deployment claim.",
    ],
    "cases": [],
}
old_settings = None
errors = []

def step(case, label, action):
    entry = {"action": label, "status": "started"}
    case["steps"].append(entry)
    value = action()  # Errors propagate to the case boundary and are never treated as success.
    entry["output"] = value.as_dict() if hasattr(value, "as_dict") else value
    entry["status"] = "executed_pending_case_commit"
    return value

def snapshot(wo, rm, fg):
    """Read native facts without implementing a second inventory calculation."""
    wo.reload()
    cards = frappe.get_all("Job Card", filters={"work_order": wo.name}, pluck="name")
    return {
        "work_order": wo.as_dict(),
        "job_cards": [frappe.get_doc("Job Card", name).as_dict() for name in cards],
        "stock_entries": frappe.get_all(
            "Stock Entry", filters={"work_order": wo.name},
            fields=["name", "docstatus", "purpose", "is_return", "fg_completed_qty"],
            order_by="creation asc",
        ),
        "bins": frappe.get_all("Bin", filters={"item_code": ["in", [rm, fg]]}, fields=["*"]),
        "stock_ledger": frappe.get_all(
            "Stock Ledger Entry", filters={"item_code": ["in", [rm, fg]]}, fields=["*"],
            order_by="posting_date asc, posting_time asc, creation asc",
        ),
        "observed": {
            "raw_source": frappe.db.get_value("Bin", {"item_code": rm, "warehouse": SOURCE}, "actual_qty"),
            "raw_wip": frappe.db.get_value("Bin", {"item_code": rm, "warehouse": WIP}, "actual_qty"),
            "finished_stock": frappe.db.get_value("Bin", {"item_code": fg, "warehouse": FINISHED}, "actual_qty"),
        },
    }

def build_case(case, scope, rm_qty, operation_count):
    from frappe.utils import now
    from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
    from erpnext.manufacturing.doctype.routing.test_routing import create_routing, setup_operations
    from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
    from erpnext.stock.doctype.item.test_item import make_item
    from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry as receipt
    rm, fg = f"{PREFIX}-{scope}-RM", f"{PREFIX}-{scope}-FG"
    for item in (rm, fg):
        step(case, f"create Item {item}", lambda item=item: make_item(item, {
            "is_stock_item": 1, "stock_uom": UOM, "valuation_method": "Moving Average",
        }))
    route_name = None
    if operation_count:
        operations = [{
            "operation": f"{PREFIX}-{scope}-OP-{index}",
            "workstation": f"{PREFIX}-{scope}-WS-{index}",
            "time_in_mins": 1, "sequence_id": index,
        } for index in range(1, operation_count + 1)]
        step(case, "create synthetic operations/workstations", lambda: setup_operations(operations))
        route = step(case, "create Routing", lambda: create_routing(
            routing_name=f"{PREFIX}-{scope}-ROUTE", operations=operations,
        ))
        route_name = route.name
    bom = make_bom(
        item=fg, company=COMPANY,
        currency=frappe.get_cached_value("Company", COMPANY, "default_currency"),
        quantity=1, raw_materials=[rm], rm_qty=rm_qty, rate=2,
        source_warehouse=SOURCE, routing=route_name, with_operations=bool(operation_count),
        do_not_save=True,
    )
    step(case, "BOM.insert with normal permissions", bom.insert)
    step(case, "BOM.submit", bom.submit)
    step(case, "native Material Receipt: raw initial stock 20 at rate 2", lambda: receipt(
        item_code=rm, target=SOURCE, company=COMPANY, qty=20, basic_rate=2,
    ))
    wo = make_wo_order_test_record(
        production_item=fg, bom_no=bom.name, qty=10, stock_uom=UOM,
        source_warehouse=SOURCE, wip_warehouse=WIP, fg_warehouse=FINISHED,
        company=COMPANY, transfer_material_against="Work Order",
        planned_start_date=now(), do_not_save=True,
    )
    step(case, "Work Order.insert from native factory", wo.insert)
    step(case, "Work Order.submit (native Job Card creation)", wo.submit)
    case["ids"] = {"raw_item": rm, "finished_item": fg, "bom": bom.name, "work_order": wo.name}
    case["initial"] = snapshot(wo, rm, fg)
    return wo, rm, fg

def case01(case):
    from frappe.utils import add_to_date, now
    from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
    case["input"] = {"planned_fg": 10, "raw_initial": 20, "bom_qty": 1, "raw_per_bom": 0.5, "operations": 3}
    wo, rm, fg = build_case(case, "C01", 0.5, 3)
    transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
    step(case, "transfer for 10 FG: generated raw quantity must be inspected", transfer.submit)
    case["after_transfer"] = snapshot(wo, rm, fg)
    cards = frappe.get_all("Job Card", filters={"work_order": wo.name},
                           fields=["name", "sequence_id"], order_by="sequence_id asc, creation asc")
    if len(cards) != 3:
        raise AssertionError(f"Expected 3 native Job Cards, got {len(cards)}")
    for row in cards:
        card = frappe.get_doc("Job Card", row.name)
        start = now()
        card.append("time_logs", {"from_time": start, "to_time": add_to_date(start, minutes=1), "completed_qty": 10})
        step(case, f"submit Job Card {card.name} with completed_qty=10", card.submit)
    case["after_job_cards_before_manufacture"] = snapshot(wo, rm, fg)
    manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
    step(case, "submit Manufacture for 10 FG", manufacture.submit)
    case["final"] = snapshot(wo, rm, fg)
    values = case["final"]["observed"]
    case["quantity_checks"] = {
        "source_15": values["raw_source"] == 15,
        "wip_0": values["raw_wip"] == 0,
        "fg_10": values["finished_stock"] == 10,
        "work_order_produced_10": wo.produced_qty == 10,
        "three_operation_completed_10": len(wo.operations) == 3 and all(row.completed_qty == 10 for row in wo.operations),
    }

def case06(case):
    from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry, make_stock_return_entry
    case["input"] = {"planned_fg": 10, "raw_initial": 20, "raw_per_bom": 1, "issue": 10, "return": 2, "draft_issue": 3}
    wo, rm, fg = build_case(case, "C06", 1, 0)
    transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
    step(case, "submit raw transfer 10 to WIP", transfer.submit)
    case["after_issue"] = snapshot(wo, rm, fg)
    def submit_return():
        returned = make_stock_return_entry(wo.name)
        if returned is None:
            raise RuntimeError("Native make_stock_return_entry returned no document")
        if len(returned.items) != 1 or returned.items[0].item_code != rm:
            raise AssertionError("Unexpected native return rows; inspect the recorded input")
        case["native_return_before_edit"] = returned.as_dict()
        returned.items[0].qty = 2
        return returned.submit()
    step(case, "native return: change only requested qty to 2, submit", submit_return)
    case["after_return"] = snapshot(wo, rm, fg)
    def save_draft():
        draft = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 3))
        if len(draft.items) != 1 or draft.items[0].qty != 3:
            case["native_draft_before_save"] = draft.as_dict()
            raise AssertionError("Native pending transfer did not generate raw qty 3")
        return draft.insert()
    step(case, "save unsubmitted transfer 3 (docstatus=0)", save_draft)
    case["final"] = snapshot(wo, rm, fg)
    row = wo.required_items[0]
    values = case["final"]["observed"]
    case["quantity_checks"] = {
        "source_12": values["raw_source"] == 12,
        "wip_8": values["raw_wip"] == 8,
        "cumulative_transferred_10": row.transferred_qty == 10,
        "cumulative_returned_2": row.returned_qty == 2,
        "native_consumed_field_0": row.consumed_qty == 0,
        "no_manufactured_qty": wo.produced_qty == 0,
    }
    case["consumption_interpretation"] = "No consumption/manufacture document was submitted; native consumed_qty=0 is not evidence of measured actual consumption zero."

if OUTPUT.exists():
    raise RuntimeError("Result file already exists; preserve it before an explicitly separate run")
    if not frappe.db.exists("UOM", UOM):
        frappe.get_doc({"doctype": "UOM", "uom_name": UOM, "must_be_whole_number": 0}).insert()
        frappe.db.commit()
    report["uom_mapping"] = {"fixture": "U-PC", "native": UOM, "must_be_whole_number": 0}

try:
    if frappe.local.site != "r05.localhost":
        raise RuntimeError("Probe is restricted to r05.localhost")
    for doctype, name in [("Company", COMPANY), ("UOM", UOM), ("Item Group", "Products"),
                          ("Warehouse", SOURCE), ("Warehouse", WIP), ("Warehouse", FINISHED)]:
        if not frappe.db.exists(doctype, name):
            raise RuntimeError(f"Required upstream fixture is missing: {doctype} {name}")
    if frappe.get_cached_value("UOM", UOM, "must_be_whole_number"):
        raise RuntimeError("The selected upstream UOM requires integers and cannot represent raw qty 0.5")
    if frappe.get_all("Item", filters={"item_code": ["like", PREFIX + "%"]}, pluck="name"):
        raise RuntimeError("Synthetic prefix already exists; no records will be deleted or reused")
    old_settings = {name: frappe.db.get_single_value("Manufacturing Settings", name) for name in SETTINGS}
    report["manufacturing_settings_before"] = old_settings
    report["manufacturing_settings_during"] = SETTINGS
    report["system_settings"] = {
        name: frappe.db.get_single_value("System Settings", name)
        for name in ["float_precision", "rounding_method", "time_zone"]
    }
    frappe.db.set_single_value("Manufacturing Settings", SETTINGS)
    frappe.db.commit()
    for label, action in [("CASE-01", case01), ("CASE-06", case06)]:
        current = {"case": label, "steps": []}
        report["cases"].append(current)
        try:
            action(current)
            frappe.db.commit()
            current["transaction"] = "committed"
            current["status"] = "quantity_checks_match" if all(current["quantity_checks"].values()) else "quantity_mismatch"
            if current["status"] == "quantity_mismatch":
                errors.append(label + ": quantity mismatch")
        except Exception:
            frappe.db.rollback()
            current["status"] = "error"
            current["transaction"] = "rolled_back; earlier step outputs are observations, not retained documents"
            current["traceback"] = traceback.format_exc()
            errors.append(label + ": exception; see traceback")
except Exception:
    frappe.db.rollback()
    report["setup_error"] = traceback.format_exc()
    errors.append("setup error")
finally:
    if old_settings is not None:
        try:
            frappe.db.set_single_value("Manufacturing Settings", old_settings)
            frappe.db.commit()
            report["manufacturing_settings_restored"] = True
        except Exception:
            frappe.db.rollback()
            report["settings_restore_error"] = traceback.format_exc()
            errors.append("settings restore error")
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["errors"] = errors
    report["status"] = "executed_quantity_subset_only" if not errors else "errors_or_mismatches"
    # Exclusive creation preserves evidence from any previous invocation.
    with OUTPUT.open("x", encoding="utf-8") as result_file:
        json.dump(report, result_file, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({"status": report["status"], "output": str(OUTPUT), "errors": errors}, ensure_ascii=False))

if errors:
    raise RuntimeError("R02 probe has errors or mismatches; inspect sites/r05-r02-result.json")
