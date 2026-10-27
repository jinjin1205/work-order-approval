"""R05 synthetic material follow-up. Run once, only after coordinator review.
exec(open('/eval/material_followup.py').read(), {'__name__': '__main__'})
No product changes. Only normal documents, native factories and temporary settings.
"""
import hashlib
import json
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import frappe
import erpnext
from frappe.utils import now
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry, make_stock_return_entry
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry as receipt

PREFIX = "R05F-M"
OUTPUT = Path("/home/frappe/frappe-bench/sites/r05-followup-material.json")
COMPANY, UOM = "_Test Company", "R02 件"
SOURCE, WIP, FINISHED = "Stores - _TC", "_Test Warehouse - _TC", "_Test Warehouse 1 - _TC"
KG, G = PREFIX + "-kg", PREFIX + "-g"
SYSTEM = {"float_precision": "6", "rounding_method": "Commercial Rounding"}
MANUFACTURING = {
    "disable_capacity_planning": 1,
    "backflush_raw_materials_based_on": "Material Transferred for Manufacture",
    "material_consumption": 1,
    "overproduction_percentage_for_work_order": 0,
}
report = {
    "probe": PREFIX, "started_utc": datetime.now(timezone.utc).isoformat(),
    "site": frappe.local.site, "user": frappe.session.user,
    "versions": {"erpnext": erpnext.__version__, "frappe": frappe.__version__},
    "scope": "R05 return remainder and linked limit; explicit consumption; Q05 local precision; U01 cross-unit consumption",
    "limitations": [
        "Administrator CLI synthetic evaluation, not HTTP, UI, ordinary-role, concurrency or customer acceptance.",
        "No product code or business arithmetic is added; Decimal only compares observed values with fixed expected constants.",
        "Temporary settings and only our Property Setters are restored; synthetic committed documents remain as evidence.",
        "Rollback experiments are observations, not retained stock documents or proof of HTTP rollback.",
        "Configured precision is not proof of end-to-end decimal arithmetic, UI, report, export or AI consistency.",
    ],
    "cases": [], "errors": [], "mismatches": [],
}
old_system = None
old_manufacturing = None
setter_changes = []


def equal(actual, expected):
    return actual is not None and Decimal(str(actual)) == Decimal(str(expected))


def system_snapshot():
    settings = frappe.get_doc("System Settings")
    return {
        "fields": {key: settings.get(key) for key in SYSTEM},
        "defaults": {key: frappe.db.get_default(key) for key in SYSTEM},
    }


def snapshot(wo, rm):
    wo.reload()
    entries = frappe.get_all("Stock Entry", filters={"work_order": wo.name}, pluck="name", order_by="creation asc")
    return {
        "work_order": wo.as_dict(),
        "stock_entries": [frappe.get_doc("Stock Entry", name).as_dict() for name in entries],
        "bins": frappe.get_all("Bin", filters={"item_code": rm}, fields=["*"]),
        "stock_ledger": frappe.get_all("Stock Ledger Entry", filters={"item_code": rm}, fields=["*"], order_by="posting_date asc, posting_time asc, creation asc"),
        "observed": {
            "source": frappe.db.get_value("Bin", {"item_code": rm, "warehouse": SOURCE}, "actual_qty"),
            "wip": frappe.db.get_value("Bin", {"item_code": rm, "warehouse": WIP}, "actual_qty"),
            "transferred_qty": wo.required_items[0].transferred_qty,
            "returned_qty": wo.required_items[0].returned_qty,
            "consumed_qty": wo.required_items[0].consumed_qty,
            "stock_uom": wo.required_items[0].stock_uom,
        },
    }


