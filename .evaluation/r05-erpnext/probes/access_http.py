"""Ordinary-account HTTP probes. Review first; runs only against loopback r05 site.

No credentials are logged. X-R05-Request-Id is an evidence label, NOT a native
idempotency contract. Separate invocations need separate exclusive output paths.
"""
import argparse
import copy
import json
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--setup", required=True)
p.add_argument("--secrets", required=True)
p.add_argument("--output", required=True)
p.add_argument("--section", choices=["access", "concurrency", "retry", "delete", "recovery"], required=True)
args = p.parse_args()
setup = json.loads(Path(args.setup).read_text())
credentials = json.loads(Path(args.secrets).read_text())
base = credentials["base_url"].rstrip("/")
if base != "http://127.0.0.1:18085" or setup["site"] != "r05.localhost" or setup["prefix"] != "R05F-A":
    raise RuntimeError("Only reviewed loopback r05 fixture is permitted")
output = Path(args.output)
if output.exists():
    raise RuntimeError("Evidence output exists; do not overwrite or blindly rerun")
report = {"section": args.section, "started_utc": datetime.now(timezone.utc).isoformat(),
          "fixture_setup": args.setup, "base_url": base, "requests": [], "cases": [],
          "limits": ["Synthetic local ordinary-account native API subset only.",
                     "Request labels are not native idempotency keys.",
                     "No lost-response or injected pre-commit failure was tested."]}
lock = threading.Lock()

