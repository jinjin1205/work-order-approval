"""Read only exact-commit CI metadata; no credentials or runtime business data."""
import datetime,json,sys
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
base='https://api.github.com/repos/jinjin1205/work-order-approval'
def get(path):
    try:
        with urlopen(Request(base+path,headers={'Accept':'application/vnd.github+json','User-Agent':'work-order-closeout'}),timeout=30) as r:return json.load(r)
    except HTTPError as e:
        return {'unavailable_http_status':e.code}
workflow=get('/actions/workflows?per_page=100')
results=[]
for sha in sys.argv[1:]:
    runs=get('/actions/runs?head_sha='+sha+'&per_page=100');checks=get('/commits/'+sha+'/check-runs?per_page=100');status=get('/commits/'+sha+'/status?per_page=100')
    results.append(dict(sha=sha,actions_total=runs.get('total_count'),runs=[{k:r.get(k) for k in ['id','head_sha','head_branch','status','conclusion','html_url']} for r in runs.get('workflow_runs',[])],check_runs_total=checks.get('total_count'),check_runs=[{k:r.get(k) for k in ['name','head_sha','status','conclusion','html_url']} for r in checks.get('check_runs',[])],statuses_total=status.get('total_count'),statuses=[{k:r.get(k) for k in ['context','state','target_url']} for r in status.get('statuses',[])],errors=[v for v in [runs,checks,status] if 'unavailable_http_status' in v]))
result=dict(checked_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),repo='jinjin1205/work-order-approval',workflow_count=workflow.get('total_count'),workflows=[{k:w.get(k) for k in ['name','path','state','html_url']} for w in workflow.get('workflows',[])],workflow_errors=workflow.get('unavailable_http_status'),commits=results,scope='Exact SHA, all events; zero checks is NOT CI success; no permission assumptions for unnamed collaborators')
print(json.dumps(result,indent=2))
