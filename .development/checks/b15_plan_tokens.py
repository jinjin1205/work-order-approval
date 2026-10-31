import json,os
from pathlib import Path
import frappe
from frappe.utils.password import set_encrypted_password
p=Path('/tmp/b08-private/b15-plan/access.json');os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');a=json.loads(p.read_text())
 for actor in a['actors'].values():
  assert not actor.get('api_key');actor['api_key']=frappe.generate_hash(length=15);actor['api_secret']=frappe.generate_hash(length=15);frappe.db.set_value('User',actor['user'],'api_key',actor['api_key']);set_encrypted_password('User',actor['user'],actor['api_secret'],fieldname='api_secret')
 p.write_text(json.dumps(a));frappe.db.commit();print('2 isolated actor tokens prepared; no secrets printed')
finally:frappe.db.rollback();frappe.destroy()