def build_case(case, suffix, raw_per_bom, planned, initial, stock_uom=UOM, uoms=None):
    rm, fg = f"{PREFIX}-{suffix}-RM", f"{PREFIX}-{suffix}-FG"
    make_item(rm, {"is_stock_item": 1, "stock_uom": stock_uom, "valuation_method": "Moving Average"}, uoms=uoms)
    make_item(fg, {"is_stock_item": 1, "stock_uom": UOM, "valuation_method": "Moving Average"})
    bom = make_bom(item=fg, company=COMPANY, currency=frappe.get_cached_value("Company", COMPANY, "default_currency"),
                   quantity=1, raw_materials=[rm], rm_qty=raw_per_bom, rate=2,
                   source_warehouse=SOURCE, with_operations=False, do_not_save=True)
    case["bom_input"] = bom.as_dict()
    bom.insert()
    bom.submit()
    bom.reload()
    case["bom_reloaded"] = bom.as_dict()
    opening = receipt(item_code=rm, company=COMPANY, target=SOURCE, qty=initial, basic_rate=2)
    wo = make_wo_order_test_record(production_item=fg, bom_no=bom.name, qty=planned, stock_uom=UOM,
                                  source_warehouse=SOURCE, wip_warehouse=WIP, fg_warehouse=FINISHED,
                                  company=COMPANY, transfer_material_against="Work Order", planned_start_date=now(), do_not_save=True)
    wo.insert()
    wo.submit()
    wo.reload()
    case["ids"] = {"raw_item": rm, "finished_item": fg, "bom": bom.name, "work_order": wo.name, "opening_stock": opening.name}
    case["work_order_after_submit"] = wo.as_dict()
    return wo, rm, bom


def return_first(case, wo, qty):
    doc = make_stock_return_entry(wo.name)
    case["first_return_factory_before_input"] = doc.as_dict() if doc else None
    if doc is None or len(doc.items) != 1:
        raise AssertionError("First native return must have one row for the isolated one-item work order")
    doc.company = wo.company
    doc.items[0].cost_center = frappe.get_cached_value("Company", wo.company, "cost_center")
    doc.items[0].qty = qty
    doc.submit()
    doc.reload()
    case["first_return_reloaded"] = doc.as_dict()
    return doc


def consumption(wo, rm, qty, uom, factor):
    """Normal new Stock Entry form inputs; native validation calculates stock qty/rates/ledger."""
    doc = frappe.new_doc("Stock Entry")
    doc.update({"company": COMPANY, "purpose": "Material Consumption for Manufacture", "work_order": wo.name,
                "from_bom": 1, "bom_no": wo.bom_no, "fg_completed_qty": wo.qty, "from_warehouse": WIP})
    doc.set_stock_entry_type()
    doc.append("items", {"item_code": rm, "s_warehouse": WIP, "qty": qty,
                         "uom": uom, "conversion_factor": factor})
    doc.submit()
    doc.reload()
    return doc


def return_experiment(case, label, wo, rm, first_return, qty, extra_wip=0):
    """Each branch starts from a committed baseline, always rolls back its own input."""
    branch = {"input": {"return_qty": qty, "other_stock_receipt_to_wip": extra_wip}, "expected": "reject" if extra_wip else "accept"}
    case[label] = branch
    try:
        if extra_wip:
            other = receipt(item_code=rm, company=COMPANY, target=WIP, qty=extra_wip, basic_rate=2)
            branch["other_stock_document"] = other.as_dict()
        branch["before"] = snapshot(wo, rm)
        doc = frappe.copy_doc(first_return)
        doc.docstatus = 0
        branch["action"] = "Copy submitted return into a new draft, explicitly set docstatus=0, enter requested quantity, normal submit"
        doc.items[0].qty = qty
        branch["submitted_input"] = doc.as_dict()
        doc.submit()
        branch["outcome"] = "accepted"
        branch["after_attempt"] = snapshot(wo, rm)
    except Exception as exc:
        branch["outcome"] = "rejected"
        branch["exception_type"] = type(exc).__name__
        branch["exception_message"] = str(exc)
        branch["traceback"] = traceback.format_exc()
    finally:
        frappe.db.rollback()
        frappe.clear_document_cache("Work Order", wo.name)
        branch["after_rollback"] = snapshot(wo, rm)
        branch["transaction"] = "rolled_back; branch documents and stock effects not retained"
    return branch


