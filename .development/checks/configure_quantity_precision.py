"""Apply the native six-place default only to the existing B01 isolated sites."""
import argparse
import json
import os

import frappe

parser = argparse.ArgumentParser()
parser.add_argument('site', choices=['xgd-dev.localhost', 'xgd-test.localhost'])
parser.add_argument('--apply', action='store_true', help='Save native System Settings; otherwise read only')
args = parser.parse_args()
os.chdir('sites')
frappe.init(site=args.site)
frappe.connect()
try:
    frappe.set_user('Administrator')
    settings = frappe.get_single('System Settings')
    before = {'setting': settings.float_precision, 'effective_default': frappe.db.get_default('float_precision')}
    changed = False
    if args.apply:
        settings.float_precision = '6'
        # Native save synchronizes DefaultValue; writing Singles directly does not.
        settings.save()
        assert frappe.db.get_default('float_precision') == '6'
        frappe.db.commit()
        frappe.clear_cache()
        changed = before != {'setting': '6', 'effective_default': '6'}
    current = frappe.get_single('System Settings')
    print(json.dumps({'site': args.site, 'mode': 'apply' if args.apply else 'read',
        'changed': changed, 'before': before,
        'after': {'setting': current.float_precision, 'effective_default': frappe.db.get_default('float_precision')},
        'language': current.language, 'rounding_method': current.rounding_method,
        'limit': 'Native Float default only; explicit field precision and Currency settings retain native precedence. No full Decimal claim.'},
        ensure_ascii=False, indent=2))
finally:
    frappe.db.rollback()
    frappe.destroy()
