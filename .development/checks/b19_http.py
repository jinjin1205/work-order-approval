"""Real socket requests against the retained B19 HTTP fixture; no transaction mocking or retries."""
import argparse
import http.client
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=("fixture", "deny", "deny-tail", "approval", "execute"))
parser.add_argument("--output", required=True)
args = parser.parse_args()
fixture = json.loads(Path(".development/private/b19-http/fixture.json").read_text())
assert fixture["site"] == "xgd-b19-http.localhost" and fixture["base_url"] == "http://127.0.0.1:18088"
secrets = [v for u in fixture["users"].values() for k, v in u.items() if k in ("api_key", "api_secret")]
report = {"phase": args.phase, "started_utc": datetime.now(timezone.utc).isoformat(), "requests": [], "passed": False}
started_local = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
WORK_ORDER = "erpnext.manufacturing.doctype.work_order.work_order."
JOB_CARD = "erpnext.manufacturing.doctype.job_card.job_card."
order_path = "/api/resource/Work%20Order/" + quote(fixture["order"], safe="")


def request(actor, method, path, data=None, *, status=200, exception=None, label):
    credentials = fixture["users"][actor]
    entry = {"label": label, "actor": actor, "method": method, "path": path, "expected_status": status}
    report["requests"].append(entry)
    connection = http.client.HTTPConnection("127.0.0.1", 18088, timeout=60)
    try:
        connection.request(method, path, body=json.dumps(data) if data is not None else None, headers={
            "Host": fixture["site"], "Content-Type": "application/json", "Accept": "application/json",
            "Authorization": "token " + credentials["api_key"] + ":" + credentials["api_secret"],
        })
        response = connection.getresponse()
        entry["status"] = response.status
        raw = response.read().decode()
    finally:
        connection.close()
    for secret in secrets:
        raw = raw.replace(secret, "[REDACTED]")
    payload = json.loads(raw)
    entry["response"] = payload
    assert response.status == status, f"{label}: HTTP {response.status}, expected {status}"
    if exception:
        assert payload.get("exc_type") == exception, f"{label}: unexpected exception type"
    entry["http_expectation_met"] = True
    return payload


def call(actor, method, data, label, status=200, exception=None):
    return request(actor, "POST", "/api/method/" + method, data, status=status, exception=exception, label=label)


def read_order(label="read-order"):
    return request("operator", "GET", order_path, label=label)["data"]


def act(actor, action, order, *, status=200, exception=None, reason=None):
    data = {"work_order": fixture["order"], "action": action, "expected_modified": order["modified"]}
    if reason:
        data["reason"] = reason
    result = call(actor, WORK_ORDER + "apply_production_approval", data, actor + "-" + action, status, exception)
    return result.get("message")


def cards():
    query = urlencode({"fields": json.dumps(["name", "docstatus", "total_completed_qty", "total_time_in_mins"]),
        "filters": json.dumps([["work_order", "=", fixture["order"]]])})
    return request("operator", "GET", "/api/resource/Job%20Card?" + query, label="read-own-tasks")["data"]


with Path(args.output).open("x") as output:
    try:
        if args.phase == "fixture":
            for actor, credentials in fixture["users"].items():
                response = request(actor, "GET", "/api/method/frappe.auth.get_logged_user", label="identity-" + actor)
                assert response["message"] == credentials["email"]
            order = read_order()
            assert order["workflow_state"] == "草稿" and order["qty"] == 10 and order["docstatus"] == 0
        elif args.phase in ("deny", "deny-tail"):
            order = read_order()
            assert order["workflow_state"] == "草稿"
            if args.phase == "deny":
                request("operator", "PUT", order_path, {"workflow_state": "待签批", "approval_reviewed_by": fixture["users"]["operator"]["email"]},
                    status=403, exception="PermissionError", label="resource-approval-forgery")
                call("director", "frappe.client.submit", {"doc": order}, "direct-submit", 403, "PermissionError")
                call("operator", "frappe.model.workflow.apply_workflow", {"doc": order, "action": "送审"}, "native-workflow-bypass", 403, "PermissionError")
                # Native bulk catches the business error. HTTP 200 is not treated as approval success.
                call("operator", "frappe.model.workflow.bulk_workflow_approval", {
                    "doctype": "Work Order", "docnames": json.dumps([fixture["order"]]), "action": "送审"}, "native-bulk-workflow")
                assert read_order("read-after-bulk-workflow")["workflow_state"] == "草稿"
                result = call("operator", "frappe.client.bulk_update", {"docs": json.dumps([{
                    "doctype": "Work Order", "docname": fixture["order"], "workflow_state": "待审核", "qty": 99}])}, "generic-bulk-save")
                assert len(result["message"]["failed_docs"]) == 1
                request("operator", "POST", "/api/resource/Job%20Card", fixture["job_payload"], status=403, exception="PermissionError", label="pending-manual-task")
            call("operator", JOB_CARD + "make_time_log", {"args": {"job_card_id": fixture["legacy_timer_card"],
                "start_time": started_local, "status": "Work In Progress", "employees": []}}, "legacy-unapproved-timer", 403, "PermissionError")
            call("warehouse", "frappe.client.submit", {"doc": fixture["stock_payload"]}, "pending-stock-submit", 403, "PermissionError")
            call("warehouse", "frappe.client.submit", {"doc": fixture["indirect_stock_payload"]}, "indirect-unapproved-stock", 403, "PermissionError")
            final = read_order("read-after-all-denials")
            assert final["workflow_state"] == "草稿" and final["qty"] == 10 and final["docstatus"] == 0
        elif args.phase == "approval":
            order = read_order()
            order = act("operator", "送审", order)
            assert order["workflow_state"] == "待审核"
            old_view = dict(order)
            act("other", "审核通过", order, status=403, exception="PermissionError")
            act("operator", "审核通过", order, status=403, exception="PermissionError")
            order = act("reviewer", "退回", order, reason="调整数量")
            order = request("operator", "PUT", order_path, {"qty": 11}, label="edit-returned-basis")["data"]
            assert order["qty"] == 11
            order = act("operator", "送审", order)
            act("reviewer", "审核通过", old_view, status=417, exception="TimestampMismatchError")
            order = act("reviewer", "审核通过", order)
            assert order["workflow_state"] == "待签批" and order["docstatus"] == 0
            act("reviewer", "签批通过", order, status=403, exception="PermissionError")
            order = act("director", "签批通过", order)
            assert order["workflow_state"] == "已批准" and order["docstatus"] == 1 and order["status"] == "Not Started"
            tasks = cards()
            assert len(tasks) == 3 and all(t["docstatus"] == 0 and t["total_completed_qty"] == 0 and t["total_time_in_mins"] == 0 for t in tasks)
        else:
            order = read_order()
            assert order["workflow_state"] == "已批准" and order["docstatus"] == 1
            task = cards()[0]
            call("operator", JOB_CARD + "make_time_log", {"args": {"job_card_id": task["name"],
                "start_time": started_local, "status": "Work In Progress", "employees": []}}, "approved-timer")
            task = request("operator", "GET", "/api/resource/Job%20Card/" + quote(task["name"], safe=""), label="read-timer-result")["data"]
            assert len(task["time_logs"]) == 1 and task["time_logs"][0]["from_time"]
            result = call("warehouse", "frappe.client.submit", {"doc": fixture["stock_payload"]}, "approved-stock-submit")["message"]
            assert result["docstatus"] == 1 and result["work_order"] == fixture["order"]
        report["passed"] = True
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")
print(json.dumps({"phase": args.phase, "requests": len(report["requests"]), "passed": report["passed"]}))
