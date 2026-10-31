import os,json
from pathlib import Path
import frappe
from b16_query_fixture import verify_retention
P=Path('/tmp/b08-private/b16-query');os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');a=json.loads((P/'access.json').read_text());user=a['actors']['reader']['user'];assert a['roles']['export'] in frappe.get_roles(user);frappe.get_doc('User',user).remove_roles(a['roles']['export']);verify_retention(json.loads((P/'before.json').read_text()));frappe.db.commit();print('Removed only B16 synthetic reader role; old facts preserved with recorded native seen exception')
finally:frappe.db.rollback();frappe.destroy()
