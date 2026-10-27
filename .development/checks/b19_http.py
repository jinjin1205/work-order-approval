"""Real socket requests against the retained B19 HTTP fixture; no transaction mocking or retries."""
import argparse
import http.client
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=("fixture", "deny", "deny-tail", "approval", "execute", "ui-actions", "ui-stop", "ui-stop-tail"))
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


def new_ui_order(label, amended_from=None):
    access = json.loads(Path(".development/private/b19-http/ui-access.json").read_text())
    template = request("operator", "GET", "/api/resource/Work%20Order/" + quote(access["draft_orders"][0], safe=""), label="read-ui-approved")["data"]
    fields = ("production_item", "bom_no", "company", "qty", "source_warehouse", "wip_warehouse", "fg_warehouse",
        "scrap_warehouse", "production_team", "planned_start_date", "use_multi_level_bom", "transfer_material_against", "skip_transfer", "from_wip_warehouse")
    new = {key: template.get(key) for key in fields}
    new["doctype"] = "Work Order"
    if amended_from:
        new["amended_from"] = amended_from
    # Only BOM-defined fields; no execution totals or scheduling from the approved order.
    new["operations"] = [{key: row.get(key) for key in ("operation", "bom", "workstation", "time_in_mins", "description", "sequence_id")}
        for row in template["operations"]]
    new["required_items"] = [{key: row.get(key) for key in ("item_code", "source_warehouse", "required_qty", "stock_uom", "rate", "operation", "include_item_in_manufacturing")}
        for row in template["required_items"]]
    return request("operator", "POST", "/api/resource/Work%20Order", new, label=label)["data"]


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
        elif args.phase == "ui-actions":
            access = json.loads(Path(".development/private/b19-http/ui-access.json").read_text())
            fixture["order"] = access["draft_orders"][1]
            order_path = "/api/resource/Work%20Order/" + quote(fixture["order"], safe="")
            order = read_order("second-ui-draft")
            assert order["workflow_state"] == "草稿"
            order = act("operator", "送审", order)
            stale = dict(order)
            order = act("reviewer", "退回", order, reason="请核对计划数量")
            assert order["workflow_state"] == "退回"
            order = request("operator", "PUT", order_path, {"qty": 12}, label="returned-quantity-edit")["data"]
            order = act("operator", "送审", order)
            act("reviewer", "审核通过", stale, status=417, exception="TimestampMismatchError")
            act("operator", "终止", order, status=417, exception="ValidationError")
            order = act("operator", "终止", order, reason="合成样例需求取消")
            assert order["workflow_state"] == "终止" and order["docstatus"] == 0
            # Preserve the browser-approved demonstration. Create one new order using native insert.
            order = new_ui_order("new-cancellation-fixture")
            fixture["order"] = order["name"]
            report["cancel_order"] = order["name"]
            order_path = "/api/resource/Work%20Order/" + quote(fixture["order"], safe="")
            order = act("operator", "送审", order)
            order = act("reviewer", "审核通过", order)
            order = act("director", "签批通过", order)
            assert order["status"] == "Not Started" and all(t["total_time_in_mins"] == 0 for t in cards())
            act("operator", "取消修订", order, status=403, exception="PermissionError", reason="无权取消")
            act("director", "取消修订", order, status=417, exception="ValidationError")
            old_approved = dict(order)
            order = act("director", "取消修订", order, reason="合成样例计划调整")
            assert order["workflow_state"] == "已取消" and order["docstatus"] == 2
            act("director", "取消修订", old_approved, status=417, exception="TimestampMismatchError", reason="旧页面重提")
        elif args.phase in ("ui-stop", "ui-stop-tail"):
            amended_from = None
            if args.phase == "ui-stop-tail":
                # Resume the recorded fixture failure through authorized cancellation/amendment, not a DB edit.
                previous = json.loads(Path("evidence/B19/chinese-flow/http-stop.json").read_text())
                assert not previous["passed"] and previous["requests"][-1]["response"]["exc_type"] == "MandatoryError"
                fixture["order"] = previous["stop_order"]
                order_path = "/api/resource/Work%20Order/" + quote(fixture["order"], safe="")
                old = read_order("failed-fixture-before-amendment")
                assert old["status"] == "Not Started" and old["material_transferred_for_manufacturing"] == 0
                old = act("director", "取消修订", old, reason="样例漏复制参与生产字段，取消后修订")
                amended_from = old["name"]
            order = new_ui_order("new-stop-fixture", amended_from=amended_from)
            fixture["order"] = order["name"]
            report["stop_order"] = order["name"]
            order_path = "/api/resource/Work%20Order/" + quote(fixture["order"], safe="")
            order = act("operator", "送审", order)
            order = act("reviewer", "审核通过", order)
            order = act("director", "签批通过", order)
            transfer = call("warehouse", WORK_ORDER + "make_stock_entry", {"work_order_id": order["name"],
                "purpose": "Material Transfer for Manufacture", "qty": 1}, "new-transfer-draft")["message"]
            transfer = call("warehouse", "frappe.client.submit", {"doc": transfer}, "new-transfer-submit")["message"]
            task = cards()[0]
            call("operator", JOB_CARD + "make_time_log", {"args": {"job_card_id": task["name"],
                "start_time": started_local, "status": "Work In Progress", "employees": []}}, "new-timer")
            timer_path = "/api/resource/Job%20Card/" + quote(task["name"], safe="")
            original_logs = request("operator", "GET", timer_path, label="timer-before-stop")["data"]["time_logs"]
            order = read_order("before-stop")
            act("director", "取消修订", order, status=403, exception="PermissionError", reason="已有事实不可取消")
            act("operator", "停止执行", order, status=403, exception="PermissionError", reason="无权停止")
            act("director", "停止执行", order, status=417, exception="ValidationError")
            order = act("director", "停止执行", order, reason="合成样例停止新增执行")
            assert order["status"] == "Stopped" and order["docstatus"] == 1
            assert request("operator", "GET", timer_path, label="timer-after-stop")["data"]["time_logs"] == original_logs
            call("operator", JOB_CARD + "make_time_log", {"args": {"job_card_id": task["name"],
                "start_time": started_local, "status": "Work In Progress", "employees": []}}, "stopped-timer-denied", 403, "PermissionError")
            blocked = dict(transfer)
            for key in ("name", "creation", "modified", "owner", "modified_by", "docstatus"):
                blocked.pop(key, None)
            call("warehouse", "frappe.client.submit", {"doc": blocked}, "stopped-transfer-denied", 403, "PermissionError")
            returned = call("warehouse", WORK_ORDER + "make_stock_return_entry", {"work_order": order["name"]}, "stopped-return-draft")["message"]
            returned = call("warehouse", "frappe.client.submit", {"doc": returned}, "stopped-return-submit")["message"]
            assert returned["docstatus"] == 1 and returned["is_return"] == 1
            call("warehouse", "frappe.client.cancel", {"doctype": "Stock Entry", "name": returned["name"]}, "cancel-stopped-return")
            assert read_order("after-return-cancel")["status"] == "Stopped"
            assert request("operator", "GET", timer_path, label="timer-after-cleanup")["data"]["time_logs"] == original_logs
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
