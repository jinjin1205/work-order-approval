"""Bounded independent native transactions for original B19 approval races and rollback."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import frappe
from b08_distinct_concurrency_fixture import capture_tables, compare_tables, preserved, write_private
from b19_remaining_fixture import audit

P=Path('/tmp/b08-private/b19-remaining')
BENCH=Path('/home/frappe/frappe-bench')


def wait_file(folder,name,seconds):
    deadline=time.monotonic()+seconds
    while not(folder/name).exists():
        assert time.monotonic()<deadline,'Missing bounded schedule signal: '+name
        time.sleep(.05)


def child(case,actor,a,info,folder):
    from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder,apply_production_approval,make_stock_entry
    role='director' if actor=='A' or case=='double' else 'planner' if case=='withdraw' else 'warehouse'
    frappe.set_user(a['actors'][role]['user'])
    assert 'System Manager'not in frappe.get_roles()
    write_private(folder/(actor+'-connection.json'),{'connection':frappe.db.sql('select connection_id()')[0][0]})
    if actor=='A':
        original=WorkOrder.add_comment
        def comment(self,*args,**kwargs):
            if self.name==info['order'] and len(args)>1 and args[0]=='Comment' and args[1].startswith('审批动作：签批通过；'):
                assert self.docstatus==1 and self.workflow_state=='已批准'
                (folder/'A-native-state-updated').touch(exist_ok=False)
                if case=='fault':
                    raise RuntimeError('B19 controlled approval comment write failure')
                wait_file(folder,'release',25)
            return original(self,*args,**kwargs)
        WorkOrder.add_comment=comment
    try:
        if case=='execute' and actor=='B':
            assert frappe.has_permission('Stock Entry','create')
            result=frappe.get_doc(make_stock_entry(info['order'],'Material Transfer for Manufacture',qty=10)).insert().submit()
            name=result.name
        else:
            action='撤回' if case=='withdraw' and actor=='B' else '签批通过'
            result=apply_production_approval(info['order'],action,info['version'],'B19并发撤回验收' if action=='撤回'else None)
            name=result.name
        frappe.db.commit()
        outcome={'committed':True,'name':name}
    except Exception as error:
        # Process boundary records the real failure and rolls back the native transaction.
        frappe.db.rollback()
        outcome={'committed':False,'error_type':type(error).__name__,'message':str(error)}
    write_private(folder/(actor+'-result.json'),outcome)


def run(case,a,info,folder):
    assert not(folder/'source.json').exists(),'Never replay a recorded schedule'
    runtime=json.loads(Path('/b01/b16-query-source-manifest.json').read_text())['files']
    files=set(runtime)|{'erpnext/manufacturing/permissions.py'}
    source={name:hashlib.sha256((BENCH/'apps/erpnext'/name).read_bytes()).hexdigest()for name in sorted(files)}
    write_private(folder/'source.json',{'case':case,'order':info['order'],'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'runtime_files':source})
    frappe.set_user('Administrator')
    rollback_before=capture_tables(['Work Order','Work Order Operation','Job Card','Workflow Action','Version','Comment']) if case=='fault' else None
    frappe.db.rollback()
    processes=[];observation={'parent_lock_wait':False}
    try:
        def spawn(actor):
            log=(folder/(actor+'.log')).open('x')
            process=subprocess.Popen([str(BENCH/'env/bin/python'),'/b01/b19_remaining_race.py',case,actor],cwd=BENCH,stdout=log,stderr=subprocess.STDOUT)
            log.close()
            processes.append(process)
        spawn('A');wait_file(folder,'A-native-state-updated',18)
        if case!='fault':
            spawn('B');wait_file(folder,'B-connection.json',12)
            connection=json.loads((folder/'B-connection.json').read_text())['connection']
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                current=[r for r in frappe.db.sql('SHOW FULL PROCESSLIST',as_dict=True)if r.Id==connection]
                if current and current[0].Info and 'tabWork Order'in current[0].Info and 'for update'in current[0].Info.lower():
                    observation={'parent_lock_wait':True,'connection_state':current[0].State}
                    break
                if(folder/'B-result.json').exists():
                    observation['B_finished_before_release']=True
                    break
                time.sleep(.05)
    finally:
        (folder/'release').touch(exist_ok=False)
        for process in processes:
            try:
                process.wait(timeout=35)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
                raise
    results={actor:json.loads((folder/(actor+'-result.json')).read_text())for actor in (['A']if case=='fault'else['A','B'])}
    frappe.db.rollback();frappe.set_user('Administrator')
    order=frappe.get_doc('Work Order',info['order'])
    state=audit()
    summary={'case':case,'observation':observation,'results':results,'docstatus':order.docstatus,'workflow_state':order.workflow_state,
             'stock':frappe.get_all('Stock Entry',filters={'work_order':order.name},fields=['name','docstatus']),
             'old_rows_unchanged':state['old_rows_unchanged']}
    if case=='fault':
        checks=compare_tables(rollback_before)
        summary['rollback_same_rows']=preserved(checks)and all(r['new_rows']==0 for r in checks.values())
    else:
        ca=json.loads((folder/'A-connection.json').read_text());cb=json.loads((folder/'B-connection.json').read_text())
        summary['connections_distinct']=ca!=cb
    write_private(folder/'summary.json',summary)
    assert summary['old_rows_unchanged']
    if case=='fault':
        assert not results['A']['committed'] and results['A']['error_type']=='RuntimeError'
        assert order.docstatus==0 and order.workflow_state=='待签批' and summary['rollback_same_rows'],summary
    else:
        assert results['A']['committed'] and order.docstatus==1 and order.workflow_state=='已批准',summary
        assert summary['connections_distinct'],summary
        if case in ('double','withdraw'):
            assert observation['parent_lock_wait'] and not results['B']['committed'],summary
            assert results['B']['error_type'] in ('TimestampMismatchError','PermissionError'),summary
        elif results['B']['committed']:
            assert observation['parent_lock_wait'] and len(summary['stock'])==1 and summary['stock'][0]['docstatus']==1,summary
            assert order.required_items[0].transferred_qty==5,summary
        else:
            assert results['B']['error_type']=='PermissionError' and not summary['stock'],summary
    print(json.dumps({k:v for k,v in summary.items()if k not in ('results','stock')}|{'outcomes':{k:v['committed']for k,v in results.items()}},ensure_ascii=False))


if __name__=='__main__':
    case,mode=sys.argv[1:3];assert case in ('double','withdraw','execute','fault')and mode in ('A','B','run')
    a=json.loads((P/'access.json').read_text());info=json.loads((P/'race-cases.json').read_text())[case]
    folder=P/'races'/case;folder.mkdir(parents=True,exist_ok=True)
    os.chdir(BENCH/'sites');frappe.init(site=a['site']);frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        child(case,mode,a,info,folder)if mode in ('A','B')else run(case,a,info,folder)
    finally:
        frappe.db.rollback();frappe.destroy()
