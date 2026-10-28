"""Compare only pre-existing B08 synthetic records; new followup data is retained."""
import hashlib,json,os
from pathlib import Path
import frappe
os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
    assert frappe.conf.b08_http_only
    old=json.loads(Path('/tmp/b08-private/followup-20261028-before.json').read_text())
    result={}
    for dt,expected in old.items():
        current={r.name:hashlib.sha256(frappe.as_json(r).encode()).hexdigest() for r in frappe.get_all(dt,fields=['*'])}
        assert all(current.get(n)==h for n,h in expected.items()),dt+' old records changed'
        result[dt]=dict(original_rows=len(expected),original_rows_unchanged=True,new_rows=len(set(current)-set(expected)))
    print(json.dumps(dict(tables=result,all_original_records_unchanged=True,limits='Only the 11 listed tables; not a full database audit. New synthetic records retained.'),ensure_ascii=False,indent=2))
finally:
    frappe.db.rollback();frappe.destroy()
