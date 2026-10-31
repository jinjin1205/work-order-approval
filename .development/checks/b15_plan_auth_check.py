import os,json
from pathlib import Path
import frappe
from frappe.utils.password import get_decrypted_password,set_encrypted_password
os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');a=json.loads(Path('/tmp/b08-private/b15-plan/access.json').read_text());actor=a['actors']['other'];u=frappe.get_doc('User',actor['user']);secret=get_decrypted_password('User',u.name,fieldname='api_secret',raise_exception=False)
 print(json.dumps({'enabled':bool(u.enabled),'key_matches':u.api_key==actor['api_key'],'secret_present':bool(secret),'secret_matches':secret==actor['api_secret']}))
 assert not secret and u.api_key==actor['api_key'];u.api_secret=actor['api_secret'];u.save();frappe.db.commit();print('Restored synthetic secret through native User.save; revoked role remains revoked')
 for i,line in enumerate(Path('..','apps/frappe/frappe/core/doctype/user/user.py').read_text().splitlines()):
  if 'api_secret' in line:print('user.py',i+1,line.strip())
finally:frappe.db.rollback();frappe.destroy()
