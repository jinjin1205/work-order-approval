"""One I06 correction interruption, controlled savepoint rollback, and recovery.

This is a database test, not an HTTP rollback or response-loss test. It reuses
the original fixture by composition and never runs its existing test methods or
FrappeTestCase.setUpClass (which commits). All fixture writes are rolled back.
Only the final safe summary is printed; identifiers and raw output stay private.
"""
import contextlib
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
import unittest
from unittest.mock import patch
import uuid

import erpnext
import frappe


PRIVATE = Path("/tmp/b08-recovery-controlled-private")
MANIFEST = Path("/b01/b08-recovery-source-manifest.json")
BUSINESS = ["Work Order", "Work Order Item", "Work Order Operation", "Job Card", "Job Card Time Log",
            "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry", "Workflow Action", "Version", "Comment"]
SECURITY = ["User", "Role", "Has Role", "User Permission", "Custom DocPerm"]
EXTRA = ["Employee", "Production Time Rule", "Production Time Period", "Workstation"]
STOCK = ["Stock Entry", "Stock Entry Detail", "Stock Ledger Entry"]
AUDIT = {"modified", "modified_by"}
ORDER_DERIVED = {"actual_operating_cost", "total_operating_cost", "actual_start_date", "actual_end_date", "lead_time", "status"}
OPERATION_DERIVED = {"completed_qty", "process_loss_qty", "actual_operation_time", "actual_start_time",
                     "actual_end_time", "status", "actual_operating_cost"}
RUN_DIR = None
CHECKS = {}


def canonical(value):
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     default=str, separators=(",", ":")).encode()).hexdigest()


def write_private(name, value):
    with (RUN_DIR / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")


def source_state():
    manifest = json.loads(MANIFEST.read_text())
    root = Path(erpnext.__file__).resolve().parent.parent
    actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in manifest["files"]}
    assert len(actual) == 33 and actual == manifest["files"], "Runtime does not match the required 33-file manifest"
    return {"manifest_file_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            "manifest": manifest, "runtime_files": actual, "runtime_files_match": True,
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "erpnext_version": erpnext.__version__, "frappe_version": frappe.__version__}


def rows(doctype, filters=None, columns=None):
    columns = columns or sorted(frappe.db.get_table_columns(doctype))
    return canonical(frappe.get_all(doctype, filters=filters, fields=columns, order_by="name", limit_page_length=0))


def capture_tables(doctypes, prior=None):
    captured = {}
    for doctype in doctypes:
        columns = prior[doctype]["columns"] if prior else sorted(frappe.db.get_table_columns(doctype))
        captured[doctype] = {"columns": columns,
                             "rows": {row["name"]: digest(row) for row in rows(doctype, columns=columns)}}
    return captured


def retention(before, after):
    return {doctype: {"old_rows": len(value["rows"]),
                      "missing": len(set(value["rows"]) - set(after[doctype]["rows"])),
                      "changed": sum(name in after[doctype]["rows"] and saved != after[doctype]["rows"][name]
                                     for name, saved in value["rows"].items()),
                      "new_rows": len(set(after[doctype]["rows"]) - set(value["rows"]))}
            for doctype, value in before.items()}


def task_state(order_name):
    order = frappe.get_doc("Work Order", order_name)
    cards = rows("Job Card", {"work_order": order_name})
    return {"order": canonical(order.as_dict()), "cards": cards,
            "logs": rows("Job Card Time Log", {"parent": ["in", [row["name"] for row in cards]]}),
            "global_cards": rows("Job Card"), "global_logs": rows("Job Card Time Log"),
            "stock": capture_tables(STOCK),
            "cost_precisions": {row.name: row.precision("actual_operating_cost") for row in order.operations}}


def without(value, excluded):
    return {key: item for key, item in value.items() if key not in excluded}


def order_invariants(order, operation_id):
    fixed = without(order, AUDIT | ORDER_DERIVED | {"operations"})
    for key, value in fixed.items():
        if isinstance(value, list):
            fixed[key] = [without(row, AUDIT) if isinstance(row, dict) else row for row in value]
    fixed["operations"] = [without(row, AUDIT | (OPERATION_DERIVED if row["name"] == operation_id else set()))
                           for row in order["operations"]]
    return fixed


