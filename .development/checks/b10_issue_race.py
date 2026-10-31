"""Two real DB transactions; gate only the first on_submit, never replace business rules."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import frappe
from b10_issue_fixture import P, runtime, audit
from b08_distinct_concurrency_fixture import write_private

case=sys.argv[1]
assert case in ('race-red','race-green')
mode=sys.argv[2]
folder=P/case
folder.mkdir(exist_ok=True)
a=json.loads((P/'access.json').read_text())
bench=Path('/home/frappe/frappe-bench')
os.chdir(bench/'sites'); frappe.init(site=a['site']); frappe.connect()
try:
    assert frappe.conf.b08_http_only
    if mode in ('A','B'):
        from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
        def wait_release():
            deadline=time.monotonic()+30
            while not (folder/'release').exists():
                assert time.monotonic()<deadline,'Controlled schedule timed out'
                time.sleep(.05)
        original=StockEntry.on_submit
        def on_submit(self):
            (folder/(mode+'-validated')).touch(exist_ok=False)
            if mode=='A':
                wait_release()
            return original(self)
        StockEntry.on_submit=on_submit
        frappe.set_user(a['actors'][mode]['user'])
        write_private(folder/(mode+'-connection.json'),{'connection':frappe.db.sql('select connection_id()')[0][0]})
        try:
            doc=frappe.get_doc('Stock Entry',a['cases'][case]['drafts'][mode])
            doc.submit(); frappe.db.commit()
            result={'actor':mode,'committed':True,'docstatus':1}
        except Exception as error:
            # Test-process boundary: retain actual type/message, rollback, no retry or false success.
            frappe.db.rollback()
            result={'actor':mode,'committed':False,'error_type':type(error).__name__,'message':str(error)}
        write_private(folder/(mode+'-result.json'),result)
    else:
        assert mode=='run' and not (folder/'source.json').exists(),'Do not replay a race'
        write_private(folder/'source.json',runtime())
        def spawn(actor):
            return subprocess.Popen([str(bench/'env/bin/python'),'/b01/b10_issue_race.py',case,actor],cwd=bench,stdout=(folder/(actor+'.log')).open('x'),stderr=subprocess.STDOUT)
        def wait_file(name, seconds):
            deadline=time.monotonic()+seconds
            while not (folder/name).exists():
                assert time.monotonic()<deadline,'Missing race signal '+name
                time.sleep(.05)
        processes=[]
        try:
            processes.append(spawn('A')); wait_file('A-validated',15)
            processes.append(spawn('B')); wait_file('B-connection.json',10)
            connection=json.loads((folder/'B-connection.json').read_text())['connection']
            observation={'parent_lock_wait':False,'second_validated_before_release':False}
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                rows=[row for row in frappe.db.sql('SHOW FULL PROCESSLIST',as_dict=True) if row.Id==connection]
                if rows and rows[0].Info and 'for update' in rows[0].Info.lower():
                    query=rows[0].Info
                    observation['parent_lock_wait']='tabWork Order' in query and 'for update' in query.lower()
                    observation['connection_state']=rows[0].State
                    observation['observation_method']='same-user SHOW FULL PROCESSLIST; A held before ledger until release'
                    observation['lock_query_table']='Work Order' if observation['parent_lock_wait'] else 'other'
                    break
                if (folder/'B-validated').exists():
                    observation['second_validated_before_release']=True
                    wait_file('B-result.json',12)
                    break
                time.sleep(.1)
        finally:
            (folder/'release').touch(exist_ok=False)
            for process in processes:
                process.wait(timeout=35)
        results=[json.loads((folder/(actor+'-result.json')).read_text()) for actor in ('A','B')]
        frappe.db.rollback(); frappe.set_user('Administrator')
        state=audit()
        summary={'case':case,'connections_distinct':json.loads((folder/'A-connection.json').read_text())!=json.loads((folder/'B-connection.json').read_text()),'observation':observation,'results':results,'state':state['cases'][case],'old_rows_unchanged':state['old_rows_unchanged'],'runtime':runtime()}
        write_private(folder/'summary.json',summary)
        # Only sanitized status is stdout; raw errors and object identifiers stay private.
        print(json.dumps({k:v for k,v in summary.items() if k not in ('results','runtime')}|{'outcomes':[{'committed':r['committed'],'error_type':r.get('error_type')} for r in results]},ensure_ascii=False))
finally:
    frappe.db.rollback(); frappe.destroy()