def case_returns(case):
    case["input"] = {"planned": 10, "raw_per_bom": 1, "initial": 20, "issue": 10, "first_return": 2, "measured_consumption": 7}
    wo, rm, bom = build_case(case, "RET", 1, 10, 20)
    transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10))
    transfer.submit()
    first_return = return_first(case, wo, 2)
    case["baseline"] = snapshot(wo, rm)
    generated = make_stock_return_entry(wo.name)
    case["second_return_factory_unmodified"] = generated.as_dict() if generated else None
    frappe.db.commit()
    case["baseline_checkpoint"] = "committed: isolated opening, issue 10 and return 2 retained"
    correct = return_experiment(case, "manual_remaining_8", wo, rm, first_return, 8)
    over = return_experiment(case, "over_return_9_with_other_stock_10", wo, rm, first_return, 9, extra_wip=10)
    doc = consumption(wo, rm, 7, UOM, 1)
    case["explicit_consumption_document"] = doc.as_dict()
    case["after_consumption"] = snapshot(wo, rm)
    after_factory = make_stock_return_entry(wo.name)
    case["return_factory_after_consumption_unmodified"] = after_factory.as_dict() if after_factory else None
    facts = case["after_consumption"]["observed"]
    rows = case["second_return_factory_unmodified"].get("items", []) if generated else []
    case["checks"] = {
        "factory_single_remaining_8": len(rows) == 1 and equal(rows[0].get("qty"), 8) and rows[0].get("s_warehouse") == WIP and rows[0].get("t_warehouse") == SOURCE,
        "manual_second_return_8_accepted": correct["outcome"] == "accepted",
        "manual_return_8_source_20_wip_0": correct.get("after_attempt", {}).get("observed", {}).get("source") == 20 and equal(correct.get("after_attempt", {}).get("observed", {}).get("wip"), 0),
        "linked_over_return_rejected_despite_sufficient_warehouse_stock": over["outcome"] == "rejected",
        "branch_rollback_source_12_wip_8": all(equal(over["after_rollback"]["observed"][key], value) for key, value in {"source":12,"wip":8,"returned_qty":2}.items()),
        "explicit_consumption_7_wip_1_source_12": equal(facts["consumed_qty"], 7) and equal(facts["wip"], 1) and equal(facts["source"], 12),
    }
    case["interpretation"] = "Source 12, issued 10 and returned 2 describe material transfer. Only the separately submitted consumption entry supplies explicit consumption 7; remaining WIP 1 is a stock location fact, not a cause or responsibility finding."


def set_precision(doctype, fieldname, value):
    filters = {"doc_type": doctype, "field_name": fieldname, "property": "precision"}
    existing = frappe.get_all("Property Setter", filters=filters, fields=["name", "value"])
    if existing:
        raise RuntimeError(f"Pre-existing precision Property Setter: {existing}; abort instead of replacing unrelated configuration")
    before = frappe.get_meta(doctype).get_field(fieldname).precision
    doc = make_property_setter(doctype, fieldname, "precision", str(value), "Int")
    setter_changes.append({"doctype": doctype, "field": fieldname, "name": doc.name, "before_meta_precision": before})
    frappe.db.commit()
    frappe.clear_cache(doctype=doctype)
    return {"name": doc.name, "doctype": doctype, "field": fieldname, "before": before, "configured": frappe.get_meta(doctype).get_field(fieldname).precision}


def restore_setters():
    restored = []
    for change in reversed(setter_changes):
        if frappe.db.exists("Property Setter", change["name"]):
            doc = frappe.get_doc("Property Setter", change["name"])
            if doc.doc_type != change["doctype"] or doc.field_name != change["field"] or doc.property != "precision":
                raise RuntimeError("Property Setter identity changed; refusing to delete unrelated configuration")
            frappe.delete_doc("Property Setter", change["name"])
        frappe.clear_cache(doctype=change["doctype"])
        restored.append({**change, "after_meta_precision": frappe.get_meta(change["doctype"]).get_field(change["field"]).precision,
                         "setter_absent": not frappe.db.exists("Property Setter", change["name"])})
    frappe.db.commit()
    report["property_setters_restored"] = restored
    if not all(row["setter_absent"] and row["after_meta_precision"] == row["before_meta_precision"] for row in restored):
        raise RuntimeError("Property Setter restoration mismatch")


