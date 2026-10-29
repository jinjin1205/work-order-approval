"""New B06 partial-plan HTTP boundary; no replay, retry, or old fixture writes."""
import concurrent.futures
import http.client
import json
import subprocess
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import quote

p = Path(".development/private/b06-tasks-20261029")
a = json.loads((p / "access.json").read_text())
assert a["site"] == "xgd-b08-http.localhost"
assert not (p / "http-summary.json").exists(), "Resume from evidence; never replay consumed input"
raw = []

def control(mode):
    return json.loads(subprocess.check_output(["docker", "exec", "-w", "/home/frappe/frappe-bench", "xgd-b08-check", "env/bin/python", "/b01/b06_tasks_control.py", mode], text=True))

def request(label, actor, path, arguments=None, verb="POST", barrier=None):
    actor = a["actors"][actor]
    connection = http.client.HTTPConnection("127.0.0.1", 18090, timeout=40)
    try:
        connection.connect()
        port = connection.sock.getsockname()[1]
        if barrier:
            barrier.wait(timeout=10)
        started = time.perf_counter_ns()
        connection.request(verb, path, body=json.dumps(arguments).encode() if arguments is not None else None,
            headers={"Host": a["site"], "Authorization": "token " + actor["api_key"] + ":" + actor["api_secret"], "Content-Type": "application/json", "Connection": "close"})
        response = connection.getresponse()
        result = {"case": label, "status": response.status, "body": json.loads(response.read()),
            "started_ns": started, "ended_ns": time.perf_counter_ns(), "local_port": port}
        raw.append(result)
        (p / "http-raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2))
        return result
    finally:
        connection.close()

api = "/api/method/erpnext.manufacturing.doctype.job_card.job_card."
before = control("state")
assert before["state"] == "待审核" and before["reports"] == 0
assert [float(row["plan"]) for row in before["tasks"]] == [1, 2, 3]
row = before["tasks"][0]["name"]
resource = "/api/resource/Work%20Order%20Operation/" + quote(row, safe="")
assert request("frozen unreported child PUT", "editor", resource, {"time_in_mins": 999}, "PUT")["status"] == 403
assert request("frozen unreported child DELETE", "editor", resource, verb="DELETE")["status"] == 403
assert control("state") == before
control("approve")
tasks = request("current independent task plans", "reporter", api + "get_production_report_tasks", {"work_order": a["order"]})
assert tasks["status"] == 200 and [row["plan"] for row in tasks["body"]["message"]["tasks"]] == [1, 2, 3]

arguments = []
for hour in (9, 10):
    args = {"work_order": a["order"], "operation_id": row, "from_time": f"2026-10-20 {hour}:00:00", "to_time": f"2026-10-20 {hour+1}:00:00"}
    preview = request("partial task time context", "reporter", api + "preview_production_report_time", args)
    assert preview["status"] == 200
    args.update(request_id=uuid.uuid4().hex, good_quantity=1, bad_quantity=0,
        context_fingerprint=preview["body"]["message"]["context_fingerprint"])
    arguments.append(args)

initial = control("state")
assert initial["cards"] == 3 and initial["reports"] == 0
bad = {**arguments[0], "request_id": uuid.uuid4().hex, "good_quantity": 2}
assert request("task plan 1 rejects report 2", "reporter", api + "confirm_production_report", bad)["status"] == 417
assert control("state") == initial, "Failed HTTP request left partial facts"

barrier = threading.Barrier(2)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures = [pool.submit(request, "different request " + str(i), "reporter", api + "confirm_production_report", args, "POST", barrier) for i, args in enumerate(arguments)]
    results = [future.result() for future in futures]
assert sorted(r["status"] for r in results) == [200, 417]
overlap = min(r["ended_ns"] for r in results) > max(r["started_ns"] for r in results)
assert overlap and len({r["local_port"] for r in results}) == 2
after = control("state")
assert after["reports"] == 1 and after["cards"] == 4
assert after["tasks"][0]["good"] == 1 and after["tasks"][0]["bad"] == 0 and after["tasks"][0]["status"] == "Completed"
assert all(not r["good"] and not r["bad"] for r in after["tasks"][1:])
assert after["parent_plan"] == 10 and after["produced"] == 0 and after["inventory"] == 0
summary = {"frozen_child_put": 403, "frozen_child_delete": 403, "frozen_zero_partial_write": True,
    "task_plans": [1, 2, 3], "parent_plan": 10, "over_report_status": 417, "over_report_zero_partial_write": True,
    "concurrent_statuses": sorted(r["status"] for r in results), "distinct_connections": 2,
    "client_request_intervals_overlap": overlap, "database_lock_overlap_observed": False,
    "effective_reports": 1, "task_good": 1, "task_bad": 0, "task_completed": True,
    "other_tasks_pending": True, "new_stock_entries": 0,
    "scope": "New partial-task limit only; unchanged I03-I06 not rerun; not whole G2 acceptance"}
(p / "http-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(summary, ensure_ascii=False))
