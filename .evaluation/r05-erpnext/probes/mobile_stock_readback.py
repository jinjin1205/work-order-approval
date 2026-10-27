"""Read-only ordinary Stock User evidence after browser actions."""
import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--stage', required=True)
args = p.parse_args()
creds = json.loads(Path('.evaluation/r05-erpnext/access-secrets.json').read_text())['users']['stock']
fixture = json.loads(Path('evidence/R05/followup/mobile/material-setup.json').read_text())
result = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'user': creds['email'], 'stage': args.stage, 'responses': {}}
queries = {
    'issue': '/api/resource/Stock Entry/' + fixture['stock_draft'],
    'work_order': '/api/resource/Work Order/' + fixture['work_order'],
    'entries': '/api/resource/Stock Entry?' + urllib.parse.urlencode({'filters': json.dumps({'work_order': fixture['work_order']}), 'fields': json.dumps(['name','docstatus','is_return','purpose']), 'limit_page_length': 50}),
    'bins': '/api/resource/Bin?' + urllib.parse.urlencode({'filters': json.dumps({'item_code': fixture['ids']['raw_item']}), 'fields': json.dumps(['name','warehouse','actual_qty']), 'limit_page_length': 50}),
    'ledger': '/api/resource/Stock Ledger Entry?' + urllib.parse.urlencode({'filters': json.dumps({'item_code': fixture['ids']['raw_item']}), 'fields': json.dumps(['name','warehouse','actual_qty','qty_after_transaction','voucher_no','is_cancelled']), 'limit_page_length': 50}),
}
for key, path in queries.items():
    req = urllib.request.Request('http://127.0.0.1:18085' + path.replace(' ', '%20'), headers={'Authorization': 'token ' + creds['api_key'] + ':' + creds['api_secret']})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result['responses'][key] = {'status': response.status, 'body': json.load(response)}
    except urllib.error.HTTPError as error:
        result['responses'][key] = {'status': error.code, 'body': error.read().decode()}
output = Path('evidence/R05/followup/mobile') / (args.stage + '.json')
with output.open('x') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps({k: {'status': v['status'], 'data': v['body'].get('data') if k in ('entries','bins','ledger') and isinstance(v['body'],dict) else None} for k,v in result['responses'].items()}, ensure_ascii=False))
