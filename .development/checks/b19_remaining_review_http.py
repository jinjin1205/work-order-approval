"""Exercise the two confirmed File input fixes against the restarted HTTP process once."""
import hashlib
import json
import sys
from b19_remaining_http import A, P, call, download


def verify_retained():
    case = json.loads((P/'attachment-case.json').read_text())
    read = lambda name: json.loads((P/(name+'.json')).read_text())
    assert read('review-public-url-refused')['status'] == 403
    assert read('review-retarget-publish-refused')['status'] == 403
    current = read('review-original-basis-retained')['body']['message']
    assert current['is_private'] == 1 and current['file_url'] == case['v1_url']
    assert read('review-original-basis-download')['status'] == 200
    assert hashlib.md5((P/'review-original-basis-download.bin').read_bytes()).hexdigest() == case['v1_hash']
    for label in ('public','private'):
        doc = read('review-'+label+'-source')['body']['message']
        assert read('review-cleanup-'+doc['name'])['status'] == 200
    return dict(public_url_disguise_status=403, retarget_publish_status=403,
        original_private_bytes_retained=True, synthetic_controls_deleted=2)


def run_http_once():
    case = json.loads((P/'attachment-case.json').read_text())
    created = []
    try:
        for label, private in [('public',0), ('private',1)]:
            doc = call('review-'+label+'-source', 'frappe.client.insert', {'doc':dict(doctype='File',
                file_name=A['prefix']+'-review-'+label+'.txt', content=A['prefix']+'-review-'+label,
                is_private=private)}, 'reviewer')
            created.append(doc)
        public, private = created
        call('review-public-url-refused', 'frappe.client.insert', {'doc':dict(doctype='File',
            file_name=public['file_name'], file_url=public['file_url'], is_private=1,
            attached_to_doctype='Work Order', attached_to_name=case['order'])}, 'reviewer', expected=403)
        response = json.loads((P/'review-public-url-refused.json').read_text())['body']
        assert '生产工单审批依据必须使用私有附件' in json.dumps(response, ensure_ascii=False)
        call('review-retarget-publish-refused', 'frappe.client.save',
             {'doc':dict(private, file_url=case['v1_url'], is_private=0)}, 'reviewer', expected=403)
        call('review-original-basis-retained', 'frappe.client.get',
             dict(doctype='File',name=case['v1']), 'reviewer')
        result = download('review-original-basis-download', case['v1_url'], 'reviewer')
        assert result['status'] == 200 and result['native_content_hash'] == case['v1_hash']
    finally:
        for doc in created:
            call('review-cleanup-'+doc['name'], 'frappe.client.delete',
                 dict(doctype='File', name=doc['name']), 'reviewer')


if __name__ == '__main__':
    if sys.argv[1:] != ['verify-retained']:
        run_http_once()
    print(json.dumps(verify_retained()))
