"""Read-only native HTTP checks for the isolated B02 fixture; no retries."""
import argparse
import http.client
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

parser = argparse.ArgumentParser()
parser.add_argument("--secrets", default=".development/private/b02-http.json")
parser.add_argument("--phase", choices=("initial", "revoked"), required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
fixture = json.loads(Path(args.secrets).read_text())
assert fixture["site"] == "xgd-test.localhost"
assert fixture["base_url"] == "http://127.0.0.1:18087"
assert fixture["prefix"].startswith("B02-")
secrets = [value for user in fixture["users"].values() for key, value in user.items() if key in {"api_key", "api_secret"}]
report = {
    "phase": args.phase, "site": fixture["site"], "base_url": fixture["base_url"],
    "prefix": fixture["prefix"], "started_utc": datetime.now(timezone.utc).isoformat(),
    "requests": [], "passed": False,
    "limits": ["Three read helpers only; no task-scope, report submission, stock, AI or concurrency acceptance."],
}
module = "erpnext.manufacturing.doctype.job_card.job_card."


def request(actor, method, params, label, expected_status, expected_message=None, forbidden=()):
    credentials = fixture["users"][actor]
    path = "/api/method/" + method
    if params:
        path += "?" + urlencode(params)
    entry = {"case": label, "actor": actor, "email": credentials["email"],
             "method": "GET", "path": path, "expected_status": expected_status}
    report["requests"].append(entry)
    connection = http.client.HTTPConnection("127.0.0.1", 18087, timeout=30)
    try:
        connection.request("GET", path, headers={
            "Host": fixture["site"], "Accept": "application/json",
            "Authorization": "token " + credentials["api_key"] + ":" + credentials["api_secret"],
        })
        response = connection.getresponse()
        entry["status"] = response.status
        content = response.read().decode("utf-8")
    except (OSError, http.client.HTTPException) as error:
        entry["transport_error"] = type(error).__name__
        raise RuntimeError(f"{label}: transport failed; no automatic retry") from None
    finally:
        connection.close()
    # Preserve the response for diagnosis without retaining any issued credential.
    for secret in secrets:
        content = content.replace(secret, "[REDACTED]")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = {"response_text": content}
    entry["response"] = payload
    assert entry["status"] == expected_status, f"{label}: HTTP {entry['status']}, expected {expected_status}"
    if expected_status == 403:
        assert payload.get("exc_type") == "PermissionError", f"{label}: denial was not a PermissionError"
    else:
        assert "message" in payload, f"{label}: no native response message"
        if expected_message is not None:
            entry["expected_message"] = expected_message
            assert payload["message"] == expected_message, f"{label}: unexpected result"
    for value in forbidden:
        assert value not in content, f"{label}: restricted data leaked"
    entry["passed"] = True
    return payload.get("message")


output = Path(args.output)
with output.open("x") as stream:
    try:
        allowed, restricted = fixture["orders"]
        operation = fixture["operations"][0]
        search = {"doctype": "Operation", "txt": "", "searchfield": "name", "start": 0, "page_len": 20}
        dates = {"start": "2026-10-19", "end": "2026-10-22"}
        if args.phase == "initial":
            for actor in ("reader", "outsider"):
                request(actor, "frappe.auth.get_logged_user", {}, "identity-" + actor, 200,
                        fixture["users"][actor]["email"])
            request("reader", module + "get_operation_details", {"work_order": allowed, "operation": operation},
                    "reader-details-allowed", 200, [{"name": fixture["operation_rows"][0], "idx": 1}])
            request("reader", module + "get_operations", {**search, "filters": json.dumps({"work_order": allowed})},
                    "reader-search-allowed", 200, [[name] for name in fixture["operations"]])
            request("reader", module + "get_operation_details", {"work_order": restricted, "operation": operation},
                    "reader-details-restricted", 403, forbidden=(fixture["operation_rows"][1],))
            request("reader", module + "get_operations", {**search, "filters": json.dumps({"work_order": restricted})},
                    "reader-search-restricted", 403, forbidden=(fixture["operation_rows"][1],))
            request("outsider", module + "get_operation_details", {"work_order": allowed, "operation": operation},
                    "outsider-details", 403, forbidden=fixture["operation_rows"])
            request("outsider", module + "get_operations", {**search, "filters": json.dumps({"work_order": allowed})},
                    "outsider-search", 403, forbidden=fixture["operation_rows"])
            request("outsider", module + "get_job_details", dates, "outsider-calendar", 403,
                    forbidden=fixture["cards"])
            events = request("reader", module + "get_job_details", dates, "reader-calendar", 200,
                             forbidden=(fixture["cards"][1], fixture["prefix"] + "-受限"))
            report["requests"][-1]["passed"] = False
            report["requests"][-1]["expected_visible_cards"] = [fixture["cards"][0]]
            assert isinstance(events, list) and len(events) == 1, "reader-calendar: unexpected event count"
            assert events[0]["name"] == fixture["cards"][0], "reader-calendar: wrong visible card"
            assert events[0]["from_time"] == "2026-10-20 08:00:00", "reader-calendar: start time changed"
            assert events[0]["to_time"] == "2026-10-20 08:01:00", "reader-calendar: end time changed"
            report["requests"][-1]["passed"] = True
            request("reader", module + "get_job_details", {**dates, "filters": json.dumps({"name": fixture["cards"][1]})},
                    "reader-calendar-forced-restricted", 200, [])
            request("reader", module + "get_operations", search, "reader-search-missing-parent", 200, [])
        else:
            request("reader", "frappe.auth.get_logged_user", {}, "revoked-token-identity", 200,
                    fixture["users"]["reader"]["email"])
            request("reader", module + "get_operation_details", {"work_order": allowed, "operation": operation},
                    "revoked-details", 403, forbidden=fixture["operation_rows"])
            request("reader", module + "get_operations", {**search, "filters": json.dumps({"work_order": allowed})},
                    "revoked-search", 403, forbidden=fixture["operation_rows"])
            request("reader", module + "get_job_details", dates, "revoked-calendar", 403,
                    forbidden=fixture["cards"])
        report["passed"] = True
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

print(json.dumps({"phase": args.phase, "requests": len(report["requests"]), "passed": report["passed"],
                  "evidence": str(output)}, ensure_ascii=False))
