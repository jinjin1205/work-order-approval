import json,traceback
from pathlib import Path
from datetime import datetime,timezone
import frappe
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
out=Path('/home/frappe/frappe-bench/sites/r05f-mobile-material-setup.json')
if out.exists() or frappe.local.site!='r05.localhost':raise RuntimeError('Wrong site or existing result')
h={};exec(Path('/eval/r02_probe.py').read_text().split('\nif OUTPUT.exists():',1)[0],h);h['PREFIX']='R05F-U'
r={'started_utc':datetime.now(timezone.utc).isoformat(),'scope':'Native setup for ordinary warehouse mobile-width UI','steps':[]}
old={k:frappe.db.get_single_value('Manufacturing Settings',k) for k in h['SETTINGS']}
try:
 if frappe.get_all('Item',filters={'name':['like','R05F-U%']},limit=1):raise RuntimeError('Prefix exists')
 frappe.db.set_single_value('Manufacturing Settings',dict(h['SETTINGS']))
 wo,rm,fg=h['build_case'](r,'MAT',1,0)
 stock=frappe.get_doc(make_stock_entry(wo.name,'Material Transfer for Manufacture',5));stock.insert()
 user='r05f-a-stock@example.invalid'
 perm=frappe.get_doc({'doctype':'User Permission','user':user,'allow':'Work Order','for_value':wo.name,'apply_to_all_doctypes':1}).insert()
 frappe.clear_cache(user=user)
 frappe.db.commit()
 r.update({'transaction':'committed','work_order':wo.name,'stock_draft':stock.name,'user':user,'permission':perm.name,'stock_document':stock.as_dict()})
except Exception:
 frappe.db.rollback();r['error']=traceback.format_exc();raise
finally:
 frappe.db.set_single_value('Manufacturing Settings',dict(old));frappe.db.commit()
 r['settings_restored']={k:frappe.db.get_single_value('Manufacturing Settings',k) for k in old}==old
 r['finished_utc']=datetime.now(timezone.utc).isoformat()
 with out.open('x') as f:json.dump(r,f,ensure_ascii=False,indent=2,default=str)
 print(json.dumps({k:r.get(k) for k in ['transaction','work_order','stock_draft','settings_restored','error']}))
