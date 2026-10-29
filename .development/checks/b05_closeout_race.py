"""One bounded overlapping HTTP begin/close case on the new synthetic sample."""
import concurrent.futures
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
a = json.loads((ROOT / ".development/private/b05-closeout-20261029/access.json").read_text())
sample = next(s for s in a["samples"] if s["mode"] == "race")
prefix = "erpnext.manufacturing.doctype.work_order.work_order."
def call(method, values, *, get=False):
    data = urllib.parse.urlencode(values).encode()
    url = a["base_url"] + "/api/method/" + method
    if get: url += "?" + data.decode()
    req = urllib.request.Request(url, data=None if get else data,
        headers={"Authorization":"token " + a["api_key"] + ":" + a["api_secret"]})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())
def document(doctype, name):
    status, body = call("frappe.client.get", {"doctype":doctype,"name":name}, get=True)
    assert status == 200, (status, body)
    return body["message"]
order = document("Work Order", sample["order"])
card = document("Job Card", sample["card"])
assert order["status"] == "Not Started" and not card.get("time_logs"), "Never replay this sample"
barrier = threading.Barrier(2)
def run(kind):
    barrier.wait(timeout=10)
    start = time.perf_counter_ns()
    if kind == "begin":
        result = call("erpnext.manufacturing.doctype.job_card.job_card.make_time_log", {"args":json.dumps({"job_card_id":sample["card"],"start_time":"2026-10-20 13:00:00","status":"Work In Progress"})})
    else:
        result = call(prefix+"close_work_order", {"work_order":order["name"],"status":"Closed","expected_modified":order["modified"],"reason":"本包计时与结束重叠验收，保留差额"})
    return {"kind":kind,"start":start,"end":time.perf_counter_ns(),"status":result[0],"body":result[1]}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures = [pool.submit(run, kind) for kind in ("begin","close")]
    results = [f.result() for f in futures]
begin, close = results
assert max(r["start"] for r in results) < min(r["end"] for r in results), "Requests did not overlap"
assert sum(r["status"] == 200 for r in results) == 1, results
order = document("Work Order", sample["order"])
card = document("Job Card", sample["card"])
open_count = sum(bool(row.get("from_time")) and not row.get("to_time") for row in card.get("time_logs",[]))
if close["status"] == 200:
    assert begin["status"] in (403,417) and order["status"] == "Closed" and open_count == 0, results
    assert "关闭" in json.dumps(begin["body"],ensure_ascii=False), begin
    winner = "close"
else:
    assert begin["status"] == 200 and close["status"] == 417 and open_count == 1 and order["status"] != "Closed", results
    assert "活动计时" in json.dumps(close["body"],ensure_ascii=False), close
    winner = "begin"
    status, body = call(prefix+"preview_production_close", {"work_order":order["name"],"expected_modified":order["modified"]}, get=True)
    assert status == 200, body
    preview = body["message"]
    status, body = call(prefix+"finish_production_timers", {"work_order":order["name"],"expected_modified":preview["modified"],"timer_fingerprint":preview["timer_fingerprint"],"end_time":"2026-10-20 14:00:00"})
    assert status == 200, body
    order = document("Work Order",sample["order"])
    status, body = call(prefix+"close_work_order", {"work_order":order["name"],"status":"Closed","expected_modified":order["modified"],"reason":"计时重叠样例正常收尾后人工结束"})
    assert status == 200, body
final = document("Work Order",sample["order"])
final_card = document("Job Card",sample["card"])
assert final["status"] == "Closed" and not final_card.get("started_time")
assert not any(not row.get("to_time") for row in final_card.get("time_logs",[]))
assert final_card["docstatus"] == 0 and final_card["total_completed_qty"] == 0
out = {"scenario":"native timer begin vs manual close on one new approved parent", "requests":2,
    "begin_http":begin["status"],"close_http":close["status"],"winner":winner,
    "client_interval_overlap_ms":(min(r["end"] for r in results)-max(r["start"] for r in results))/1e6,
    "only_one_initial_success":True,"final_closed":True,"final_open_timers":0,
    "confirmed_report_added":0,"timer_quantity":0,
    "limit":"One overlapping HTTP case; not a DB lock trace, all resource paths, shared workstation concurrency, pressure test or full G3"}
(ROOT / "evidence/B05/closeout-20261029/http-race.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(out,ensure_ascii=False))
