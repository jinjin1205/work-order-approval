"""Exactly one real two-connection HTTP attempt for the selected I03/I04 case.

Run only on the prepared dedicated fixture. Source/script hashes are written
before requests. No mutation retry is implemented. Raw responses stay private.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import http.client
import json
import math
import os
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlencode

PRIVATE = Path(".development/private/b08-distinct-concurrency")
EVIDENCE = Path("evidence/B08/distinct-concurrency-20261028")
CONTAINER_PRIVATE = "/tmp/b08-distinct-concurrency-private/"
FIXTURE_SCRIPT = "/b01/b08_distinct_concurrency_fixture.py"
API = "erpnext.manufacturing.doctype.job_card.job_card."
AUDIT = {"modified", "modified_by"}
ORDER_DERIVED = {"actual_operating_cost", "total_operating_cost", "actual_start_date", "actual_end_date", "lead_time", "status"}
OPERATION_DERIVED = {"completed_qty", "process_loss_qty", "actual_operation_time", "actual_start_time",
                     "actual_end_time", "status", "actual_operating_cost"}


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), default=str).encode()).hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")
    path.chmod(0o600)


def container_json(container, *args):
    return json.loads(subprocess.check_output(["docker", "exec", container, "env/bin/python", FIXTURE_SCRIPT, *args], text=True))


def snapshot(case, label):
    info = container_json("xgd-b08-check", "snapshot", case, label)
    name = case + "-" + label + ".json"
    target = PRIVATE / name
    assert not target.exists(), "Never replace a prior snapshot"
    subprocess.run(["docker", "cp", "xgd-b08-check:" + CONTAINER_PRIVATE + name, str(target)], check=True, capture_output=True)
    target.chmod(0o600)
    data = json.loads(target.read_text())
    assert sha(data) == info["state_sha256"], "Snapshot copy hash mismatch"
    return data


def service_evidence():
    path = EVIDENCE / "server-prerequisite.json"
    observed = json.loads(path.read_text())
    assert observed["observed_frappe_serve_default_no_threading"] is False
    assert observed["observed_werkzeug_argument"] == "threaded=not no_threading"
    assert observed["threading_disable_flag_present"] is False
    return {"evidence_file": path.name, "evidence_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "observed": observed, "database_lock_overlap_observed": False}


def request(sample, alias, method, arguments=None, verb="GET", resource=False, barrier=None):
    actor = sample["actors"][alias]
    headers = {"Host": sample["site"], "Authorization": "token " + actor["keys"]["api_key"] + ":" + actor["keys"]["api_secret"],
               "Content-Type": "application/json", "Accept": "application/json", "Connection": "close"}
    path = "/api/resource/" + method if resource else "/api/method/" + method
    body = None
    if arguments is not None:
        if verb == "GET":
            path += "?" + urlencode({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in arguments.items()})
        else:
            body = json.dumps(arguments).encode()
    connection = http.client.HTTPConnection("127.0.0.1", 18090, timeout=45)
    local_port = None
    request_attempted = False
    started_ns = time.perf_counter_ns()
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        connection.connect()
        local_port = connection.sock.getsockname()[1]
        if barrier:
            barrier.wait(timeout=15)
        started_ns = time.perf_counter_ns()
        started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        request_attempted = True
        connection.request(verb, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = json.loads(response.read())
        status = response.status
    except Exception as error:
        payload = {"transport_error_type": type(error).__name__}
        status = None
    finally:
        ended_ns = time.perf_counter_ns()
        ended_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        connection.close()
    return {"actor": alias, "status": status, "response": payload, "start_ns": started_ns, "end_ns": ended_ns,
            "start_utc": started_utc, "end_utc": ended_utc, "local_port": local_port, "request_attempted": request_attempted}


def response_value(result):
    assert result["status"] == 200, "Required normal HTTP request failed; see private responses"
    data = result["response"]
    return data.get("message", data.get("data"))


def error_text(data):
    parts = [str(data.get("exception", ""))]
    items = data.get("_server_messages") or "[]"
    for item in json.loads(items) if isinstance(items, str) else items:
        parts.append(str((json.loads(item) if isinstance(item, str) else item).get("message", "")))
    return "\n".join(parts)


def stable(value, excluded):
    return {key: val for key, val in value.items() if key not in excluded}


def invariant_order(order, operation_id):
    result = stable(order, AUDIT | ORDER_DERIVED | {"operations"})
    for key, value in result.items():
        if isinstance(value, list):
            result[key] = [stable(row, AUDIT) if isinstance(row, dict) else row for row in value]
    result["operations"] = [stable(row, AUDIT | (OPERATION_DERIVED if row["name"] == operation_id else set()))
                            for row in order["operations"]]
    return result


def verify_state(sample, case, before, after, replies, previews):
    data = sample["cases"][case]
    successes = {alias: reply for alias, reply in replies.items() if reply["status"] == 200}
    expected = 1 if case == "I03" else 2
    assert len(successes) == expected, "Unexpected number of accepted requests"
    rejected = {alias: reply for alias, reply in replies.items() if reply["status"] != 200}
    if case == "I03":
        reply = next(iter(rejected.values()))
        assert reply["status"] == 417 and reply["response"].get("exc_type") == "ValidationError"
        assert any(message in error_text(reply["response"]) for message in
                   ("本道工序已经完成", "本工序累计数量超过工单允许数量")), "Rejection must be the specific task quantity/state conflict"
    names = {reply["response"]["message"]["name"] for reply in successes.values()}
    assert len(names) == expected and data["baseline_card"] not in names
    before_cards = {row["name"]: row for row in before["cards"]}
    after_cards = {row["name"]: row for row in after["cards"]}
    assert all(after_cards.get(name) == row for name, row in before_cards.items()), "Existing plan or baseline cards changed"
    assert set(after_cards) - set(before_cards) == names, "Partial or unrelated cards were added"
    global_before = before["global_cards"]["rows"]
    global_after = after["global_cards"]["rows"]
    assert all(global_after.get(name) == value for name, value in global_before.items())
    assert set(global_after) - set(global_before) == names, "Global new-card set differs from successful requests"
    old_logs = {row["name"]: row for row in before["global_time_logs"]}
    all_logs = {row["name"]: row for row in after["global_time_logs"]}
    assert all(all_logs.get(name) == row for name, row in old_logs.items()), "Existing time rows changed"
    new_logs = [row for name, row in all_logs.items() if name not in old_logs]
    assert len(new_logs) == expected and {row["parent"] for row in new_logs} == names
    assert all(row["parent"] in global_after for row in new_logs), "New orphan time row found"
    for alias, reply in successes.items():
        card = after_cards[reply["response"]["message"]["name"]]
        actor = sample["actors"][alias]
        logs = [row for row in new_logs if row["parent"] == card["name"]]
        assert card["owner"] == actor["user"] and card["report_request_id"] == data["requests"][alias]
        assert card["docstatus"] == 1 and card["work_order"] == data["order"] and card["operation_id"] == data["operation_id"]
        assert card["total_completed_qty"] == data["inputs"][alias]["good_quantity"] and card["process_loss_qty"] == 0
        assert len(logs) == 1 and logs[0]["employee"] == actor["employee"]
        assert logs[0]["from_time"] == data["inputs"][alias]["from_time"] and logs[0]["to_time"] == data["inputs"][alias]["to_time"]
        assert logs[0]["completed_qty"] == data["inputs"][alias]["good_quantity"]
        assert logs[0]["time_in_mins"] == card["total_time_in_mins"] == 60
        assert card["report_effective_seconds"] == 3600
        assert card["report_effective_seconds"] == previews[alias]["effective_seconds"]
    for alias in rejected:
        assert not any(row.get("report_request_id") == data["requests"][alias] for row in after["cards"])
    assert invariant_order(before["order"], data["operation_id"]) == invariant_order(after["order"], data["operation_id"])
    assert before["stock"] == after["stock"], "Stock rows or values changed"
    facts = [row for row in after["cards"] if row.get("report_request_id") and row["docstatus"] == 1]
    assert len(facts) == 1 + expected
    operation = next(row for row in after["order"]["operations"] if row["name"] == data["operation_id"])
    good = sum(row["total_completed_qty"] for row in facts)
    bad = sum(row["process_loss_qty"] for row in facts)
    minutes = sum(row["total_time_in_mins"] for row in facts)
    assert good == operation["completed_qty"] == 10 and bad == operation["process_loss_qty"] == 0
    assert minutes == operation["actual_operation_time"] == (120 if case == "I03" else 180)
    assert operation["status"] == "Completed" and after["order"]["qty"] == 10
    assert after["order"]["status"] == "In Process"
    fact_names = {row["name"] for row in facts}
    fact_logs = [row for row in after["logs"] if row["parent"] in fact_names]
    first = min(row["from_time"] for row in fact_logs)
    last = max(row["to_time"] for row in fact_logs)
    assert operation["actual_start_time"] == after["order"]["actual_start_date"] == first
    assert operation["actual_end_time"] == after["order"]["actual_end_date"] == last
    lead_minutes = (datetime.datetime.fromisoformat(last) - datetime.datetime.fromisoformat(first)).total_seconds() / 60
    assert after["order"]["lead_time"] == lead_minutes
    before_operation = next(row for row in before["order"]["operations"] if row["name"] == data["operation_id"])
    expected_cost = before_operation["hour_rate"] * (120 if case == "I03" else 180) / 60
    precision = after["operation_cost_precisions"][operation["name"]]
    assert math.isclose(operation["actual_operating_cost"], expected_cost, rel_tol=0, abs_tol=0.5 * 10 ** -precision)
    assert math.isclose(after["order"]["actual_operating_cost"], sum(row["actual_operating_cost"] for row in after["order"]["operations"]), abs_tol=1e-6)
    expected_total = after["order"]["additional_operating_cost"] + (after["order"]["actual_operating_cost"] or after["order"]["planned_operating_cost"]) + after["order"]["corrective_operation_cost"]
    assert math.isclose(after["order"]["total_operating_cost"], expected_total, abs_tol=1e-6)
    assert not after["order"].get("produced_qty") and not after["order"].get("material_transferred_for_manufacturing")
    return {"passed": True, "new_fact_count": expected, "effective_fact_count": len(facts), "new_time_rows": len(new_logs),
            "new_orphan_time_rows": 0, "rejected_request_partial_facts": 0, "old_cards_and_time_rows_unchanged": True,
            "plan_route_and_other_tasks_unchanged": True, "stock_unchanged": True, "owner_employee_request_task_binding": True,
            "same_task_distinct_new_cards": True, "final": {"plan": 10, "good": good, "bad": bad, "remaining": 0,
                "actual_operation_minutes": minutes, "lead_time_minutes": lead_minutes,
                "locked_hour_rate": before_operation["hour_rate"], "independent_expected_task_cost": expected_cost,
                "cost_precision": precision, "effective_seconds": sum(row["report_effective_seconds"] for row in facts),
                "task_actual_operating_cost": operation["actual_operating_cost"], "work_order_actual_operating_cost": after["order"]["actual_operating_cost"],
                "work_order_total_operating_cost": after["order"]["total_operating_cost"], "actual_start": first,
                "actual_end": last, "task_status": operation["status"], "work_order_status": after["order"]["status"]}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=("I03", "I04"))
    args = parser.parse_args()
    case = args.case
    os.umask(0o077)
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sample = json.loads((PRIVATE / "fixture.json").read_text())
    assert sample["site"] == "xgd-b08-http.localhost" and sample["base_url"] == "http://127.0.0.1:18090"
    assert sample["actors"]["A"]["user"] != sample["actors"]["B"]["user"]
    source = {name: container_json(name, "source") for name in ("xgd-b08-check", "xgd-b08-ui")}
    local_scripts = {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                     for name in ("b08_distinct_concurrency_fixture.py", "b08_distinct_concurrency_http.py")}
    assert all(item["scripts"] == local_scripts for item in source.values())
    beginning = {"case": case, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "scripts_before_batch": local_scripts, "runtime_source_before_batch": source,
                 "web_concurrency": service_evidence(), "client_connections": 2, "automatic_mutation_retries": 0}
    write_json(PRIVATE / (case + "-started.json"), {**beginning, "fixture_sha256": sha(sample)})
    write_json(EVIDENCE / ("http-" + case.lower() + "-before.json"), beginning)
    raw = []
    summary = {"case": case, "passed": False, "http_confirmations_sent": 0,
               "scripts_before_batch": local_scripts, "scope": "real HTTP; no browser actions", "requests": []}
    after_captured = False
    try:
        data = sample["cases"][case]
        before = snapshot(case, "before")
        initial_facts = [row for row in before["cards"] if row.get("report_request_id") and row["docstatus"] == 1]
        assert len(initial_facts) == 1 and initial_facts[0]["total_completed_qty"] == 8
        assert not any(row.get("report_request_id") in data["requests"].values() for row in before["cards"])
        previews = {}
        bodies = {}
        for alias in ("A", "B"):
            identity = request(sample, alias, "frappe.auth.get_logged_user")
            raw.append({"step": "identity", **identity})
            assert response_value(identity) == sample["actors"][alias]["user"]
            permissions = []
            for doctype, docname, permission, expected in (
                ("Work Order", data["order"], "read", True), ("Work Order", data["order"], "write", False),
                ("Stock Entry", "", "create", False), ("Job Card", data["baseline_card"], "write", True),
                ("Job Card", data["baseline_card"], "submit", True),
            ):
                result = request(sample, alias, "frappe.client.has_permission", {"doctype": doctype, "docname": docname, "perm_type": permission})
                raw.append({"step": "permission", **result})
                actual = response_value(result)["has_permission"]
                permissions.append({"doctype": doctype, "permission": permission, "actual": actual, "expected": expected})
                assert actual is expected, "Actor permission differs from narrow contract"
            result = request(sample, alias, API + "preview_production_report_time", data["inputs"][alias])
            raw.append({"step": "preview", **result})
            previews[alias] = response_value(result)
            bodies[alias] = {**data["inputs"][alias], "request_id": data["requests"][alias],
                             "context_fingerprint": previews[alias]["context_fingerprint"]}
            summary.setdefault("previews", []).append({"actor": alias, "permissions": permissions,
                "effective_seconds": previews[alias]["effective_seconds"], "business_time": {
                    "from": data["inputs"][alias]["from_time"], "to": data["inputs"][alias]["to_time"]},
                "request_key_sha256": sha(data["requests"][alias]), "actor_identity_sha256": sha(sample["actors"][alias]["user"]),
                "task_identity_sha256": sha([data["order"], data["operation_id"]]), "business_content_sha256": sha(data["inputs"][alias])})
        assert bodies["A"]["request_id"] != bodies["B"]["request_id"]
        write_json(PRIVATE / (case + "-request-bodies.json"), bodies)
        barrier = threading.Barrier(2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = {alias: pool.submit(request, sample, alias, API + "confirm_production_report", bodies[alias], "POST", False, barrier)
                       for alias in ("A", "B")}
            replies = {alias: future.result() for alias, future in futures.items()}
        summary["http_confirmations_sent"] = sum(reply["request_attempted"] for reply in replies.values())
        raw.extend({"step": "concurrent-confirm", **reply} for reply in replies.values())
        write_json(PRIVATE / (case + "-concurrent-responses.json"), replies)
        after = snapshot(case, "after")
        after_captured = True
        overlap = min(reply["end_ns"] for reply in replies.values()) - max(reply["start_ns"] for reply in replies.values())
        summary["client_intervals_overlap"] = overlap > 0
        summary["client_overlap_ms"] = overlap / 1_000_000
        summary["independent_tcp_connections"] = len({reply["local_port"] for reply in replies.values()}) == 2
        for alias, reply in replies.items():
            response = reply["response"]
            summary["requests"].append({"actor": alias, "status": reply["status"], "exception_type": response.get("exc_type"),
                "start_utc": reply["start_utc"], "end_utc": reply["end_utc"], "elapsed_ms": (reply["end_ns"] - reply["start_ns"]) / 1_000_000,
                "request_key_sha256": sha(data["requests"][alias]), "business_content_sha256": sha(data["inputs"][alias]),
                "result_card_sha256": sha(response["message"]["name"]) if reply["status"] == 200 else None,
                "specific_quantity_or_completed_conflict": any(marker in error_text(response) for marker in
                    ("本道工序已经完成", "本工序累计数量超过工单允许数量")),
                "permission_or_overlap_or_server_error": reply["status"] in (403, 500) or response.get("exc_type") == "OverlapError"})
            result = request(sample, alias, API + "get_production_report_result", {"request_id": data["requests"][alias]})
            raw.append({"step": "independent-result-readback", **result})
            saved = response_value(result)
            assert (saved is not None) == (reply["status"] == 200)
            if saved is not None:
                assert saved["name"] == response["message"]["name"] and saved["docstatus"] == 1
        assert overlap > 0 and summary["independent_tcp_connections"], "No real overlapping independent client requests"
        summary["verification"] = verify_state(sample, case, before, after, replies, previews)
        summary["before_state_sha256"] = sha(before)
        summary["after_state_sha256"] = sha(after)
        summary["passed"] = True
    except Exception as error:
        summary["failure_type"] = type(error).__name__
        summary["failure_message"] = str(error) if isinstance(error, AssertionError) else "See private execution log"
        raise
    finally:
        if not after_captured and (PRIVATE / (case + "-before.json")).exists():
            try:
                snapshot(case, "after")
            except Exception as error:
                summary["after_snapshot_error"] = type(error).__name__
        write_json(PRIVATE / (case + "-raw.json"), raw)
        summary["runtime_source_before_batch_file"] = "http-" + case.lower() + "-before.json"
        summary["database_lock_overlap_observed"] = False
        summary["limit"] = "Two-thread-capable service and overlapping independent HTTP intervals; not a DB lock trace, not full G3 or browser acceptance. No retry occurred."
        write_json(EVIDENCE / ("http-" + case.lower() + ".json"), summary)
        print(json.dumps({"case": case, "passed": summary["passed"], "http_confirmations_sent": summary["http_confirmations_sent"],
                          "failure_type": summary.get("failure_type"), "credentials_printed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