class InjectedCorrectionFailure(RuntimeError):
    """Observable test-only interruption after cancel and insert, before submit."""


class TestCorrectionRollback(unittest.TestCase):
    def setUp(self):
        from erpnext.manufacturing.doctype.job_card.test_job_card import TestProductionReportConfirmation

        # Composition deliberately avoids inherited test discovery and class-level commits.
        self.fixture = TestProductionReportConfirmation("test_full_correction_retains_original_rule_and_fact")
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_correction_cancel_insert_failure_rolls_back_then_same_key_recovers(self):
        from frappe.permissions import update_permission_property
        from erpnext.manufacturing.doctype.job_card.job_card import JobCard

        fixture = self.fixture
        frappe.set_user("Administrator")
        update_permission_property("Job Card", "生产报工", 0, "cancel", 1)
        frappe.set_user(fixture.user)
        self.assertFalse(frappe.has_permission("Work Order", "write", doc=fixture.order))
        self.assertFalse(frappe.has_permission("Stock Entry", "create"))
        self.assertTrue(frappe.has_permission("Job Card", "cancel"))
        previous_context = getattr(frappe.local, "production_report_context", None)
        original_key = frappe.generate_hash(length=32)
        original_name = fixture.report(10, 0, request_id=original_key)["name"]
        self.assertIs(getattr(frappe.local, "production_report_context", None), previous_context)
        correction_key = frappe.generate_hash(length=32)
        reason = "合成验收：更正中断回滚后按原请求恢复"
        before = task_state(fixture.order.name)
        before_tables = capture_tables(BUSINESS + SECURITY + EXTRA)
        write_private("before-interruption.json", {"state": before, "tables": before_tables,
                                                  "original_key": original_key, "correction_key": correction_key})
        original = next(row for row in before["cards"] if row["name"] == original_name)
        original_logs = [row for row in before["logs"] if row["parent"] == original_name]
        operation = next(row for row in before["order"]["operations"] if row["name"] == fixture.operation_id)
        self.assertEqual((original["docstatus"], original["total_completed_qty"], original["process_loss_qty"]), (1, 10, 0))
        self.assertEqual((operation["completed_qty"], operation["status"], operation["actual_operation_time"]), (10, "Completed", 60))
        self.assertEqual(len(original_logs), 1)
        self.assertEqual(len(fixture.plan_names), 3)
        self.assertEqual(before["order"]["qty"], 10)
        observed = {}

        def interrupt_before_submit(card):
            # These assertions prove the requested DB-visible interruption point was reached.
            self.assertEqual(card.report_request_id, correction_key)
            self.assertEqual(card.amended_from, original_name)
            self.assertIs(frappe.local.production_report_context.card, card)
            self.assertEqual(frappe.db.get_value("Job Card", original_name, "docstatus"), 2)
            self.assertEqual(frappe.db.get_value("Job Card", card.name, "docstatus"), 0)
            new_logs = rows("Job Card Time Log", {"parent": card.name})
            self.assertEqual(len(new_logs), 1)
            self.assertEqual(new_logs[0]["completed_qty"], 8)
            interrupted = task_state(fixture.order.name)
            current_operation = next(row for row in interrupted["order"]["operations"] if row["name"] == fixture.operation_id)
            self.assertEqual((current_operation["completed_qty"], current_operation["process_loss_qty"],
                              current_operation["actual_operation_time"], current_operation["status"]), (0, 0, 0, "Pending"))
            self.assertNotEqual(interrupted["order"], before["order"])
            self.assertEqual(interrupted["stock"], before["stock"])
            observed.update(card=card.name, logs=[row["name"] for row in new_logs])
            write_private("observed-interruption.json", interrupted)
            raise InjectedCorrectionFailure("I06_AFTER_CANCEL_AND_INSERT_BEFORE_SUBMIT")

        frappe.db.savepoint("b08_correction_interruption")
        with patch.object(JobCard, "submit", interrupt_before_submit):
            with self.assertRaisesRegex(InjectedCorrectionFailure, "I06_AFTER_CANCEL_AND_INSERT_BEFORE_SUBMIT"):
                fixture.method("correct_production_report")(original_name, correction_key, 8, 0, reason)
        self.assertTrue(observed)
        self.assertIs(getattr(frappe.local, "production_report_context", None), previous_context)
        # Explicit test-harness rollback: this does not claim HTTP automatic rollback.
        frappe.db.rollback(save_point="b08_correction_interruption")
        rolled_back = task_state(fixture.order.name)
        rolled_back_tables = capture_tables(BUSINESS + SECURITY + EXTRA, before_tables)
        write_private("after-savepoint-rollback.json", {"state": rolled_back, "tables": rolled_back_tables})
        self.assertEqual(rolled_back, before)
        self.assertEqual(rolled_back_tables, before_tables)
        self.assertFalse(frappe.db.exists("Job Card", {"report_request_id": correction_key}))
        self.assertFalse(frappe.db.exists("Job Card", observed["card"]))
        self.assertTrue(all(not frappe.db.exists("Job Card Time Log", name) for name in observed["logs"]))
        self.assertIsNone(fixture.method("get_production_report_result")(correction_key))
        self.assertIs(getattr(frappe.local, "production_report_context", None), previous_context)
        CHECKS["interruption_and_rollback"] = {"passed": True, "original_cancelled_observed": True,
            "replacement_draft_and_time_row_observed": True, "changed_derivation_observed": True,
            "exception": "InjectedCorrectionFailure", "rollback": "explicit controlled DB savepoint",
            "all_20_table_snapshots_restored": True, "original_all_fields_time_rows_and_snapshots_restored": True,
            "replacement_key_and_partial_rows_absent": True, "request_context_restored": True,
            "before_state_sha256": digest(before), "after_rollback_state_sha256": digest(rolled_back)}

        # Patch has been removed. Recover exactly once using the same original/key/content.
        result = fixture.method("correct_production_report")(original_name, correction_key, 8, 0, reason)
        self.assertIs(getattr(frappe.local, "production_report_context", None), previous_context)
        recovered = task_state(fixture.order.name)
        write_private("after-same-key-recovery.json", {"state": recovered, "result": result})
        corrected = next(row for row in recovered["cards"] if row["name"] == result["name"])
        cancelled = next(row for row in recovered["cards"] if row["name"] == original_name)
        self.assertNotEqual(corrected["name"], original_name)
        self.assertEqual((corrected["docstatus"], corrected["amended_from"], corrected["total_completed_qty"], corrected["process_loss_qty"]), (1, original_name, 8, 0))
        self.assertEqual((cancelled["docstatus"], cancelled["total_completed_qty"], cancelled["process_loss_qty"]), (2, 10, 0))
        self.assertEqual(without(cancelled, AUDIT | {"docstatus", "status"}), without(original, AUDIT | {"docstatus", "status"}))
        cancelled_logs = [row for row in recovered["logs"] if row["parent"] == original_name]
        self.assertEqual([without(row, AUDIT | {"docstatus"}) for row in cancelled_logs],
                         [without(row, AUDIT | {"docstatus"}) for row in original_logs])
        self.assertTrue(all(row["docstatus"] == 2 for row in cancelled_logs))
        self.assertEqual(corrected["owner"], fixture.user)
        self.assertEqual(corrected["report_request_id"], correction_key)
        self.assertEqual(corrected["report_metrics_context"], original["report_metrics_context"])
        original_context = frappe.parse_json(original["report_time_context"])
        new_context = frappe.parse_json(corrected["report_time_context"])
        self.assertEqual(new_context["original_report"], original_name)
        self.assertEqual(without(new_context, {"confirmed_at", "original_report", "rule_basis"}),
                         without(original_context, {"confirmed_at"}))
        self.assertEqual(corrected["report_effective_seconds"], original["report_effective_seconds"])
        new_logs = [row for row in recovered["logs"] if row["parent"] == corrected["name"]]
        self.assertEqual(len(new_logs), 1)
        self.assertEqual((new_logs[0]["employee"], new_logs[0]["from_time"], new_logs[0]["to_time"],
                          new_logs[0]["completed_qty"], new_logs[0]["time_in_mins"], new_logs[0]["docstatus"]),
                         (fixture.employee, original_logs[0]["from_time"], original_logs[0]["to_time"], 8, 60, 1))
        self.assertEqual(corrected["total_time_in_mins"], 60)
        self.assertEqual(order_invariants(recovered["order"], fixture.operation_id), order_invariants(before["order"], fixture.operation_id))
        after_operation = next(row for row in recovered["order"]["operations"] if row["name"] == fixture.operation_id)
        self.assertEqual((after_operation["completed_qty"], after_operation["process_loss_qty"], after_operation["status"],
                          after_operation["actual_operation_time"]), (8, 0, "Work in Progress", 60))
        self.assertEqual(recovered["order"]["qty"] - after_operation["completed_qty"] - after_operation["process_loss_qty"], 2)
        self.assertEqual(recovered["order"]["status"], "In Process")
        self.assertEqual((after_operation["actual_start_time"], recovered["order"]["actual_start_date"]), (new_logs[0]["from_time"],) * 2)
        self.assertEqual((after_operation["actual_end_time"], recovered["order"]["actual_end_date"]), (new_logs[0]["to_time"],) * 2)
        self.assertEqual(recovered["order"]["lead_time"], 60)
        expected_cost = operation["hour_rate"] * 60 / 60
        precision = recovered["cost_precisions"][fixture.operation_id]
        self.assertTrue(math.isclose(after_operation["actual_operating_cost"], expected_cost, rel_tol=0, abs_tol=0.5 * 10 ** -precision))
        self.assertTrue(math.isclose(recovered["order"]["actual_operating_cost"], sum(row["actual_operating_cost"] for row in recovered["order"]["operations"]), abs_tol=1e-6))
        expected_total = recovered["order"]["additional_operating_cost"] + (recovered["order"]["actual_operating_cost"] or recovered["order"]["planned_operating_cost"]) + recovered["order"]["corrective_operation_cost"]
        self.assertTrue(math.isclose(recovered["order"]["total_operating_cost"], expected_total, abs_tol=1e-6))
        self.assertEqual(recovered["stock"], before["stock"])
        # Preserve all plan/other cards, and require exactly one replacement and one new log globally.
        before_cards = {row["name"]: row for row in before["global_cards"]}
        after_cards = {row["name"]: row for row in recovered["global_cards"]}
        self.assertEqual(set(after_cards) - set(before_cards), {corrected["name"]})
        self.assertTrue(all(after_cards.get(name) == row for name, row in before_cards.items() if name != original_name))
        before_logs = {row["name"]: row for row in before["global_logs"]}
        after_logs = {row["name"]: row for row in recovered["global_logs"]}
        self.assertEqual(set(after_logs) - set(before_logs), {new_logs[0]["name"]})
        old_log_names = {row["name"] for row in original_logs}
        self.assertTrue(all(after_logs.get(name) == row for name, row in before_logs.items() if name not in old_log_names))
        before_orphans = {row["name"] for row in before["global_logs"] if row["parent"] not in before_cards}
        after_orphans = {row["name"] for row in recovered["global_logs"] if row["parent"] not in after_cards}
        self.assertEqual(after_orphans, before_orphans)
        self.assertTrue(all(row["parent"] in after_cards for row in new_logs))
        self.assertEqual(frappe.db.count("Job Card", {"report_request_id": correction_key}), 1)
        self.assertEqual(frappe.db.count("Job Card", {"work_order": fixture.order.name, "docstatus": 1, "report_request_id": ["is", "set"]}), 1)
        found = fixture.method("get_production_report_result")(correction_key)
        self.assertEqual((found["name"], found["docstatus"], found["good"], found["bad"]), (corrected["name"], 1, 8, 0))
        self.assertEqual(found["time_context"], new_context)
        self.assertIs(getattr(frappe.local, "production_report_context", None), previous_context)
        CHECKS["same_key_recovery"] = {"passed": True, "new_fact_count": 1, "new_time_rows": 1,
            "original_retained_cancelled_good": 10, "replacement_good": 8, "bad": 0, "remaining": 2,
            "original_link_and_snapshot_preserved": True, "plan_and_other_tasks_unchanged": True,
            "stock_unchanged": True, "new_orphan_time_rows": 0, "existing_orphan_set_unchanged": True,
            "result_lookup_same_card_and_time_snapshot": True,
            "request_context_restored": True, "actual_minutes": 60, "effective_seconds": corrected["report_effective_seconds"],
            "task_status": after_operation["status"], "work_order_status": recovered["order"]["status"],
            "hour_rate": operation["hour_rate"], "expected_task_cost": expected_cost,
            "actual_task_cost": after_operation["actual_operating_cost"], "cost_precision": precision,
            "nonzero_cost_exercised": bool(operation["hour_rate"]), "recovered_state_sha256": digest(recovered)}