def case_q05(case):
    case["input"] = {"planned": 3, "raw_per_bom": "0.000050", "expected_intermediate": "0.000150", "expected_final": "0.0002"}
    case["configuration"] = [set_precision("Work Order Item", "required_qty", 4)]
    wo, rm, bom = build_case(case, "Q05", 0.000050, 3, 1)
    case["precision"] = {"bom_qty": bom.items[0].precision("qty"), "bom_stock_qty": bom.items[0].precision("stock_qty"), "work_order_required": wo.required_items[0].precision("required_qty")}
    case["work_order_database_row"] = frappe.db.get_value("Work Order Item", wo.required_items[0].name, ["required_qty", "stock_uom"], as_dict=True)
    first = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 3))
    case["stock_factory_with_work_order_precision_only"] = first.as_dict()
    # Record the work-order-only candidate before expanding configuration to stock fields.
    frappe.db.commit()
    case["baseline_checkpoint"] = "committed: Q05 BOM, Work Order and opening stock; no generated transfer submitted yet"
    case["configuration"].append(set_precision("Stock Entry Detail", "qty", 4))
    case["configuration"].append(set_precision("Stock Entry Detail", "transfer_qty", 4))
    stock = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 3))
    case["stock_factory_with_stock_precision"] = stock.as_dict()
    stock.insert()
    stock.submit()
    stock.reload()
    wo.reload()
    case["stock_reloaded"] = stock.as_dict()
    case["stock_database_row"] = frappe.db.get_value("Stock Entry Detail", stock.items[0].name, ["qty", "transfer_qty", "uom", "stock_uom", "conversion_factor"], as_dict=True)
    case["after_stock"] = snapshot(wo, rm)
    case["checks"] = {
        "bom_input_retained": equal(bom.items[0].qty, "0.00005") and equal(bom.items[0].stock_qty, "0.00005"),
        "work_order_metadata_precision_4": case["precision"]["work_order_required"] == 4,
        "work_order_stored_required_is_target_0002": equal(case["work_order_database_row"].required_qty, "0.0002"),
        "stock_qty_target_0002": equal(stock.items[0].qty, "0.0002") and equal(stock.items[0].transfer_qty, "0.0002"),
        "stock_wip_target_0002": equal(case["after_stock"]["observed"]["wip"], "0.0002"),
        "wo_required_and_transferred_same": equal(wo.required_items[0].required_qty, wo.required_items[0].transferred_qty),
    }


def case_u01(case):
    case["input"] = {"stock_unit": KG, "alternative_unit": G, "conversion": "1 kg = 1000 g; g to stock kg factor 0.001", "issue_kg": "0.001", "return_kg": "0.0004", "net_kg": "0.0006", "explicit_consumption_g": "0.5", "expected_consumption_kg": "0.0005", "expected_wip_after_consumption_kg": "0.0001"}
    for unit in (KG, G):
        if frappe.db.exists("UOM", unit):
            raise RuntimeError("Synthetic UOM already exists; no reuse or deletion")
        frappe.get_doc({"doctype": "UOM", "uom_name": unit, "must_be_whole_number": 0}).insert()
    wo, rm, bom = build_case(case, "U01", 0.001, 1, 1, stock_uom=KG,
                             uoms=[{"uom": KG, "conversion_factor": 1}, {"uom": G, "conversion_factor": 0.001}])
    transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
    transfer.submit()
    transfer.reload()
    case["transfer_reloaded"] = transfer.as_dict()
    return_first(case, wo, 0.0004)
    case["after_issue_and_return"] = snapshot(wo, rm)
    case["consumption_input"] = {"uom": G, "qty": 0.5, "conversion_factor": 0.001, "stock_uom": KG}
    doc = consumption(wo, rm, 0.5, G, 0.001)
    case["consumption_reloaded"] = doc.as_dict()
    case["after_consumption"] = snapshot(wo, rm)
    generated = make_stock_return_entry(wo.name)
    case["return_factory_after_cross_unit_consumption"] = generated.as_dict() if generated else None
    net = case["after_issue_and_return"]["observed"]
    facts = case["after_consumption"]["observed"]
    case["checks"] = {
        "issue_stock_qty_0001": equal(transfer.items[0].transfer_qty, "0.001"),
        "return_stock_qty_00004": equal(net["returned_qty"], "0.0004"),
        "net_wip_00006": equal(net["wip"], "0.0006"),
        "consumption_stock_qty_00005": equal(doc.items[0].transfer_qty, "0.0005"),
        "ledger_wip_00001": equal(facts["wip"], "0.0001"),
        "work_order_consumed_stock_qty_00005": equal(facts["consumed_qty"], "0.0005"),
        "work_order_consumed_matches_entry_stock_qty": equal(facts["consumed_qty"], doc.items[0].transfer_qty),
    }


if OUTPUT.exists():
    raise RuntimeError("Exclusive evidence output already exists; use an explicitly reviewed new attempt")
