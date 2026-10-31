"""Read the existing two-round sample; do not mutate business or invent a replay engine."""
import hashlib
import json
import os
from pathlib import Path

import frappe
from frappe.utils import get_datetime

P = Path('/tmp/b08-private/b19-remaining')


def inspect_basis():
    case = json.loads((P/'attachment-case.json').read_text())
    snapshots = [json.loads((P/name).read_text())['body']['message'] for name in
                 ('attachment-first-send.json', 'attachment-second-send.json')]
    current = frappe.get_doc('Work Order', case['order'])
    sends = frappe.get_all('Comment', filters=dict(reference_doctype='Work Order',
        reference_name=current.name, comment_type='Comment', content=['like', '%审批动作：送审；依据版本：%']),
        fields=['name', 'creation', 'content'], order_by='creation asc')
    assert len(sends) == 2
    versions = frappe.get_all('Version', filters=dict(ref_doctype='Work Order', docname=current.name),
        fields=['name', 'creation', 'data'], order_by='creation asc')
    dates = [(v, change) for v in versions for change in json.loads(v.data)['changed']
             if change[0] == 'expected_delivery_date']
    assert len(dates) == 1
    version, change = dates[0]
    df = current.meta.get_field('expected_delivery_date')
    assert change[1:] == [frappe.format_value(s['expected_delivery_date'], df) for s in snapshots]
    assert get_datetime(sends[0].creation) < get_datetime(version.creation) < get_datetime(sends[1].creation)
    headers = ['production_item', 'bom_no', 'company', 'production_team', 'qty', 'stock_uom',
               'planned_start_date', 'source_warehouse', 'wip_warehouse', 'fg_warehouse']
    rows = {'operations': ['name', 'operation', 'workstation', 'sequence_id', 'time_in_mins', 'report_plan_qty'],
            'required_items': ['name', 'item_code', 'stock_uom', 'source_warehouse', 'required_qty', 'operation']}
    for snapshot in snapshots:
        assert snapshot['name'] == current.name
        for field in headers:
            assert str(snapshot.get(field)) == str(current.get(field)), field
        for table, fields in rows.items():
            assert len(snapshot[table]) == len(current.get(table))
            for expected, actual in zip(snapshot[table], current.get(table)):
                for field in fields:
                    assert str(expected.get(field)) == str(actual.get(field)), (table, field)
    assert str(current.expected_delivery_date) == snapshots[1]['expected_delivery_date']
    files = [frappe.get_doc('File', case[name]) for name in ('v1', 'v2')]
    for index, file in enumerate(files):
        assert file.is_private == 1 and file.file_url.startswith('/private/files/')
        assert file.attached_to_name == current.name and file.attached_to_doctype == 'Work Order'
        content = file.get_content()
        if isinstance(content, str):
            content = content.encode()
        assert hashlib.md5(content).hexdigest() == file.content_hash == case['v'+str(index+1)+'_hash']
    rounds = []
    for index, send in enumerate(sends):
        included = [f.name for f in files if get_datetime(f.creation) <= get_datetime(send.creation)]
        assert included == [f.name for f in files[:index+1]]
        rounds.append(dict(round=index+1, sent_comment=send.name,
            expected_delivery_date=snapshots[index]['expected_delivery_date'], attachments=included))
    return dict(order=current.name, rounds=rounds, date_version=version.name,
        native_formatted_date_change=change[1:], input_operations=3, input_materials=1,
        original_bytes_retained=True, native_versions=len(versions), read_only=True,
        limitation='仅本样例输入依据；签批派生排程不冒充送审输入，外部URL版本未验证')


if __name__ == '__main__':
    os.chdir('sites')
    frappe.init(site='xgd-b08-http.localhost')
    frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator')
        print(json.dumps(inspect_basis(), ensure_ascii=False, indent=2, default=str))
    finally:
        frappe.db.rollback()
        frappe.destroy()
