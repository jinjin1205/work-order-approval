"""Bounded real HTTP acceptance; defaults to reads and permission checks only.

Use --run --deployment-confirmed only after the parent confirms the fixed Web
source. A failed historical guard stops the run immediately. The only successful
deletes allowed here are manifest-listed, newly created, empty draft children.
"""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

os.umask(0o077)
PRIVATE = Path(".development/private/b08-history-paths")
EVIDENCE = Path("evidence/B08/history-paths-20261028")
fixture = json.loads((PRIVATE / "fixture.json").read_text())
assert fixture["site"] == "xgd-b08-http.localhost" and fixture["base_url"] == "http://127.0.0.1:18090"
assert fixture["user"].startswith("b08-history-") and (PRIVATE / "before.json").exists()
headers = {"Authorization": "token " + fixture["keys"]["api_key"] + ":" + fixture["keys"]["api_secret"],
           "Content-Type": "application/json", "Host": fixture["site"]}
requests = []
raw = []
cases = []
HISTORY_MESSAGE = "工序已有报工历史，不能直接改写、改挂或删除任务行"
TIME_MESSAGE = "报工时间和数量属于原记录，不能单独新增、改写或删除"


def write_json(path, value, exclusive=False):
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def resource(doctype, name):
    return "/api/resource/" + quote(doctype, safe="") + "/" + quote(name, safe="")


def rpc(method):
    return "/api/method/" + method


def call(label, path, args=None, verb="GET"):
    body = None
    if args is not None:
        if verb == "GET":
            path += "?" + urlencode(args)
        else:
            body = json.dumps(args).encode()
    started = time.monotonic()
    request = Request(fixture["base_url"] + path, data=body, headers=headers, method=verb)
    try:
        with urlopen(request, timeout=45) as response:
            status = response.status
            data = json.load(response)
    except HTTPError as error:
        status = error.code
        data = json.load(error)
    elapsed = round(time.monotonic() - started, 3)
    requests.append({"case": label, "verb": verb, "status": status,
                     "exception_type": data.get("exc_type"), "elapsed_seconds": elapsed})
    raw.append({"case": label, "status": status, "response": data})
    return status, data


def read(doctype, name, label="read"):
    status, data = call(label, resource(doctype, name))
    assert status == 200, "Required authorized read failed; inspect private response"
    return data["data"]


def messages(data):
    value = data.get("_server_messages") or "[]"
    items = json.loads(value) if isinstance(value, str) else value
    return "\n".join([str(data.get("exception", "")), *[
        str((json.loads(item) if isinstance(item, str) else item).get("message", "")) for item in items]])


def protected():
    targets = [
        ("Work Order", fixture["orders"]["history"]["order"]),
        ("Work Order Operation", fixture["orders"]["history"]["operations"][0]),
        ("Job Card", fixture["cancelled_card"]), ("Job Card Time Log", fixture["cancelled_log"]),
        ("Job Card", fixture["replacement_card"]),
        ("Work Order", fixture["orders"]["destination"]["order"]),
        ("Job Card", fixture["empty_card"]),
    ]
    # A missing row is captured as failure evidence, not hidden by an exception.
    return [call("history-readback", resource(dt, name)) for dt, name in targets]


def preflight():
    status, data = call("authenticate-new-test-actor", rpc("frappe.auth.get_logged_user"))
    assert status == 200 and data["message"] == fixture["user"], "Wrong HTTP identity"
    targets = [
        ("Work Order Operation", fixture["orders"]["history"]["operations"][0], ("read", "write", "submit", "delete")),
        ("Job Card Time Log", fixture["cancelled_log"], ("read", "write", "delete")),
        ("Work Order", fixture["orders"]["destination"]["order"], ("read", "write", "delete")),
        ("Work Order", fixture["orders"]["disposable"]["order"], ("read", "write", "delete")),
        ("Job Card", fixture["empty_card"], ("read", "write", "delete")),
    ]
    permissions = []
    for doctype, name, required in targets:
        read(doctype, name, "authorized-object-read")
        for permission in required:
            status, response = call("permission-" + permission, rpc("frappe.client.has_permission"),
                                    {"doctype": doctype, "docname": name, "perm_type": permission})
            allowed = status == 200 and response.get("message", {}).get("has_permission") is True
            permissions.append({"doctype": doctype, "permission": permission, "allowed": allowed})
            assert allowed, "Base permission missing; refusal would not prove a business guard"
    row = read("Work Order Operation", fixture["orders"]["history"]["operations"][0])
    assert row["docstatus"] == 1 and not any(row.get(k) for k in
        ("report_wage_mode", "report_wage_rate", "report_wage_currency", "report_standard_efficiency"))
    original = read("Job Card", fixture["cancelled_card"])
    replacement = read("Job Card", fixture["replacement_card"])
    assert original["docstatus"] == 2 and original["report_request_id"]
    assert replacement["docstatus"] == 1 and replacement["amended_from"] == original["name"]
    assert original["time_logs"][0]["name"] == fixture["cancelled_log"]
    cases.append({"case": "preflight", "passed": True, "ordinary_actor": True,
                  "pricing_unconfigured": True, "original_docstatus": 2, "replacement_docstatus": 1,
                  "original_good": original["total_completed_qty"], "replacement_good": replacement["total_completed_qty"],
                  "permissions": permissions})


