import hashlib,json
from pathlib import Path
import frappe,erpnext
root=Path('/home/frappe/frappe-bench/apps/frappe')
paths=['frappe/core/doctype/document_naming_rule/document_naming_rule.py','frappe/core/doctype/document_naming_rule/document_naming_rule.json','frappe/core/doctype/user_permission/user_permission.py','frappe/core/doctype/user_permission/user_permission.json','frappe/model/create_new.py','frappe/model/naming.py']
print(json.dumps({'frappe':frappe.__version__,'erpnext':erpnext.__version__,'native_files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest()for n in paths}},indent=2))
