"""One I05 POST through a one-request loopback proxy, then GET-only recovery.

The proxy never sends downstream response bytes. It buffers the real upstream
response, observes committed facts through a new DB process, then disconnects.
Run only with --run after dedicated setup; no POST retry or fixture replay.
"""
import argparse
import datetime
import hashlib
import http.client
import json
import math
import os
import socket
import socketserver
import subprocess
import threading
import time
import traceback
from pathlib import Path

from b08_distinct_concurrency_http import API, invariant_order, request, response_value, sha, write_json

PRIVATE = Path(".development/private/b08-recovery")
EVIDENCE = Path("evidence/B08/recovery-20261028")
SCRIPT = "/b01/b08_recovery_fixture.py"
SCRIPTS = ("b08_recovery_fixture.py", "b08_response_loss_http.py",
           "b08_distinct_concurrency_fixture.py", "b08_distinct_concurrency_http.py")


def stamp():
    return {"monotonic_ns": time.perf_counter_ns(), "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def container_json(container, *args):
    result = subprocess.run(["docker", "exec", container, "env/bin/python", SCRIPT, *args],
                            text=True, capture_output=True, timeout=45)
    if result.returncode:
        write_json(PRIVATE / ("db-error-" + args[0] + ".json"),
                   {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        raise RuntimeError("Dedicated DB observer failed; output is private")
    return json.loads(result.stdout)


def snapshot(label):
    observation = container_json("xgd-b08-check", "snapshot", label)
    target = PRIVATE / (label + ".json")
    assert not target.exists(), "Never replace a saved observation"
    subprocess.run(["docker", "cp", "xgd-b08-check:/tmp/b08-recovery-private/" + label + ".json", str(target)],
                   capture_output=True, check=True, timeout=15)
    target.chmod(0o600)
    state = json.loads(target.read_text())
    assert sha(state) == observation["state_sha256"]
    return state, observation


def verify(sample, before, committed, after, recovered, upstream):
    data = sample["cases"]["I05"]
    actor = sample["actors"]["A"]
    assert after == committed, "GET recovery changed facts or derived values"
    facts = [row for row in after["cards"] if row.get("report_request_id")]
    assert len(facts) == 1
    card = facts[0]
    assert card["name"] == recovered["name"] == upstream["message"]["name"]
    assert card["report_request_id"] == data["request_id"] and card["owner"] == actor["user"]
    assert card["docstatus"] == recovered["docstatus"] == 1
    assert recovered["time_context"] == json.loads(card["report_time_context"])
    assert card["work_order"] == data["order"] and card["operation_id"] == data["operation_id"]
    assert card["total_completed_qty"] == recovered["good"] == 2 and card["process_loss_qty"] == recovered["bad"] == 0
    assert card["total_time_in_mins"] == 60 and card["report_effective_seconds"] == 3600
    old_cards, new_cards = before["global_cards"]["rows"], after["global_cards"]["rows"]
    assert all(new_cards.get(name) == value for name, value in old_cards.items())
    assert set(new_cards) - set(old_cards) == {card["name"]}
    old_logs = {row["name"]: row for row in before["global_time_logs"]}
    all_logs = {row["name"]: row for row in after["global_time_logs"]}
    assert all(all_logs.get(name) == value for name, value in old_logs.items())
    added = [row for name, row in all_logs.items() if name not in old_logs]
    assert len(added) == 1 and added[0]["parent"] == card["name"] and added[0]["parent"] in new_cards
    log = added[0]
    assert log["employee"] == actor["employee"] and log["completed_qty"] == 2 and log["time_in_mins"] == 60
    assert log["from_time"] == data["inputs"]["from_time"] and log["to_time"] == data["inputs"]["to_time"]
    assert invariant_order(before["order"], data["operation_id"]) == invariant_order(after["order"], data["operation_id"])
    assert before["stock"] == after["stock"]
    order = after["order"]
    operation = next(row for row in order["operations"] if row["name"] == data["operation_id"])
    assert order["qty"] == 10 and operation["completed_qty"] == 2 and operation["process_loss_qty"] == 0
    assert operation["actual_operation_time"] == order["lead_time"] == 60
    assert order["status"] == "In Process" and operation["status"] == "Work in Progress"
    assert order["actual_start_date"] == operation["actual_start_time"] == log["from_time"]
    assert order["actual_end_date"] == operation["actual_end_time"] == log["to_time"]
    assert not order["produced_qty"] and not order["material_transferred_for_manufacturing"]
    precision = after["operation_cost_precisions"][operation["name"]]
    assert math.isclose(operation["actual_operating_cost"], operation["hour_rate"], rel_tol=0, abs_tol=0.5 * 10 ** -precision)
    assert math.isclose(order["actual_operating_cost"], sum(row["actual_operating_cost"] for row in order["operations"]), abs_tol=1e-6)
    expected_total = order["additional_operating_cost"] + (order["actual_operating_cost"] or order["planned_operating_cost"]) + order["corrective_operation_cost"]
    assert math.isclose(order["total_operating_cost"], expected_total, abs_tol=1e-6)
    return {"passed": True, "new_facts": 1, "new_time_rows": 1, "orphan_time_rows": 0,
            "recovery_returns_original": True, "recovery_changes_no_values": True,
            "plan_route_other_tasks_and_old_cards_logs_unchanged": True, "stock_unchanged": True,
            "final": {"plan": 10, "good": 2, "bad": 0, "remaining": 8, "minutes": 60,
                      "task_status": operation["status"], "work_order_status": order["status"],
                      "hour_rate": operation["hour_rate"], "actual_operating_cost": order["actual_operating_cost"]},
            "nonzero_cost_verified": operation["hour_rate"] != 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", required=True)
    parser.parse_args()
    os.umask(0o077)
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    PRIVATE.chmod(0o700)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sample = json.loads((PRIVATE / "fixture.json").read_text())
    assert sample["site"] == "xgd-b08-http.localhost" and sample["base_url"] == "http://127.0.0.1:18090"
    assert not (PRIVATE / "started.json").exists(), "Never replay a started I05 batch"
    source = {name: container_json(name, "source") for name in ("xgd-b08-check", "xgd-b08-ui")}
    scripts = {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest() for name in SCRIPTS}
    assert all(item["scripts"] == scripts for item in source.values())
    beginning = {"at": stamp(), "scripts_before_actions": scripts, "runtime_before_actions": source,
                 "scope": "I05 real HTTP; one POST and GET-only recovery", "post_retry_limit": 0}
    write_json(PRIVATE / "started.json", beginning)
    write_json(EVIDENCE / "http-i05-before.json", beginning)
    raw, events, proxy = [], {}, {"upstream_post_attempts": 0, "downstream_response_bytes": 0}
    summary = {"passed": False, "scripts_before_actions": scripts, "confirmation_post_retries": 0}
    server = worker = client = None
    try:
        before, _ = snapshot("before")
        assert not any(row.get("report_request_id") for row in before["cards"]) and not before["logs"]
        identity = request(sample, "A", "frappe.auth.get_logged_user")
        raw.append({"step": "identity", **identity})
        assert response_value(identity) == sample["actors"]["A"]["user"]
        permissions = []
        data = sample["cases"]["I05"]
        for doctype, docname, permission, expected in (("Work Order", data["order"], "read", True),
            ("Work Order", data["order"], "write", False), ("Stock Entry", "", "create", False),
            ("Job Card", "", "create", True)):
            result = request(sample, "A", "frappe.client.has_permission",
                             {"doctype": doctype, "docname": docname, "perm_type": permission})
            raw.append({"step": "permission", **result})
            actual = response_value(result)["has_permission"]
            permissions.append({"doctype": doctype, "permission": permission, "actual": actual, "expected": expected})
            assert actual is expected
        preview = request(sample, "A", API + "preview_production_report_time", data["inputs"])
        raw.append({"step": "preview", **preview})
        preview_value = response_value(preview)
        assert preview_value["effective_seconds"] == 3600
        # The recovery side knows only this pre-existing key, never the proxy's buffered result.
        recovery_key = data["request_id"]
        body = {**data["inputs"], "request_id": recovery_key, "context_fingerprint": preview_value["context_fingerprint"]}
        body_bytes = json.dumps(body).encode()
        write_json(PRIVATE / "original-request.json", body)
        summary.update({"permissions": permissions, "request_key_sha256": sha(recovery_key),
                        "business_content_sha256": sha(body), "actor_identity_sha256": sha(sample["actors"]["A"]["user"])})
        path = "/api/method/" + API + "confirm_production_report"
        keys = sample["actors"]["A"]["keys"]
        auth = "token " + keys["api_key"] + ":" + keys["api_secret"]
        headers = {"Host": sample["site"], "Authorization": auth, "Content-Type": "application/json", "Connection": "close"}

        class OneRequestProxy(socketserver.StreamRequestHandler):
            def handle(self):
                upstream = None
                self.request.settimeout(45)
                try:
                    assert self.rfile.readline(65537) == ("POST " + path + " HTTP/1.1\r\n").encode()
                    incoming = http.client.parse_headers(self.rfile)
                    assert incoming.get("Host") == sample["site"] and incoming.get("Authorization") == auth
                    assert incoming.get("Transfer-Encoding") is None
                    assert int(incoming.get("Content-Length", "0")) == len(body_bytes)
                    assert self.rfile.read(len(body_bytes)) == body_bytes
                    events["proxy_request_validated"] = stamp()
                    upstream = http.client.HTTPConnection("127.0.0.1", 18090, timeout=45)
                    proxy["upstream_post_attempts"] += 1
                    events["upstream_send"] = stamp()
                    upstream.request("POST", path, body=body_bytes, headers=headers)
                    response = upstream.getresponse()
                    buffered = response.read()
                    events["backend_response_buffered"] = stamp()
                    proxy["upstream_status"] = response.status
                    proxy["upstream_body_sha256"] = hashlib.sha256(buffered).hexdigest()
                    write_json(PRIVATE / "buffered-response.json", {"status": response.status,
                        "body_utf8": buffered.decode(errors="replace"), "body_sha256": proxy["upstream_body_sha256"]})
                    proxy["upstream_payload"] = json.loads(buffered)
                    assert response.status == 200, "Backend did not accept the sole confirmation"
                    events["db_observation_start"] = stamp()
                    proxy["committed_state"], proxy["db_observation"] = snapshot("committed")
                    assert proxy["db_observation"]["submitted_fact_time_and_parent_visible"]
                    events["commit_observed"] = stamp()
                    proxy["commit_observed_before_drop"] = True
                except Exception as error:
                    proxy["failure_type"] = type(error).__name__
                    write_json(PRIVATE / "proxy-failure.json", {"traceback": traceback.format_exc()})
                finally:
                    if upstream:
                        upstream.close()
                    # No writes to wfile/send/sendall occur: no downstream HTTP bytes are sent.
                    events["downstream_drop_start"] = stamp()
                    try:
                        self.request.shutdown(socket.SHUT_RDWR)
                    except OSError as error:
                        proxy["shutdown_error_type"] = type(error).__name__
                    events["downstream_drop_finished"] = stamp()

        server = socketserver.TCPServer(("127.0.0.1", 0), OneRequestProxy)
        server.timeout = 45
        worker = threading.Thread(target=server.handle_request, name="i05-one-request-proxy")
        worker.start()
        client = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=120)
        events["client_send"] = stamp()
        try:
            client.request("POST", path, body=body_bytes, headers=headers)
            received = client.getresponse()
            summary["unexpected_downstream_http_status"] = received.status
        except (http.client.HTTPException, OSError) as error:
            summary["client_disconnect_error_type"] = type(error).__name__
            events["client_disconnect_observed"] = stamp()
        finally:
            client.close()
        worker.join(timeout=120)
        assert not worker.is_alive(), "Proxy did not finish; never retry the confirmation"
        assert not proxy.get("failure_type"), "Proxy/DB observation failed; inspect private evidence"
        assert proxy.get("commit_observed_before_drop") and proxy["upstream_post_attempts"] == 1
        assert summary.get("client_disconnect_error_type") in ("RemoteDisconnected", "ConnectionResetError")
        assert "unexpected_downstream_http_status" not in summary
        ordered = ("client_send", "proxy_request_validated", "upstream_send", "backend_response_buffered",
                   "db_observation_start", "commit_observed", "downstream_drop_start", "client_disconnect_observed")
        assert all(events[a]["monotonic_ns"] <= events[b]["monotonic_ns"] for a, b in zip(ordered, ordered[1:]))
        events["recovery_start"] = stamp()
        recovery = request(sample, "A", API + "get_production_report_result", {"request_id": recovery_key})
        raw.append({"step": "original-key-GET-recovery", **recovery})
        recovered = response_value(recovery)
        events["recovery_finished"] = stamp()
        after, _ = snapshot("after")
        summary["verification"] = verify(sample, before, proxy["committed_state"], after, recovered, proxy["upstream_payload"])
        summary["retention"] = container_json("xgd-b08-check", "preserve")
        assert summary["retention"]["all_old_rows_unchanged"]
        summary["passed"] = True
    except Exception as error:
        summary["failure_type"] = type(error).__name__
        write_json(PRIVATE / "execution-failure.json", {"traceback": traceback.format_exc()})
        raise
    finally:
        if client:
            client.close()
        if server:
            server.server_close()
        if worker and worker.is_alive():
            worker.join(timeout=120)
        if (PRIVATE / "before.json").exists() and not (PRIVATE / "after.json").exists():
            try:
                _, observed = snapshot("after")
                summary["failure_readonly_after_observation"] = observed
            except Exception as error:
                summary["failure_after_observation_error_type"] = type(error).__name__
        if "retention" not in summary:
            try:
                summary["retention"] = container_json("xgd-b08-check", "preserve")
            except Exception as error:
                summary["retention_error_type"] = type(error).__name__
        write_json(PRIVATE / "raw-responses.json", raw)
        summary.update({"events": events, "upstream_confirmation_posts": proxy["upstream_post_attempts"],
            "downstream_response_bytes": proxy["downstream_response_bytes"],
            "commit_observed_before_drop": proxy.get("commit_observed_before_drop", False),
            "upstream_status": proxy.get("upstream_status"), "db_observation": proxy.get("db_observation"),
            "proxy_failure_type": proxy.get("failure_type"), "exact_commit_instruction_time_recorded": False,
            "limit": "Commit was observable through a fresh DB connection before response loss; no precise COMMIT instruction timestamp, browser, I06 or full G3 claim."})
        write_json(EVIDENCE / "http-i05.json", summary)
        print(json.dumps({"passed": summary["passed"], "confirmation_posts": proxy["upstream_post_attempts"],
                          "failure_type": summary.get("failure_type"), "credentials_printed": False}))


if __name__ == "__main__":
    main()