def denied(label, path, args, verb, marker, expected_status=403, expected_type="PermissionError", bulk_names=None):
    before = protected()
    assert all(status == 200 for status, _ in before), "History was already missing before the request"
    status, response = call(label, path, args, verb)
    after = protected()
    same = before == after
    text = messages(response)
    matched = marker in text if isinstance(marker, str) else any(item in text for item in marker)
    valid = status == expected_status and matched
    if bulk_names is None:
        valid = valid and response.get("exc_type") == expected_type
    else:
        valid = valid and sorted(response.get("message", [])) == sorted(bulk_names)
    cases.append({"case": label, "status": status, "exception_type": response.get("exc_type"),
                  "expected_guard_message_matched": matched, "all_original_fields_and_links_unchanged": same,
                  "before_sha256": sha(before), "after_sha256": sha(after), "passed": bool(valid and same),
                  "guard": "native_cancelled_state" if expected_type == "ValidationError" else "business_history"})
    assert valid and same, "History request did not meet its guard expectation; stop immediately"


def authorized_empty_child(doctype, name):
    assert name in fixture["authorized_disposable_children"][doctype], "Delete is outside explicit disposable allowlist"
    child = read(doctype, name, "disposable-child-read")
    parent = read(child["parenttype"], child["parent"], "disposable-parent-read")
    assert child["docstatus"] == parent["docstatus"] == 0
    if doctype == "Work Order Operation":
        assert parent["name"] == fixture["orders"]["disposable"]["order"]
        assert parent["workflow_state"] == "草稿" and parent["approval_requested_by"] == fixture["user"]
        assert child["sequence_id"] != 1, "Preserve the first operation in the disposable draft"
        assert not child["completed_qty"] and not child["process_loss_qty"] and not child["actual_operation_time"]
    else:
        assert parent["name"] == fixture["empty_card"] and not parent.get("report_request_id")
        assert not child.get("from_time") and not child.get("to_time") and not child.get("completed_qty")
        assert not parent["total_completed_qty"] and not parent["total_time_in_mins"]
    return child, parent


def positive_delete(label, doctype, name, method):
    child, parent = authorized_empty_child(doctype, name)
    history_before = [read("Job Card", fixture[key]) for key in ("cancelled_card", "replacement_card")]
    if method == "resource":
        status, response = call(label, resource(doctype, name), None, "DELETE")
        success = status == 202
    elif method == "client":
        status, response = call(label, rpc("frappe.client.delete"), {"doctype": doctype, "name": name}, "POST")
        success = status == 200
    else:
        status, response = call(label, rpc("frappe.desk.reportview.delete_items"),
                                {"doctype": doctype, "items": json.dumps([name])}, "POST")
        success = status == 200 and response.get("message") == []
    missing_status, _ = call("deleted-child-readback", resource(doctype, name))
    parent_after = read(child["parenttype"], child["parent"])
    absent = name not in [row["name"] for row in parent_after[child["parentfield"]]]
    history_same = history_before == [read("Job Card", fixture[key]) for key in ("cancelled_card", "replacement_card")]
    database = independent_absence(doctype, name)
    passed = success and absent and history_same and not database["exists"] and database["protected_cancelled_time_exists"]
    cases.append({"case": label, "status": status, "child_readback_status": missing_status,
                  "new_empty_child_deleted": absent, "parent_retained": True,
                  "independent_database_check": database,
                  "historical_cards_unchanged": history_same, "passed": bool(passed)})
    assert passed, "Disposable positive failed; stop and inspect private responses"


