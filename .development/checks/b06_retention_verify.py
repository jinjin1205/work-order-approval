"""One new isolated-station report verifies only the corrected retention boundary."""
import hashlib
import http.client
import json
import subprocess
import uuid
from pathlib import Path

p = Path(".development/private/b06-retention-20261029")
a = json.loads((p / "access.json").read_text())
assert a["site"] == "xgd-b08-http.localhost" and a["workstation"]
assert not (p / "summary.json").exists(), "Never replay a completed correction case"
historical = Path("evidence/B06/tasks-20261029/old-row-audit.json")
original_digest = hashlib.sha256(historical.read_bytes()).hexdigest()

def control(mode):
    return json.loads(subprocess.check_output(["docker", "exec", "-w", "/home/frappe/frappe-bench", "xgd-b08-check", "env/bin/python",
        "/b01/b06_tasks_control.py", mode, "b06-retention"], text=True))

state = control("state")
assert state["reports"] == 0
if state["state"] == "草稿":
    control("prepare-retention")
    control("approve")
else:
    assert state["state"] == "已批准"
state = control("state")
assert state["workstations"] == [a["workstation"]] * 3
assert [float(row["plan"]) for row in state["tasks"]] == [1, 2, 3]
actor = a["actors"]["reporter"]
responses = []

def post(method, arguments):
    connection = http.client.HTTPConnection("127.0.0.1", 18090, timeout=30)
    try:
        connection.request("POST", "/api/method/erpnext.manufacturing.doctype.job_card.job_card." + method,
            body=json.dumps(arguments).encode(), headers={"Host": a["site"], "Content-Type": "application/json",
                "Authorization": "token " + actor["api_key"] + ":" + actor["api_secret"]})
        response = connection.getresponse()
        body = json.loads(response.read())
        responses.append({"method": method, "status": response.status, "body": body})
        (p / "responses.json").write_text(json.dumps(responses, ensure_ascii=False, indent=2))
        assert response.status == 200, "See private response; do not retry mutation"
        return body["message"]
    finally:
        connection.close()

args = {"work_order": a["order"], "operation_id": state["tasks"][0]["name"],
    "from_time": "2026-10-20 15:00:00", "to_time": "2026-10-20 16:00:00"}
preview = post("preview_production_report_time", args)
post("confirm_production_report", {**args, "request_id": uuid.uuid4().hex, "good_quantity": 1, "bad_quantity": 0,
    "context_fingerprint": preview["context_fingerprint"]})
raw = subprocess.check_output(["docker", "exec", "-w", "/home/frappe/frappe-bench", "xgd-b08-check", "env/bin/python",
    "/b01/b06_tasks_preserve.py", "--case", "b06-retention"], text=True)
summary = json.loads(raw)
assert summary["strict_old_row_retention_result"] == "OK" and summary["old_tables_exact_rows_preserved"] == 23
assert hashlib.sha256(historical.read_bytes()).hexdigest() == original_digest
assert json.loads(historical.read_text())["strict_old_row_retention_result"] == "FAILED"
summary.update({"single_new_http_report_verified": True, "historical_failure_preserved": True,
    "historical_field_diff_reconstructed": False, "product_source_changed": False, "unaffected_20_methods_reused": True})
(p / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(summary, ensure_ascii=False))
