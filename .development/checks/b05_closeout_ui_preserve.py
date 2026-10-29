"""Read back old captured rows and only this package's new synthetic orders."""
import hashlib
import html
import re
import json
import os
from pathlib import Path
import frappe
os.chdir("sites")
p=Path("/tmp/b08-private")
a=json.loads((p/"b05-closeout-ui.json").read_text())
frappe.init(site=a["site"])
frappe.connect()
try:
    frappe.set_user("Administrator")
    baseline=json.loads((p/"b05-closeout-before.json").read_text())
    mismatches=[]
    additions={}
    for dt,expected in baseline.items():
        rows=frappe.get_all(dt,fields=expected["columns"],limit_page_length=0)
        current={row.name:hashlib.sha256(json.dumps(dict(row),sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest() for row in rows}
        if any(current.get(name)!=digest for name,digest in expected["rows"].items()): mismatches.append(dt)
        additions[dt]=len(set(current)-set(expected["rows"]))
    assert not mismatches,mismatches
    assert additions["Work Order"]==4 and additions["Stock Entry"]==0 and additions["Stock Ledger Entry"]==0
    closed=[]
    report_count=0
    for sample in a["samples"]:
        order=frappe.get_doc("Work Order",sample["order"])
        assert order.status=="Closed" and order.docstatus==1 and order.qty==10 and order.produced_qty==0
        card=frappe.get_doc("Job Card",sample["card"])
        assert card.docstatus==0 and card.total_completed_qty==0 and not card.started_time
        assert all(row.to_time for row in card.time_logs)
        if sample["mode"] in ("partial","stopped") or card.time_logs:
            assert len(card.time_logs)==1 and card.time_logs[0].time_in_mins==60
        comments=frappe.get_all("Comment",filters={"reference_doctype":"Work Order","reference_name":order.name,"content":["like","%人工结束工单：%"]},fields=["content","owner"])
        assert len(comments)==1 and comments[0].owner==a["user"]
        record=json.loads(html.unescape(re.search(r"<pre>(.*?)</pre>",comments[0].content,re.S).group(1)))
        assert all(key in record for key in ("未入库差额","结束原因","人工结束时间"))
        if sample["mode"]=="unicode":
            assert "未入库差额" in comments[0].content and not card.time_logs
        if sample["mode"]=="partial":
            report=frappe.get_doc("Job Card",sample["report"])
            assert report.docstatus==1 and report.report_request_id
            assert report.total_completed_qty==8 and report.process_loss_qty==2
            assert report.total_time_in_mins==60 and report.report_effective_seconds==3600
            assert len(report.time_logs)==1 and str(report.time_logs[0].from_time)=="2026-10-20 07:00:00" and str(report.time_logs[0].to_time)=="2026-10-20 08:00:00"
            assert order.operations[0].completed_qty==8 and order.operations[0].process_loss_qty==2
            assert order.operations[0].actual_operation_time==60
            assert str(order.actual_start_date)=="2026-10-20 07:00:00" and str(order.actual_end_date)=="2026-10-20 08:00:00"
            report_count+=1
        else:
            assert all(row.completed_qty==0 and row.process_loss_qty==0 for row in order.operations)
        assert not frappe.db.exists("Stock Entry",{"work_order":order.name})
        closed.append({"mode":sample["mode"],"closed":True,"timer_rows":len(card.time_logs),"timer_quantity":0,"close_records":1})
    assert additions["Job Card"]==13 and additions["User"]==2 and additions["Employee"]==1
    print(json.dumps({"old_tables_preserved":len(baseline),"old_row_mismatches":0,"new_orders":4,"all_closed":True,"new_job_cards":13,"new_confirmed_reports":report_count,"new_stock_entries":0,"new_stock_ledger_entries":0,"samples":closed,"partial_good":8,"partial_bad":2,"partial_report_minutes":60,"plan_timer_minutes_not_added_to_report":True,"original_actual_dates_retained":True,"new_display_sample_chinese_plain_text":True,"original_three_records_rewritten":0},ensure_ascii=False,indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