def independent_absence(doctype, name):
    kind = "operation" if doctype == "Work Order Operation" else "time"
    names = fixture["orders"]["disposable"]["operations"] if kind == "operation" else fixture["disposable_logs"]
    index = names.index(name)
    output = subprocess.check_output(["docker", "exec", "xgd-b08-check", "env/bin/python",
                                      "/b01/b08_history_paths_http_fixture.py", "exists", kind, str(index)], text=True)
    return json.loads(output)


def initial_negatives():
    operation_name = fixture["orders"]["history"]["operations"][0]
    row = read("Work Order Operation", operation_name)
    for field, value in (("parent", fixture["orders"]["destination"]["order"]),
                         ("operation", fixture["alternate_operation"])):
        denied("operation-client-save-" + field, rpc("frappe.client.save"),
               {"doc": {**row, field: value}}, "POST", HISTORY_MESSAGE)
    denied("operation-resource-delete", resource("Work Order Operation", operation_name), None, "DELETE", HISTORY_MESSAGE)
    denied("cancelled-time-resource-delete", resource("Job Card Time Log", fixture["cancelled_log"]), None, "DELETE", TIME_MESSAGE)
    cancelled_messages = ("Cannot edit cancelled document", "不能编辑已取消", "无法编辑已取消", "已取消的文档无法编辑")
    denied("cancelled-time-client-delete", rpc("frappe.client.delete"),
           {"doctype": "Job Card Time Log", "name": fixture["cancelled_log"]}, "POST",
           cancelled_messages, 417, "ValidationError")
    denied("operation-resource-put-parent", resource("Work Order Operation", operation_name),
           {"parent": fixture["orders"]["destination"]["order"]}, "PUT", HISTORY_MESSAGE)


def review_saved_cancelled_response():
    """Review the preserved native raise response; do not repeat an HTTP mutation."""
    prior = json.loads((EVIDENCE / "http-acceptance.json").read_text())
    responses = json.loads((PRIVATE / "acceptance-raw.json").read_text())
    assert not prior["complete"] and len(prior["cases"]) == 6
    assert all(case["passed"] for case in prior["cases"][:-1])
    last = prior["cases"][-1]
    assert last["case"] == "cancelled-time-client-delete" and last["all_original_fields_and_links_unchanged"]
    response = next(item for item in responses if item["case"] == last["case"])
    assert response["status"] == 417 and response["response"]["exc_type"] == "ValidationError"
    assert "无法编辑已取消文档" in messages(response["response"])
    cases.append({**last, "expected_guard_message_matched": True, "passed": True,
                  "reviewed_saved_response_only": True, "new_http_request": False,
                  "initial_parser_failure_retained": True})


def remaining_acceptance():
    denied("cancelled-time-sync-bulk-delete", rpc("frappe.desk.reportview.delete_items"),
           {"doctype": "Job Card Time Log", "items": json.dumps([fixture["cancelled_log"]])}, "POST",
           TIME_MESSAGE, 200, bulk_names=[fixture["cancelled_log"]])

    # First modify the last disposable operation, then remove last and second;
    # the first sequence remains. No original or priced operation is a positive.
    last, second = fixture["orders"]["disposable"]["operations"][2:0:-1]
    child, _ = authorized_empty_child("Work Order Operation", last)
    status, response = call("draft-operation-client-save", rpc("frappe.client.save"),
                            {"doc": {**child, "description": "本轮一次性无事实草稿保存正例"}}, "POST")
    after = read("Work Order Operation", last)
    passed = status == 200 and after["description"] == "本轮一次性无事实草稿保存正例" and after["parent"] == child["parent"]
    cases.append({"case": "draft-operation-client-save", "status": status, "value_saved": passed,
                  "parent_unchanged": after["parent"] == child["parent"], "passed": passed})
    assert passed, "Draft save positive failed"
    positive_delete("draft-operation-resource-delete", "Work Order Operation", last, "resource")
    positive_delete("draft-operation-client-delete", "Work Order Operation", second, "client")
    for name, method in zip(fixture["disposable_logs"], ("resource", "client", "bulk")):
        positive_delete("empty-time-" + method + "-delete", "Job Card Time Log", name, method)
    final_history_check()


