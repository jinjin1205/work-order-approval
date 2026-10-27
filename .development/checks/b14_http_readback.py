"""Ordinary configuration user HTTP readback; secrets and raw records remain local."""
import http.cookiejar
import json
from pathlib import Path
import urllib.parse
import urllib.request
root = Path(__file__).resolve().parents[2]
a = json.loads((root / '.development/private/b14-ui/access.json').read_text())
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def call(path, data=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    with client.open(a['base_url'] + path, data=body, timeout=30) as response:
        return json.load(response)
call('/api/method/login', {'usr': a['user'], 'pwd': a['password']})
rows = call('/api/resource/Production%20Time%20Rule')['data']
assert len(rows) == 1
name = rows[0]['name']
doc = call('/api/resource/Production%20Time%20Rule/' + urllib.parse.quote(name))['data']
assert doc['owner'] == a['user'] and doc['priority'] >= 0
assert [(r['period_type'], r['start_time'], r['end_time']) for r in doc['periods']] == [('Rest', '12:00:00', '13:00:00'), ('Overtime', '16:00:00', '17:00:00')]
print(json.dumps({'http_login': True, 'ordinary_config_user': True, 'list_exactly_one': True,
    'saved_rule_owned_by_user': True, 'saved_priority': doc['priority'], 'two_periods_exact': True,
    'negative_priority_not_persisted': True}))

import re
import urllib.error
html = client.open(a['base_url'] + '/app', timeout=30).read().decode()
match = re.search(r'frappe.csrf_token\s*=\s*["\']([^"\']+)', html)
assert match, 'Authenticated page must provide native CSRF token'
headers = {'X-Frappe-CSRF-Token': match[1], 'Content-Type': 'application/json'}
child = dict(doc['periods'][0])
child['start_time'] = '12:00:01'
new_child = {k: v for k, v in child.items() if k not in ('name', 'creation', 'modified', 'owner', 'modified_by')}
checks = [('direct_child_save', '/api/method/frappe.client.save', 'POST', {'doc': json.dumps(child)}),
    ('direct_child_insert', '/api/resource/Production%20Time%20Period', 'POST', new_child),
    ('direct_child_delete', '/api/resource/Production%20Time%20Period/' + urllib.parse.quote(child['name']), 'DELETE', None)]
for label, path, method, payload in checks:
    request = urllib.request.Request(a['base_url'] + path,
        data=json.dumps(payload).encode() if payload is not None else None, headers=headers, method=method)
    try:
        client.open(request, timeout=30)
    except urllib.error.HTTPError as exc:
        error = json.loads(exc.read())
        assert exc.code == 403 and error.get('exc_type') == 'PermissionError', (label, exc.code, error.get('exc_type'))
        print(json.dumps({'case': label, 'http_status': exc.code, 'exception': error['exc_type']}))
    else:
        raise AssertionError(label + ' unexpectedly succeeded')
after = call('/api/resource/Production%20Time%20Rule/' + urllib.parse.quote(name))['data']
assert after == doc
print(json.dumps({'parent_and_periods_unchanged_after_denials': True}))
