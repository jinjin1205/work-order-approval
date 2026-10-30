"""Real native dispatcher + one explicitly named RQ job, isolated synthetic targets only."""
import json
import logging
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import frappe
from frappe.utils.background_jobs import get_queue
from rq import SimpleWorker
from rq.job import Job

os.umask(0o077)
os.chdir("sites")
p = Path("/tmp/b08-private")
a = json.loads((p / "b09-lifecycle-ui.json").read_text())
assert a["site"] == "xgd-b08-http.localhost"
frappe.init(site=a["site"])
frappe.connect()
assert frappe.conf.b08_http_only
queue = get_queue("default")
mode = sys.argv[1]
state = p / "b09-lifecycle-queue.json"
try:
    if mode == "dispatch":
        assert not state.exists(), "Do not replay deletion requests"
        assert len(set(a["targets"])) == 11
        assert (p / "b09-lifecycle-protected-before.json").exists()
        actor = a["actors"]["reporter"]
        frappe.set_user(actor["user"])
        for name in a["targets"]:
            doc = frappe.get_doc("Job Card", name)
            assert doc.work_order == a["order"] and doc.has_permission("delete")
            if name != a["report"]:
                assert name in a["drafts"] and doc.docstatus == 0 and not doc.report_request_id and not doc.time_logs
        assert "System Manager" not in frappe.get_roles()
        before = queue.job_ids
        request = Request("http://xgd-b08-ui:8000/api/method/frappe.desk.reportview.delete_items",
            headers={"Host": a["site"], "Authorization": "token " + actor["api_key"] + ":" + actor["api_secret"], "Content-Type": "application/json"},
            data=json.dumps({"doctype": "Job Card", "items": json.dumps(a["targets"])}).encode(), method="POST")
        with urlopen(request, timeout=30) as response:
            status, data = response.status, json.loads(response.read())
        assert status == 200 and not data.get("message")
        new = set(queue.job_ids) - set(before)
        matches = []
        for ident in new:
            job = Job.fetch(ident, connection=queue.connection)
            if job.kwargs.get("method") == "frappe.desk.reportview.delete_bulk" and job.kwargs.get("kwargs", {}).get("items") == sorted(a["targets"], reverse=True):
                matches.append(job)
        assert len(matches) == 1
        job = matches[0]
        assert job.func_name == "frappe.utils.background_jobs.execute_job"
        assert job.kwargs["user"] == actor["user"] and job.kwargs["site"] == a["site"]
        assert job.kwargs["kwargs"]["doctype"] == "Job Card"
        state.write_text(json.dumps({"job_id": job.id, "queue": queue.name, "before_ids": before, "kwargs": job.kwargs}, default=str, indent=2))
        # An HTTP acknowledgement is not completion: the targets must still exist before execution.
        frappe.db.rollback()
        assert frappe.db.count("Job Card", {"name": ["in", a["targets"]]}) == 11
        print(json.dumps({"http_status": status, "real_rq_enqueue": True, "captured_user_and_site_match": True,
            "targets_before_worker": 11, "acknowledgement_not_completion": True}))
    elif mode == "execute":
        saved = json.loads(state.read_text())
        assert not saved.get("executed"), "Never replay this job"
        job = Job.fetch(saved["job_id"], connection=queue.connection)
        assert job.get_status() == "queued" and job.id in queue.job_ids
        assert job.kwargs == saved["kwargs"] and job.kwargs["user"] == a["actors"]["reporter"]["user"]
        untouched = [ident for ident in queue.job_ids if ident != job.id]
        assert queue.remove(job.id) == 1
        frappe.db.rollback()
        frappe.destroy()
        logging.getLogger("rq.worker").setLevel(logging.WARNING)
        worker = SimpleWorker([queue], connection=queue.connection, name="xgd-b09-only-" + job.id[-12:])
        worker.execute_job(job, queue)
        job.refresh()
        assert job.get_status() == "finished", job.get_status()
        assert job.result == [a["report"]], "Mixed deletion must retain the original report"
        assert all(ident in queue.job_ids for ident in untouched), "Unrelated queue entries changed"
        saved["executed"] = True
        saved["result"] = job.result
        state.write_text(json.dumps(saved, indent=2, default=str))
        print(json.dumps({"specified_job_worker_finished": True, "remaining_failed_targets": 1,
            "protected_report_returned": True, "unrelated_queue_entries_preserved": True,
            "scheduler_started": False, "continuous_worker_polling_tested": False}))
    else:
        raise ValueError("Unsupported mode")
finally:
    if getattr(frappe.local, "db", None):
        frappe.db.rollback()
        frappe.destroy()
