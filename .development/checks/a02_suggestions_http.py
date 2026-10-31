import json
import sys
import time
from pathlib import Path
import b19_remaining_http as http

P=Path('.development/private/a02-suggestions-20261031')
A=json.loads((P/'access.json').read_text());http.P=P;http.A=A
WO=http.WO


def prepare_order():
    doc=http.call('empty-draft','frappe.client.insert',{'doc':dict(doctype='Work Order',production_item=A['fg'],bom_no=A['bom'],
        company=A['company'],production_team=A['team'],qty=10,stock_uom=A['unit'],
        source_warehouse=A['warehouses']['source'],wip_warehouse=A['warehouses']['wip'],fg_warehouse=A['warehouses']['fg'])},'planner')
    assert not doc['operations']and not doc['required_items']
    (P/'case.json').write_text(json.dumps(dict(order=doc['name'],modified=doc['modified']),indent=2)+'\n')
    args=dict(production_item=A['fg'],company=A['company'],missing_fields=['bom_no','source_warehouse','fg_warehouse','expected_delivery_date'])
    start=time.monotonic()
    result=http.call('field-candidates','erpnext.manufacturing.production_ai.get_production_field_suggestions',args,'planner')
    elapsed=(time.monotonic()-start)*1000
    assert {r['fieldname']for r in result['candidates']}=={'bom_no','source_warehouse','fg_warehouse'}
    assert not result['history_used']
    http.call('read-only-candidates-denied','erpnext.manufacturing.production_ai.get_production_field_suggestions',args,'reader',expected=403)
    (P/'timing-http.json').write_text(json.dumps(dict(candidate_request_ms=elapsed,samples=1,model_calls=0),indent=2)+'\n')
    print(json.dumps(dict(order=doc['name'],candidate_fields=3,missing_date_is_manual=True,read_only_status=403,candidate_request_ms=elapsed)))


if __name__=='__main__':
    {'prepare-order':prepare_order}[sys.argv[1]]()