try:
    if frappe.local.site != "r05.localhost" or frappe.session.user != "Administrator":
        raise RuntimeError("Restricted to Administrator at isolated r05.localhost")
    for doctype, name in [("Company", COMPANY), ("UOM", UOM), ("Item Group", "Products"), ("Warehouse", SOURCE), ("Warehouse", WIP), ("Warehouse", FINISHED)]:
        if not frappe.db.exists(doctype, name):
            raise RuntimeError(f"Missing preexisting fixture: {doctype} {name}")
    if frappe.get_all("Item", filters={"item_code": ["like", PREFIX + "%"]}, pluck="name"):
        raise RuntimeError("Synthetic item prefix already exists; historical records will not be reused or deleted")
    report["source_git_blobs"] = {}
    for name in ["apps/erpnext/erpnext/manufacturing/doctype/work_order/work_order.py", "apps/erpnext/erpnext/manufacturing/doctype/work_order/work_order.js", "apps/erpnext/erpnext/stock/doctype/stock_entry/stock_entry.py", "apps/erpnext/erpnext/stock/doctype/stock_entry/stock_entry.js", "apps/frappe/frappe/custom/doctype/property_setter/property_setter.py"]:
        data = (Path("/home/frappe/frappe-bench") / name).read_bytes()
        report["source_git_blobs"][name] = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    old_system = system_snapshot()
    old_manufacturing = {key: frappe.db.get_single_value("Manufacturing Settings", key) for key in MANUFACTURING}
    report["system_before"] = old_system
    report["manufacturing_before"] = old_manufacturing
    settings = frappe.get_doc("System Settings")
    settings.update(SYSTEM)
    settings.save()
    frappe.db.set_single_value("Manufacturing Settings", dict(MANUFACTURING))
    frappe.db.commit()
    report["system_during"] = system_snapshot()
    report["manufacturing_during"] = {key: frappe.db.get_single_value("Manufacturing Settings", key) for key in MANUFACTURING}
    for label, action in [("return_and_explicit_consumption", case_returns), ("Q05_local_property_precision", case_q05), ("U01_cross_unit_consumption", case_u01)]:
        case = {"case": label}
        report["cases"].append(case)
        try:
            action(case)
            frappe.db.commit()
            case["transaction"] = "committed except explicitly labelled rollback experiments"
            case["status"] = "checks_match" if all(case["checks"].values()) else "target_mismatch"
            if case["status"] == "target_mismatch":
                report["mismatches"].append(label)
        except Exception:
            frappe.db.rollback()
            case["transaction"] = "current transaction rolled back; any explicitly labelled earlier baseline checkpoint remains committed"
            case["status"] = "error"
            case["traceback"] = traceback.format_exc()
            report["errors"].append(label)
        finally:
            if label == "Q05_local_property_precision":
                restore_setters()  # Must restore stock precision before U01.
except Exception:
    frappe.db.rollback()
    report["setup_or_control_error"] = traceback.format_exc()
    report["errors"].append("setup_or_control")
finally:
    # Restore independent configuration groups even if another group fails.
    for group in ("property_setters", "manufacturing", "system"):
        try:
            if group == "property_setters":
                restore_setters()
            elif group == "manufacturing" and old_manufacturing is not None:
                frappe.db.set_single_value("Manufacturing Settings", dict(old_manufacturing))
            elif group == "system" and old_system is not None:
                settings = frappe.get_doc("System Settings")
                settings.update(old_system["fields"])
                settings.save()
                for key, value in old_system["defaults"].items():
                    frappe.db.set_default(key, value)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            report[group + "_restore_error"] = traceback.format_exc()
            report["errors"].append(group + "_restore_error")
    try:
        report["system_after"] = system_snapshot()
        report["manufacturing_after"] = {key: frappe.db.get_single_value("Manufacturing Settings", key) for key in MANUFACTURING}
        report["settings_restored"] = report["system_after"] == old_system and report["manufacturing_after"] == old_manufacturing
        if old_system is not None and not report["settings_restored"]:
            report["errors"].append("settings_restore_mismatch")
    except Exception:
        report["restore_readback_error"] = traceback.format_exc()
        report["errors"].append("restore_readback_error")
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["status"] = "execution_errors" if report["errors"] else ("executed_with_target_mismatches" if report["mismatches"] else "executed_quantity_subset_only")
    with OUTPUT.open("x", encoding="utf-8") as result:
        json.dump(report, result, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({"status": report["status"], "output": str(OUTPUT), "errors": report["errors"], "mismatches": report["mismatches"]}, ensure_ascii=False))
if report["errors"]:
    raise RuntimeError("R05 material follow-up execution errors; inspect preserved evidence JSON")
