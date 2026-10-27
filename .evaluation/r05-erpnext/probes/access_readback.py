"""Read-only final persistence inspection; not ordinary authorization evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path
import frappe

output = Path('/home/frappe/frappe-bench/sites/r05f-access-readback-attempt2.json')
if output.exists() or frappe.local.site != 'r05.localhost':
    raise RuntimeError('Wrong site or retained output exists')
result = {
    'read_utc': datetime.now(timezone.utc).isoformat(), 'site': frappe.local.site,
    'kind': 'administrator read-only persistence inspection, not ordinary permission proof',
    'system_settings': {key: frappe.db.get_single_value('System Settings', key)
                        for key in ['time_zone', 'float_precision', 'rounding_method']},
    'deleted_card_exists': frappe.db.exists('Job Card', '[本地样例编号已移除]'),
    'deleted_time_log_count': frappe.db.count('Job Card Time Log', {'parent': '[本地样例编号已移除]'}),
    'deleted_document': frappe.get_all('Deleted Document',
        filters={'deleted_doctype': 'Job Card', 'deleted_name': '[本地样例编号已移除]'},
        fields=['name', 'deleted_doctype', 'deleted_name', 'restored', 'creation', 'owner', 'data']),
}
with output.open('x') as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
print(json.dumps({'output': str(output), 'deleted_card_exists': result['deleted_card_exists'],
                  'deleted_time_log_count': result['deleted_time_log_count'],
                  'deleted_document_count': len(result['deleted_document'])}))
