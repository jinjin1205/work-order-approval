"""Reproduce the reviewed source-entry/parent inversion with real native transactions."""
import json, os, subprocess, sys, time
from pathlib import Path
import frappe
from b11_return_fixture import P, audit
from b10_issue_fixture import runtime
from b08_distinct_concurrency_fixture import write_private
case,mode=sys.argv[1:];assert case in ('lock-red','lock-green')
f=P/case;f.mkdir(exist_ok=True);a=json.loads((P/'access.json').read_text());bench=Path('/home/frappe/frappe-bench')
def wait(name,seconds=20):
    deadline=time.monotonic()+seconds
    while not (f/name).exists():
        assert time.monotonic()<deadline,'Missing signal '+name
        time.sleep(.05)
os.chdir(bench/'sites');frappe.init(site=a['site']);frappe.connect()
try:
    assert frappe.conf.b08_http_only
    if mode in ('A','B'):
        from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
        original=StockEntry.check_if_latest if mode=='B' else StockEntry.validate_production_execution
        def gate(self):
            result=original(self)
            (f/(mode+'-locked')).touch(exist_ok=False)
            wait('release-'+mode)
            return result
        setattr(StockEntry,'check_if_latest' if mode=='B' else 'validate_production_execution',gate)
        frappe.set_user(a['actors'][mode]['user'])
        write_private(f/(mode+'-connection.json'),{'id':frappe.db.sql('select connection_id()')[0][0]})
        try:
            doc=frappe.get_doc('Stock Entry',a['cases'][case]['drafts'][mode])
            doc.cancel() if mode=='B' else doc.submit()
            frappe.db.commit();result={'committed':True,'docstatus':doc.docstatus}
        except Exception as error:
            frappe.db.rollback();result={'committed':False,'error_type':type(error).__name__,'message':str(error)}
        write_private(f/(mode+'-result.json'),result)
    else:
        assert mode=='run' and not (f/'source.json').exists(),'No race replay'
        write_private(f/'source.json',runtime());processes=[]
        observation={'return_reached_parent_while_cancel_held_source':False,'return_waited_for_parent':False}
        def spawn(actor):
            return subprocess.Popen([str(bench/'env/bin/python'),'/b01/b11_lock_order_race.py',case,actor],cwd=bench,stdout=(f/(actor+'.log')).open('x'),stderr=subprocess.STDOUT)
        try:
            processes.append(spawn('B'));wait('B-locked')
            processes.append(spawn('A'));wait('A-connection.json')
            connection=json.loads((f/'A-connection.json').read_text())['id']
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if (f/'A-locked').exists():
                    observation['return_reached_parent_while_cancel_held_source']=True;break
                rows=[r for r in frappe.db.sql('SHOW FULL PROCESSLIST',as_dict=True) if r.Id==connection]
                if rows and rows[0].Info and 'tabWork Order' in rows[0].Info and 'for update' in rows[0].Info.lower():
                    observation['return_waited_for_parent']=True;break
                time.sleep(.05)
            (f/'release-B').touch(exist_ok=False)
            if observation['return_reached_parent_while_cancel_held_source']:
                # B now requests the parent held by A; release A to query its real source facts.
                bconn=json.loads((f/'B-connection.json').read_text())['id']
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    rows=[r for r in frappe.db.sql('SHOW FULL PROCESSLIST',as_dict=True) if r.Id==bconn]
                    if rows and rows[0].Info and 'tabWork Order' in rows[0].Info and 'for update' in rows[0].Info.lower():break
                    time.sleep(.05)
            else:
                wait('A-locked')
        finally:
            for actor in ('A','B'):
                (f/('release-'+actor)).touch(exist_ok=True)
            for process in processes:process.wait(timeout=35)
        frappe.db.rollback();frappe.set_user('Administrator')
        results={actor:json.loads((f/(actor+'-result.json')).read_text()) for actor in ('A','B')}
        state=audit()
        summary={'case':case,'observation':observation,'results':results,'state':state['cases'][case],'old_rows_unchanged':state['old_rows_unchanged'],'runtime':runtime()}
        write_private(f/'summary.json',summary)
        print(json.dumps({k:v for k,v in summary.items() if k not in ('results','runtime')}|{'outcomes':{actor:{k:v for k,v in result.items() if k!='message'} for actor,result in results.items()}},ensure_ascii=False))
finally:
    frappe.db.rollback();frappe.destroy()
