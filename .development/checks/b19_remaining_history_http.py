"""Native parent docinfo history must retain the same read boundary after revocation."""
import json
from b19_remaining_http import A, P, call

case = json.loads((P/'attachment-case.json').read_text())
args = dict(doctype='Work Order', name=case['order'])
for actor, status in [('reviewer', 200), ('planner', 403), ('foreign_director', 403)]:
    call('history-docinfo-'+actor, 'frappe.desk.form.load.getdoc', args, actor, expected=status)
body = json.loads((P/'history-docinfo-reviewer.json').read_text())['body']
assert body['docs'][0]['name'] == case['order']
info = body['docinfo']
assert {row['name'] for row in info['attachments']} == {case['v1'],case['v2']}
assert len(info['versions']) == 7
assert sum('审批动作：送审；' in row['content'] for row in info['comments']) == 2
print(json.dumps(dict(authorized_parent_history=True, versions=7, attachment_versions=2,
                     revoked_parent_history_status=403, foreign_parent_history_status=403)))