def request(actor, method, path, label, body=None, params=None):
    credential = credentials["users"][actor]
    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Authorization": "token " + credential["api_key"] + ":" + credential["api_secret"],
               "Host": "r05.localhost", "Accept": "application/json", "X-R05-Request-Id": label}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    entry = {"id": label, "actor": actor, "user": credential["email"], "method": method,
             "path": path, "params": params, "input": body,
             "sent_utc": datetime.now(timezone.utc).isoformat(), "start_ns": time.monotonic_ns()}
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            entry["status"] = response.status
            content = response.read().decode()
    except urllib.error.HTTPError as exc:
        entry["status"] = exc.code
        content = exc.read().decode()
    except (urllib.error.URLError, TimeoutError) as exc:
        # Record transport failure as unknown commit state, never retry implicitly.
        entry["transport_error"] = str(exc)
        content = ""
    entry["end_ns"] = time.monotonic_ns()
    entry["received_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        entry["response"] = json.loads(content) if content else None
    except json.JSONDecodeError:
        entry["response_text"] = content
    with lock:
        report["requests"].append(entry)
    return entry

def resource(doctype, name=None):
    return "/api/resource/" + urllib.parse.quote(doctype, safe="") + ("/" + urllib.parse.quote(name, safe="") if name else "")

def get_doc(actor, doctype, name, label):
    response = request(actor, "GET", resource(doctype, name), label)
    if response.get("status") != 200 or "data" not in response.get("response", {}):
        raise RuntimeError(f"Required ordinary GET failed: {label}; inspect recorded response")
    return response["response"]["data"]

def snapshot(label, actor="a"):
    fixture = setup["fixtures"][label]
    wo = get_doc(actor, "Work Order", fixture["work_order"], label + "-snapshot-work-order")
    listing = request(actor, "GET", resource("Job Card"), label + "-snapshot-card-list", params={
        "fields": json.dumps(["name", "docstatus", "for_quantity", "total_completed_qty", "process_loss_qty", "status"]),
        "filters": json.dumps({"work_order": fixture["work_order"]}), "limit_page_length": 100})
    rows = listing.get("response", {}).get("data", [])
    docs = [get_doc(actor, "Job Card", row["name"], label + "-snapshot-card-" + row["name"]) for row in rows]
    return {"work_order": wo, "cards": docs,
            "effective_completed": sum(d["total_completed_qty"] for d in docs if d["docstatus"] == 1),
            "effective_loss": sum(d["process_loss_qty"] for d in docs if d["docstatus"] == 1)}

def access_probe():
    f = setup["fixtures"]
    for actor in credentials["users"]:
        request(actor, "GET", "/api/method/frappe.auth.get_logged_user", "identity-" + actor)
    for actor in ["a", "b", "outside", "none"]:
        for label in ["ALL", "DEPT", "PERSON", "B"]:
            request(actor, "GET", resource("Job Card", f[label]["job_card"]), f"get-{actor}-{label}")
        request(actor, "GET", resource("Job Card"), "list-" + actor, params={
            "fields": json.dumps(["name", "work_order", "operation"]),
            "filters": json.dumps({"work_order": ["in", [f[k]["work_order"] for k in ["ALL", "DEPT", "PERSON", "B"]]]}),
            "limit_page_length": 100})
    for actor, label in [("a", "DEPT"), ("a", "B"), ("outside", "DEPT"), ("none", "DEPT")]:
        request(actor, "PUT", resource("Job Card", f[label]["job_card"]), f"write-{actor}-{label}",
                {"remarks": f"R05F authorized/denied write probe {actor} {label}"})
    for actor, label in [("a", "B"), ("outside", "DEPT"), ("none", "DEPT")]:
        request(actor, "DELETE", resource("Job Card", f[label]["job_card"]), f"delete-deny-{actor}-{label}")
    # Native whitelisted reporting method delegates to save. Check an authorized
    # start and same-doctype forbidden target; this mutates only the new DEPT card.
    start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for actor, label in [("a", "DEPT"), ("a", "B"), ("none", "DEPT")]:
        request(actor, "POST", "/api/method/erpnext.manufacturing.doctype.job_card.job_card.make_time_log",
                f"time-log-{actor}-{label}", {"args": {"job_card_id": f[label]["job_card"],
                    "start_time": start, "employees": [], "status": "Work In Progress"}})
    # A separate whitelisted helper uses get_all internally. Test it explicitly,
    # never substitute its answer for an authorized resource/list read.
    for actor, label in [("a", "DEPT"), ("a", "B"), ("none", "DEPT")]:
        request(actor, "GET", "/api/method/erpnext.manufacturing.doctype.job_card.job_card.get_operation_details",
                f"operation-helper-{actor}-{label}", params={"work_order": f[label]["work_order"], "operation": f[label]["operation"]})
    for actor in ["stock", "a", "none"]:
        for label in ["DEPT", "B"]:
            request(actor, "GET", resource("Stock Entry", f[label]["stock_entry"]), f"stock-get-{actor}-{label}")
            request(actor, "PUT", resource("Stock Entry", f[label]["stock_draft"]), f"stock-write-{actor}-{label}",
                    {"remarks": f"R05F stock scope probe {actor} {label}"})
    report["cases"].append({"case": "access", "DEPT_after": snapshot("DEPT"), "B_after": snapshot("B", "outside")})

def concurrency_probe():
    for label, quantity in [("CONC2", 2), ("CONC1", 1), ("SPLIT1", 1)]:
        before = snapshot(label)
        fixture = setup["fixtures"][label]
        original = get_doc("a", "Job Card", fixture["job_card"], label + "-read-a")
        other = get_doc("b", "Job Card", fixture.get("second_pending_card", fixture["job_card"]), label + "-read-b")
        expected_pending = 1 if label == "SPLIT1" else 2
        if before["effective_completed"] != 8 or original["docstatus"] != 0 or original["for_quantity"] != expected_pending or original["time_logs"]:
            raise RuntimeError("Concurrency initial state is not the reviewed effective8 plus empty pending card(s)")
        if label != "SPLIT1" and original["modified"] != other["modified"]:
            raise RuntimeError("Concurrent clients did not read the same original version")
        method = "save" if label == "CONC1" else "submit"
        barrier = threading.Barrier(2)
        def worker(actor, doc, offset):
            payload = copy.deepcopy(doc)
            start = datetime.now() + timedelta(minutes=5 + offset * 2)
            payload["time_logs"] = [{"doctype": "Job Card Time Log",
                "from_time": start.strftime("%Y-%m-%d %H:%M:%S"),
                "to_time": (start + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "completed_qty": quantity}]
            payload["remarks"] = f"R05F {label} distinct request from {actor}"
            barrier.wait(timeout=20)
            return request(actor, "POST", "/api/method/frappe.client." + method, f"{label}-{actor}", {"doc": payload})
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(worker, "a", original, 0)
            second = pool.submit(worker, "b", other, 1)
            results = [first.result(), second.result()]
        overlap = min(r["end_ns"] for r in results) - max(r["start_ns"] for r in results)
        after_parallel = snapshot(label)
        if label == "CONC1":
            # Ordinary UI flow saves first, so native before_save computes loss.
            # Direct submit of qty1 against batch2/loss0 would only test invalid
            # input, not the requested same-card concurrent lawful save branch.
            saved = get_doc("a", "Job Card", fixture["job_card"], label + "-saved-before-submit")
            request("a", "POST", "/api/method/frappe.client.submit", label + "-submit-saved", {"doc": saved})
        after = snapshot(label)
        report["cases"].append({"case": label, "each_requested": quantity, "before": before,
            "request_ids": [r["id"] for r in results], "client_request_intervals_overlap": overlap > 0,
            "overlap_ms": overlap / 1_000_000, "statuses": [r.get("status") for r in results],
            "parallel_method": method, "after_parallel": after_parallel,
            "after": after, "net_effective_completed": after["effective_completed"] - before["effective_completed"],
            "native_scope": ("Distinct pending batch1 Job Cards under the same Work Order operation; both requests individually legal."
                             if label == "SPLIT1" else "Same pending whole Job Card and two stale document versions; native loss calculation remains enabled. CONC1 saves in parallel then submits retained current state.")})

def retry_probe():
    label = "RETRY"
    fixture = setup["fixtures"][label]
    case = {"case": label, "before": snapshot(label)}
    card = get_doc("a", "Job Card", fixture["job_card"], "retry-initial-card")
    if case["before"]["effective_completed"] != 8 or card["time_logs"]:
        raise RuntimeError("Retry fixture is not fresh")
    start = datetime.now() + timedelta(minutes=5)
    endpoint = "/api/method/erpnext.manufacturing.doctype.job_card.job_card.make_time_log"
    request("a", "POST", endpoint, "retry-start", {"args": {"job_card_id": card["name"],
        "start_time": start.strftime("%Y-%m-%d %H:%M:%S"), "employees": [], "status": "Work In Progress"}})
    complete = {"args": {"job_card_id": card["name"], "complete_time": (start + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
                         "completed_qty": 1, "employees": [], "status": "Complete"}}
    request("a", "POST", endpoint, "R05F-K-01", complete)
    case["after_first_complete"] = snapshot(label)
    request("a", "POST", endpoint, "R05F-K-01", complete)
    case["after_same_complete"] = snapshot(label)
    current = get_doc("a", "Job Card", card["name"], "retry-before-submit")
    submit = {"doc": current}
    request("a", "POST", "/api/method/frappe.client.submit", "R05F-SUBMIT-K-01", submit)
    case["after_first_submit"] = snapshot(label)
    request("a", "POST", "/api/method/frappe.client.submit", "R05F-SUBMIT-K-01", submit)
    case["after_same_submit"] = snapshot(label)
    report["cases"].append(case)

def delete_probe():
    fixture = setup["fixtures"]["DELETE"]
    case = {"case": "cancelled-original-deletion", "before": snapshot("DELETE")}
    original = get_doc("a", "Job Card", fixture["job_card"], "delete-original")
    if original["docstatus"] != 1 or original["total_completed_qty"] != 10 or not fixture["finished_item"].startswith("R05F-A-DELETE-"):
        raise RuntimeError("Deletion probe is restricted to its new synthetic submitted10 fixture")
    edited_rows = copy.deepcopy(original["time_logs"])
    edited_rows[0]["completed_qty"] = 8
    request("a", "PUT", resource("Job Card", original["name"]), "submitted-edit-quantity", {"time_logs": edited_rows})
    request("a", "DELETE", resource("Job Card", original["name"]), "submitted-delete")
    case["after_submitted_attempts"] = snapshot("DELETE")
    request("a", "POST", "/api/method/frappe.client.cancel", "ordinary-cancel", {"doctype": "Job Card", "name": original["name"]})
    case["after_cancel_before_delete"] = snapshot("DELETE")
    request("a", "DELETE", resource("Job Card", original["name"]), "ordinary-cancelled-delete")
    request("a", "GET", resource("Job Card", original["name"]), "read-after-delete")
    case["after_delete"] = snapshot("DELETE")
    report["cases"].append(case)

def recovery_probe():
    prior_path = output.parent / "concurrency.json"
    prior = json.loads(prior_path.read_text())
    failed = [r for r in prior["requests"] if r["id"].startswith("SPLIT1-")
              and r.get("response", {}).get("exc_type") == "QueryDeadlockError"]
    if len(failed) != 1:
        raise RuntimeError("Recovery requires exactly one recorded SPLIT1 deadlock")
    original = failed[0]
    before = snapshot("SPLIT1")
    current = get_doc(original["actor"], "Job Card", original["input"]["doc"]["name"], "split-recovery-current")
    if before["effective_completed"] != 9 or current["docstatus"] != 0 or current["time_logs"] or current["for_quantity"] != 1:
        raise RuntimeError("Failed card is not an empty unsubmitted1 with effective total9; no recovery write")
    current["time_logs"] = copy.deepcopy(original["input"]["doc"]["time_logs"])
    current["remarks"] = "R05F one explicit recovery after " + original["id"]
    result = request(original["actor"], "POST", "/api/method/frappe.client.submit",
                     original["id"] + "-recovery1", {"doc": current})
    report["cases"].append({"case": "SPLIT1-one-explicit-recovery", "prior_evidence": str(prior_path),
        "original_request_id": original["id"], "recovery_request_id": result["id"],
        "before": before, "after": snapshot("SPLIT1"), "status": result.get("status"),
        "limitation": "Separate sequential recovery; never combine with original two concurrent requests as a concurrency pass."})

try:
    {"access": access_probe, "concurrency": concurrency_probe, "retry": retry_probe,
     "delete": delete_probe, "recovery": recovery_probe}[args.section]()
except Exception:
    report["probe_error"] = traceback.format_exc()
    raise
finally:
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    with output.open("x") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"section": args.section, "output": str(output), "request_count": len(report["requests"]),
                      "has_probe_error": "probe_error" in report}))
