"""Continue only unfinished HTTP checks; keep the passed same-key concurrent pair."""
import json, uuid
from pathlib import Path
import b08_http as h
try:
    before=h.facts()
    assert len(before['reports'])==2 and before['tasks'][0]['good']==2
    args=h.args_for(1,'2026-10-15 09:00','2026-10-15 09:00')
    added=h.check('identical-zero-time-content-new-key',h.call('confirm_production_report',args),200)
    before=h.facts();assert len(before['reports'])==3 and before['tasks'][0]['good']==3
    over=h.args_for(8,'2026-10-15 10:00','2026-10-15 11:00')
    h.check('real-overquantity-rollback',h.call('confirm_production_report',over),417)
    assert h.facts()==before
    h.check('task-out-of-scope',h.call('preview_production_report_time',{**args,'operation_id':h.f['http_forbidden']}),403)
    h.check('parent-write-denied',h.call('Work Order/'+h.f['http_order'],{'qty':20},'PUT',True),403)
    original=json.loads(Path('.development/private/b08-http/last-replies.json').read_text())[0]['data']['message']['name']
    card=h.check('original-read',h.call('Job Card/'+original,None,'GET',True),200)
    h.check('original-update-denied',h.call('Job Card/'+original,{'remarks':'tamper','flags':{'ignore_validate_update_after_submit':True}},'PUT',True),403)
    h.check('child-update-denied',h.call('Job Card Time Log/'+card['time_logs'][0]['name'],{'completed_qty':9,'flags':{'ignore_validate_update_after_submit':True}},'PUT',True),403)
    found=h.check('lost-response-lookup',h.call('get_production_report_result',{'request_id':card['report_request_id']}),200)
    assert found['name']==original and h.facts()==before
    h.results.append(dict(case='final',facts=3,good=3,bad=0,plan=10,unfinished=7,full_concurrency_gate_closed=False))
finally:
    Path('evidence/B08/implementation/http-followup-results.json').write_text(json.dumps(h.results,ensure_ascii=False,indent=2)+'\n')
