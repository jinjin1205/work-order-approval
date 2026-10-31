import os,json
from pathlib import Path
import frappe
from b08_distinct_concurrency_fixture import digest
P=Path('/tmp/b08-private/b16-query');os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
try:
 assert frappe.conf.b08_http_only;frappe.set_user('Administrator');a=json.loads((P/'access.json').read_text());baseline=json.loads((P/'before.json').read_text())['Work Order'];rows=frappe.get_all('Work Order',fields=baseline['columns'],limit_page_length=0);out=[]
 for row in rows:
  if row.name not in baseline['rows']or digest(dict(row))==baseline['rows'][row.name]:continue
  seen=json.loads(row.get('_seen')or'[]');actor=a['actors']['reader']['user'];assert actor in seen
  candidate=dict(row);candidate['_seen']=json.dumps([u for u in seen if u!=actor]);candidates=[candidate['_seen']]
  if candidate['_seen']=='[]':candidates+=['',None]
  matches=[]
  for value in candidates:
   candidate['_seen']=value
   if digest(candidate)==baseline['rows'][row.name]:matches.append(value)
  out.append({'name':row.name,'current_seen':seen,'known_new_reader':actor,'only_seen_candidate_matches_baseline':len(matches)==1,'matched_prior_seen':matches})
 print(json.dumps(out,ensure_ascii=False))
finally:frappe.db.rollback();frappe.destroy()
