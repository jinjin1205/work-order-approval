"""Verify saved B19 HTTP results and emit only public-safe assertions and hashes."""
import copy
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
evidence = root / "evidence/B19/http"


def read(name):
    return json.loads((evidence / name).read_text())


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


reports = {name: read(name + ".json") for name in (
    "fixture-http", "denied-http", "denied-tail-http", "approval-http", "execute-http")}
assert all(reports[name]["passed"] for name in reports if name != "denied-http")
partial = reports["denied-http"]
assert not partial["passed"] and len(partial["requests"]) == 9
assert all(r["http_expectation_met"] for r in partial["requests"][:-1])
assert partial["requests"][-1]["response"]["exc_type"] == "ValidationError"
assert partial["requests"][-1]["status"] == 417
assert "转移" in partial["requests"][-1]["response"]["exception"]
tail = reports["denied-tail-http"]["requests"]
assert [r["status"] for r in tail] == [200, 403, 403, 403, 200]
assert all("尚未完成审核和签批" in r["response"]["exception"] for r in tail[1:4])

before, denied, approved, executed = [read(name + ".json") for name in (
    "before", "after-deny", "after-approval", "after-execution")]
# Native HTTP reads set _seen. Prove that this is the sole Work Order table change.
rows = copy.deepcopy(denied["work_order_rows"])
assert sha(rows) == denied["tables"]["Work Order"]["sha256"]
for row in rows:
    if row["name"] == before["order"]["name"]:
        row["_seen"] = None
assert sha(rows) == before["tables"]["Work Order"]["sha256"]
assert all(before["tables"][dt] == denied["tables"][dt] for dt in before["tables"] if dt != "Work Order")
assert all(before[key] == denied[key] for key in before if key != "tables")

assert approved["order"]["workflow_state"] == "已批准" and approved["order"]["docstatus"] == 1
assert approved["order"]["status"] == "Not Started" and approved["order"]["qty"] == 11
assert approved["order"]["produced_qty"] == 0 and approved["order"]["material_transferred_for_manufacturing"] == 0
assert len(approved["job_cards"]) == 3 and not approved["stock_entries"]
assert all(c["docstatus"] == 0 and c["total_completed_qty"] == 0 and c["total_time_in_mins"] == 0 for c in approved["job_cards"])
for dt in ("Job Card Time Log", "Stock Entry", "Stock Entry Detail", "Stock Ledger Entry"):
    assert before["tables"][dt] == approved["tables"][dt]
assert approved["source_qty"] == 100 and approved["wip_qty"] is None

assert executed["order"]["status"] == "Not Started" and executed["order"]["produced_qty"] == 0
assert executed["order"]["material_transferred_for_manufacturing"] == 1
assert len(executed["stock_entries"]) == 1 and executed["stock_entries"][0]["docstatus"] == 1
assert executed["source_qty"] == 99 and executed["wip_qty"] == 1
assert executed["tables"]["Job Card Time Log"]["count"] == approved["tables"]["Job Card Time Log"]["count"] + 1

for name in ("source-before.log", "source-after.log"):
    check = json.loads((evidence / name).read_text().splitlines()[-1])
    assert check["business_tables_unchanged"] == 11 and check["work_order_workflows"] == 0
source = read("source-web.json")
assert source["files_match"] and len(source["checked_files"]) == 14
manifest = json.loads((root / ".development/checks/b19-history-source-manifest.json").read_text())
assert source["patch_sha256"] == manifest["patch_sha256"]

summary = {
    "date": "2026-10-27", "scope": "B19 real HTTP against a retained synthetic test-site copy; no product code change",
    "upstream_commit": source["checkout_commit"], "patch_sha256": source["patch_sha256"],
    "runtime_source_files_match": 14,
    "requests_recorded": sum(len(r["requests"]) for r in reports.values()),
    "requests_matching_planned_status": sum(bool(q.get("http_expectation_met")) for r in reports.values() for q in r["requests"]),
    "initial_fixture_precondition_mismatch": 1,
    "fixture_correction": "Timer initially stopped at native material-transfer validation; continued on another existing no-material task of the same unapproved order. No business guard relaxed.",
    "completed_assertions": {
        "six_real_actor_identities": True, "generic_approval_bypasses_denied": True,
        "native_bulk_sync_http_200_did_not_approve": True,
        "pending_task_timer_direct_and_indirect_stock_denied": True,
        "denials_business_facts_unchanged": True, "only_native_seen_flag_changed": True,
        "two_stage_approval_return_resubmit_cross_team_self_approval_and_stale_page": True,
        "approval_creates_only_three_pending_tasks_no_execution_facts": True,
        "authorized_timer_and_stock_submit": True, "stock_quantity_moves_100_0_to_99_1": True,
        "original_test_site_eleven_tables_unchanged": True, "original_test_site_workflow_count_zero": True,
    },
    "limits": ["Native bulk exercised the below-20 synchronous rejection/rollback path; no successful bulk approval or queue claim",
        "Source preservation covers eleven recorded business tables, not every database table",
        "Dedicated HTTP copy retains workflow and synthetic data; development/customer workflow not activated",
        "Approved-basis changes, attachments, complete audit reconstruction, Chinese UI/mobile and notification remain unfinished",
        "G1 quantities, G2 original reporting and minimal roles, G3 full concurrency remain open"],
    "local_evidence_sha256": {name: hashlib.sha256((evidence / name).read_bytes()).hexdigest()
        for name in [*(name + ".json" for name in reports), "before.json", "after-deny.json", "after-approval.json",
                     "after-execution.json", "source-before.log", "source-after.log", "source-web.json"]},
}
with (evidence / "acceptance-summary.json").open("x") as output:
    json.dump(summary, output, ensure_ascii=False, indent=2)
    output.write("\n")
print(json.dumps({"assertions": "passed", "requests": summary["requests_recorded"],
    "matched_status": summary["requests_matching_planned_status"], "retained_fixture_mismatch": 1,
    "source_files": 14, "original_tables_unchanged": 11}))
