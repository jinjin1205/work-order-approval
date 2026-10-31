"""Read native configuration only; imports are tested separately inside rollback fixtures."""
import json
import os
import sys
import frappe


def export_workflow():
    source=frappe.get_doc('Workflow','生产工单两级审批')
    fields=['workflow_name','document_type','workflow_state_field','is_active','override_status','send_email_alert']
    result={name:source.get(name)for name in fields}
    result.update(doctype='Workflow',name=source.name)
    result['states']=[{name:row.get(name)for name in ['state','doc_status','allow_edit','update_field','update_value','send_email','is_optional_state']}for row in source.states]
    result['transitions']=[{name:row.get(name)for name in ['state','action','next_state','allowed','allow_self_approval','condition']}for row in source.transitions]
    return result


def read_settings():
    protected={'Version','Comment','Workflow Action','File'}
    stored=[dict(row)for row in frappe.get_all('Logs To Clear',fields=['ref_doctype','days'],filters={'parent':'Log Settings'})]
    defaults=frappe.get_hooks('default_log_clearing_doctypes',{})
    return dict(site=frappe.local.site,pause_scheduler=bool(frappe.conf.pause_scheduler),
        stored_log_rules=stored,default_log_rules=defaults,
        protected_records_listed=[row for row in stored if row['ref_doctype']in protected],
        read_only=True,customer_configuration_verified=False)


if __name__=='__main__':
    os.chdir('sites');frappe.init(site='xgd-b08-http.localhost');frappe.connect()
    try:
        assert frappe.conf.b08_http_only
        frappe.set_user('Administrator')
        print(json.dumps({'export':export_workflow,'read-settings':read_settings}[sys.argv[1]](),ensure_ascii=False,indent=2,default=str))
    finally:
        frappe.db.rollback();frappe.destroy()