def main():
    global RUN_DIR
    os.umask(0o077)
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    PRIVATE.chmod(0o700)
    RUN_DIR = PRIVATE / (datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    RUN_DIR.mkdir(mode=0o700)
    summary = {"case": "I06 correction cancel/insert before submit", "passed": False,
               "scope": "controlled DB savepoint rollback, not HTTP rollback, browser acceptance, or full G3",
               "tests_expected": 1, "tests_run": 0, "private_run_directory": RUN_DIR.name,
               "automatic_retries": 0, "recovery_calls_expected": 1, "credentials_printed": False}
    started = time.monotonic()
    connected = False
    baseline = None
    runtime = None
    with (RUN_DIR / "raw-run.log").open("x", encoding="utf-8") as raw:
        with contextlib.redirect_stdout(raw), contextlib.redirect_stderr(raw):
            try:
                runtime = source_state()
                summary["source_before_test"] = runtime
                write_private("source-before.json", runtime)
                os.chdir("sites")
                frappe.init(site="xgd-test.localhost")
                frappe.connect()
                connected = True
                assert frappe.conf.get("allow_tests"), "Tests must be enabled on the isolated test site"
                assert not frappe.db.exists("Workflow", {"document_type": "Work Order"}), "Original fixture requires no Work Order Workflow"
                frappe.flags.in_test = True
                frappe.flags.skip_test_records = True
                frappe.set_user("Administrator")
                baseline = capture_tables(BUSINESS + SECURITY + EXTRA)
                write_private("baseline-20-tables.json", baseline)
                suite = unittest.TestSuite([TestCorrectionRollback("test_correction_cancel_insert_failure_rolls_back_then_same_key_recovers")])
                result = unittest.TextTestRunner(stream=raw, verbosity=2).run(suite)
                summary.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                               skipped=len(result.skipped), test_success=result.wasSuccessful())
            except Exception as error:
                summary["runner_failure_type"] = type(error).__name__
                traceback.print_exc(file=raw)
            finally:
                if connected:
                    try:
                        frappe.db.rollback()
                        frappe.set_user("Administrator")
                        if baseline is not None:
                            after = capture_tables(BUSINESS + SECURITY + EXTRA, baseline)
                            write_private("final-20-tables.json", after)
                            summary["final_retention"] = retention(baseline, after)
                            summary["all_20_tables_exactly_restored"] = after == baseline
                            summary["baseline_tables_sha256"] = digest(baseline)
                            summary["final_tables_sha256"] = digest(after)
                        summary["final_request_context_clear"] = getattr(frappe.local, "production_report_context", None) is None
                        final_source = source_state()
                        summary["source_unchanged_after_test"] = final_source == runtime
                    except Exception as error:
                        summary["final_verification_failure_type"] = type(error).__name__
                        traceback.print_exc(file=raw)
                    finally:
                        frappe.db.rollback()
                        frappe.destroy()
    summary["checks"] = CHECKS
    summary["elapsed_seconds"] = round(time.monotonic() - started, 6)
    summary["passed"] = bool(summary.get("test_success") and summary["tests_run"] == 1 and
                             not summary.get("skipped") and summary.get("all_20_tables_exactly_restored") and
                             summary.get("final_request_context_clear") and summary.get("source_unchanged_after_test") and
                             len(CHECKS) == 2 and not summary.get("runner_failure_type") and not summary.get("final_verification_failure_type"))
    summary["limitations"] = ["Explicit harness savepoint rollback does not prove HTTP automatic rollback or committed-response recovery.",
                               "One bounded correction path; no downstream/stock reversal, concurrent correction, full G2/G3, UI, mobile or delivery acceptance.",
                               "Cost checks report whether a nonzero rate was actually exercised; zero-rate evidence is not nonzero pricing acceptance."]
    write_private("safe-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