def finish_unexecuted():
    prior = json.loads((EVIDENCE / "http-remaining.json").read_text())
    assert not prior["complete"] and len(prior["cases"]) == 5
    assert all(case["passed"] for case in prior["cases"][:-1])
    last_case = prior["cases"][-1]
    assert last_case["case"] == "draft-operation-resource-delete" and last_case["status"] == 202
    assert last_case["new_empty_child_deleted"] and last_case["historical_cards_unchanged"]
    last, second = fixture["orders"]["disposable"]["operations"][2:0:-1]
    parent = read("Work Order", fixture["orders"]["disposable"]["order"])
    assert last not in [row["name"] for row in parent["operations"]]
    database = independent_absence("Work Order Operation", last)
    assert not database["exists"] and database["protected_cancelled_time_exists"]
    cases.append({**last_case, "passed": True, "independent_database_check": database,
                  "reviewed_prior_delete_only": True, "new_delete_request": False,
                  "initial_404_expectation_failure_retained": True})
    operation_name = fixture["orders"]["history"]["operations"][0]
    denied("operation-resource-put-parent", resource("Work Order Operation", operation_name),
           {"parent": fixture["orders"]["destination"]["order"]}, "PUT", HISTORY_MESSAGE)
    positive_delete("draft-operation-client-delete", "Work Order Operation", second, "client")
    for name, method in zip(fixture["disposable_logs"], ("resource", "client", "bulk")):
        positive_delete("empty-time-" + method + "-delete", "Job Card Time Log", name, method)
    final_history_check()


def final_history_check():
    old = [item for item in raw if item["case"] == "history-readback"]
    if not old:
        old = json.loads((PRIVATE / "acceptance-raw.json").read_text())
    baseline = [(item["status"], item["response"]) for item in old if item["case"] == "history-readback"][:5]
    final = protected()[:5]
    assert baseline == final, "Final original history differs from the first HTTP snapshot"
    cases.append({"case": "final-original-history", "passed": True,
                  "all_fields_and_links_unchanged": True, "before_sha256": sha(baseline), "after_sha256": sha(final)})


def finish_empty_times():
    prior = json.loads((EVIDENCE / "http-finish.json").read_text())
    assert not prior["complete"] and prior["failure_type"] == "KeyError"
    assert len(prior["cases"]) == 4 and all(case["passed"] for case in prior["cases"])
    assert not any(request["case"].startswith("empty-time-") for request in prior["requests"])
    for name, method in zip(fixture["disposable_logs"], ("resource", "client", "bulk")):
        positive_delete("empty-time-" + method + "-delete", "Job Card Time Log", name, method)
    final_history_check()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--deployment-confirmed", action="store_true")
    parser.add_argument("--remaining", action="store_true",
                        help="Continue only the unexecuted portion after the preserved native-message parser failure")
    parser.add_argument("--finish", action="store_true",
                        help="Continue after the preserved missing-child status assertion; never repeat that delete")
    parser.add_argument("--empty-times", action="store_true",
                        help="Complete only the three unexecuted empty-time positives after the nullable-field parser stop")
    args = parser.parse_args()
    mode = "empty-times" if args.empty_times else ("finish" if args.finish else ("remaining" if args.remaining else ("acceptance" if args.run else "preflight")))
    assert sum((args.remaining, args.finish, args.empty_times)) <= 1
    assert not (args.remaining or args.finish or args.empty_times) or args.run
    assert not args.run or args.deployment_confirmed, "Wait for explicit deployment confirmation"
    if args.run:
        write_json(PRIVATE / (mode + "-started.json"), {"started_at": time.time(), "fixture_sha256": sha(fixture)}, exclusive=True)
    complete = False
    error_type = None
    try:
        preflight()
        if args.run:
            if args.empty_times:
                finish_empty_times()
            elif args.finish:
                finish_unexecuted()
            elif args.remaining:
                review_saved_cancelled_response()
                remaining_acceptance()
            else:
                initial_negatives()
                remaining_acceptance()
        complete = True
    except Exception as error:
        error_type = type(error).__name__
        raise
    finally:
        write_json(PRIVATE / (mode + "-raw.json"), raw)
        summary = {"mode": mode, "complete": complete, "failure_type": error_type,
                   "cases": cases, "requests": requests, "credentials_printed": False,
                   "scope": "real HTTP; no browser actions; synchronous bulk only"}
        write_json(EVIDENCE / ("http-" + mode + ".json"), summary)
        print(json.dumps({"mode": mode, "complete": complete, "failure_type": error_type,
                          "cases": len(cases), "requests": len(requests), "credentials_printed": False}, ensure_ascii=False))
