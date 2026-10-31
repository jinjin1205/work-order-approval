"""New B19 attachment cases against the native implementation; rollback-only fixture."""
import json
import os
import sys
import unittest
from pathlib import Path

import frappe
from frappe.permissions import add_permission, update_permission_property
from b08_distinct_concurrency_fixture import capture_tables, compare_tables, preserved
from b10_issue_fixture import TABLES


class TestB19Remaining(unittest.TestCase):
    def setUp(self):
        from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrderApproval
        self.f=TestWorkOrderApproval()
        self.f.setUp()
        self.addCleanup(self.f.clean_fixture)
        frappe.set_user('Administrator')
        role=self.f.roles[1]
        add_permission('File',role,ptype='read')
        for ptype in ('write','delete'):
            update_permission_property('File',role,0,ptype,1)
        update_permission_property('Item',role,0,'write',1)
        frappe.set_user(self.f.users['operator'])
        self.file=frappe.get_doc(dict(doctype='File',file_name=self.f.prefix+'-作业要求-v1.txt',
            content='B19合成作业要求v1',is_private=1,attached_to_doctype='Work Order',attached_to_name=self.f.order.name)).insert()
        self.original_bytes=self.file.get_content()
        self.f.act('operator','送审')
        frappe.set_user(self.f.users['reviewer'])
        self.assertTrue(frappe.has_permission('Work Order','write',doc=self.f.order))
        self.assertTrue(self.file.has_permission('write'))

    def test_frozen_attachment_metadata_cannot_be_changed(self):
        self.file.file_name='不可覆盖的已审批依据.txt'
        with self.assertRaises(frappe.PermissionError):
            self.file.save()
        current=frappe.get_doc('File',self.file.name)
        self.assertEqual(current.get_content(),self.original_bytes)
        self.assertNotEqual(current.file_name,self.file.file_name)

    def test_frozen_attachment_cannot_be_deleted(self):
        self.assertTrue(self.file.has_permission('delete'))
        with self.assertRaises(frappe.PermissionError):
            frappe.delete_doc('File',self.file.name)
        self.assertEqual(frappe.get_doc('File',self.file.name).get_content(),self.original_bytes)

    def test_frozen_attachment_cannot_be_relinked(self):
        self.file.attached_to_doctype='Item'
        self.file.attached_to_name=self.f.order.production_item
        with self.assertRaises(frappe.PermissionError):
            self.file.save()
        self.assertEqual(frappe.db.get_value('File',self.file.name,'attached_to_name'),self.f.order.name)

    def test_returned_draft_can_append_edit_delete_then_resubmit_attachment(self):
        self.f.act('reviewer','退回',reason='补充新版作业要求')
        frappe.set_user(self.f.users['operator'])
        with self.assertRaises(frappe.PermissionError):
            frappe.delete_doc('File',self.file.name)
        new=frappe.get_doc(dict(doctype='File',file_name=self.f.prefix+'-未送审.txt',content='可编辑的草稿资料',
            is_private=1,attached_to_doctype='Work Order',attached_to_name=self.f.order.name)).insert()
        new.file_name=self.f.prefix+'-草稿改名.txt';new.save()
        frappe.delete_doc('File',new.name)
        self.assertFalse(frappe.db.exists('File',new.name))
        second=frappe.get_doc(dict(doctype='File',file_name=self.f.prefix+'-作业要求v2.txt',content='B19新版作业要求v2',
            is_private=1,attached_to_doctype='Work Order',attached_to_name=self.f.order.name)).insert()
        self.f.act('operator','送审')
        frappe.set_user(self.f.users['reviewer'])
        second.file_name='不能改新版依据.txt'
        with self.assertRaises(frappe.PermissionError):second.save()
        self.assertEqual(frappe.get_doc('File',self.file.name).get_content(),self.original_bytes)
        self.assertNotEqual(frappe.get_doc('File',second.name).get_content(),self.original_bytes)
        late=frappe.get_doc(dict(doctype='File',file_name=self.f.prefix+'-送审后新增.txt',content='不可无审批追加',
            is_private=1,attached_to_doctype='Work Order',attached_to_name=self.f.order.name))
        with self.assertRaises(frappe.PermissionError):late.insert()

    def test_frozen_attachment_bytes_cannot_be_overwritten(self):
        with self.assertRaises(frappe.PermissionError):
            self.file.save_file(content=b'forbidden replacement',overwrite=True)
        self.assertEqual(frappe.get_doc('File',self.file.name).get_content(),self.original_bytes)

    def test_shared_file_cannot_make_frozen_basis_public(self):
        alias=frappe.get_doc(dict(doctype='File',file_name=self.file.file_name,file_url=self.file.file_url,
            is_private=1,attached_to_doctype='Item',attached_to_name=self.f.order.production_item)).insert()
        alias.is_private=0
        with self.assertRaises(frappe.PermissionError):alias.save()
        self.assertEqual(frappe.db.get_value('File',self.file.name,'is_private'),1)
        self.assertEqual(frappe.get_doc('File',self.file.name).get_content(),self.original_bytes)

    def test_native_workflow_import_twice_keeps_business_and_legacy_unapproved(self):
        from frappe.modules.import_file import import_doc
        frappe.set_user('Administrator')
        config=json.loads(Path('/tmp/b08-private/b19-workflow-import.json').read_text())
        self.assertEqual(config['document_type'],'Work Order')
        before=capture_tables(TABLES)
        for _ in range(2):
            imported=import_doc(json.loads(json.dumps(config)),data_import=True,ignore_version=True)
            self.assertEqual(imported.name,'生产工单两级审批')
            self.assertEqual(frappe.db.count('Workflow',{'document_type':'Work Order'}),1)
            self.assertEqual(len(imported.states),len(config['states']))
            self.assertEqual(len(imported.transitions),len(config['transitions']))
            self.assertNotEqual(frappe.db.get_value('Work Order',self.f.old_submitted.name,'workflow_state'),'已批准')
            retention=compare_tables(before)
            self.assertTrue(preserved(retention),retention)
            for doctype in ['Work Order','Work Order Item','Work Order Operation','Job Card','Stock Entry','Workflow Action']:
                self.assertEqual(retention[doctype]['new_rows'],0,doctype)

    def test_pending_action_queries_and_records_follow_parent_read(self):
        filters={'reference_doctype':'Work Order','reference_name':self.f.order.name}
        own=frappe.get_list('Workflow Action',filters=filters,fields=['name','reference_name'],limit_page_length=0)
        self.assertTrue(own)
        frappe.get_doc('Workflow Action',own[0].name).check_permission('read')
        frappe.set_user(self.f.users['other'])
        self.assertFalse(frappe.has_permission('Work Order','read',doc=self.f.order))
        self.assertFalse(frappe.get_list('Workflow Action',filters=filters,fields=['name'],limit_page_length=0))
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc('Workflow Action',own[0].name).check_permission('read')

    def test_action_select_only_and_single_parent_share_keep_exact_scope(self):
        from erpnext.manufacturing.doctype.work_order.work_order import apply_production_approval
        frappe.set_user(self.f.users['operator'])
        values={name:self.f.order.get(name)for name in ['production_item','bom_no','company','production_team','qty',
            'stock_uom','expected_delivery_date','planned_start_date','source_warehouse','wip_warehouse','fg_warehouse']}
        second=frappe.get_doc(dict(doctype='Work Order',**values)).insert()
        for row in self.f.order.operations:
            second.append('operations',dict(operation=row.operation,workstation=row.workstation,time_in_mins=1))
        second.set_required_items();second.save()
        apply_production_approval(second.name,'送审',str(second.modified))
        frappe.set_user('Administrator')
        update_permission_property('Work Order',self.f.roles[1],0,'read',0)
        update_permission_property('Work Order',self.f.roles[1],0,'select',1)
        frappe.clear_cache()
        frappe.set_user(self.f.users['reviewer'])
        self.assertFalse(frappe.has_permission('Work Order','read',doc=self.f.order))
        filters={'reference_doctype':'Work Order'}
        self.assertFalse(frappe.get_list('Workflow Action',filters=filters,fields=['reference_name'],limit_page_length=0))
        frappe.set_user('Administrator')
        frappe.share.add('Work Order',self.f.order.name,user=self.f.users['reviewer'],read=1)
        frappe.set_user(self.f.users['reviewer'])
        self.assertTrue(frappe.has_permission('Work Order','read',doc=self.f.order))
        self.assertFalse(frappe.has_permission('Work Order','read',doc=second))
        shared=frappe.get_list('Workflow Action',filters=filters,fields=['name','reference_name'],limit_page_length=0)
        self.assertEqual({r.reference_name for r in shared},{self.f.order.name})
        for row in shared:frappe.get_doc('Workflow Action',row.name).check_permission('read')

    def test_attachment_owner_loses_metadata_list_and_download_after_parent_scope_revoked(self):
        user=self.f.users['operator']
        frappe.set_user(user)
        self.assertTrue(self.file.has_permission('read'))
        self.assertTrue(self.file.is_downloadable())
        frappe.set_user('Administrator')
        other=frappe.db.get_value('Company',{'name':['!=',self.f.company]},'name')
        self.assertTrue(other)
        name=frappe.db.get_value('User Permission',{'user':user,'allow':'Company','for_value':self.f.company})
        permission=frappe.get_doc('User Permission',name);permission.for_value=other;permission.save()
        frappe.set_user(user)
        self.assertFalse(frappe.has_permission('Work Order','read',doc=self.f.order))
        self.assertFalse(self.file.has_permission('read'))
        self.assertFalse(self.file.is_downloadable())
        self.assertFalse(frappe.get_list('File',filters={'name':self.file.name},fields=['name']))

    def test_returned_draft_cannot_upload_public_approval_basis(self):
        self.f.act('reviewer','退回',reason='验证依据访问范围')
        frappe.set_user(self.f.users['operator'])
        public=frappe.get_doc(dict(doctype='File',file_name=self.f.prefix+'-公开依据.txt',content='B19合成审批依据不可公开',
            is_private=0,attached_to_doctype='Work Order',attached_to_name=self.f.order.name))
        with self.assertRaises(frappe.PermissionError):public.insert()

    def test_public_url_cannot_be_disguised_as_private_approval_attachment(self):
        self.f.act('reviewer','退回',reason='核对实际附件地址隐私')
        frappe.set_user('Administrator')
        public=frappe.get_doc(dict(doctype='File',file_name=self.f.prefix+'-公共源.txt',
            content='仅合成的公开源',is_private=0)).insert()
        frappe.set_user(self.f.users['operator'])
        disguised=frappe.get_doc(dict(doctype='File',file_name=public.file_name,file_url=public.file_url,
            is_private=1,attached_to_doctype='Work Order',attached_to_name=self.f.order.name))
        with self.assertRaises(frappe.PermissionError):disguised.insert()

    def test_unrelated_file_cannot_retarget_then_publish_frozen_basis_url(self):
        unrelated=frappe.get_doc(dict(doctype='File',file_name=self.f.prefix+'-无关私有源.txt',
            content='与冻结依据不同的原字节',is_private=1)).insert()
        self.assertNotEqual(unrelated.content_hash,self.file.content_hash)
        unrelated.file_url=self.file.file_url
        unrelated.is_private=0
        with self.assertRaises(frappe.PermissionError):unrelated.save()
        self.assertEqual(frappe.get_doc('File',self.file.name).get_content(),self.original_bytes)
        self.assertEqual(frappe.db.get_value('File',self.file.name,'is_private'),1)


if __name__=='__main__':
    os.chdir('sites'); frappe.init(site='xgd-test.localhost'); frappe.connect()
    try:
        assert frappe.conf.allow_tests and not frappe.db.exists('Workflow',{'document_type':'Work Order'})
        frappe.clear_cache()
        frappe.set_user('Administrator'); frappe.flags.in_test=True; frappe.flags.skip_test_records=True
        before=capture_tables(TABLES+['Workflow','Workflow Document State','Workflow Transition','Custom Field'])
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:]or['__main__.TestB19Remaining']))
        frappe.db.rollback(); frappe.set_user('Administrator')
        retention=compare_tables(before); assert preserved(retention),retention
        print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'old_tables_unchanged':len(retention)}))
    finally:
        frappe.db.rollback(); frappe.clear_cache(); frappe.destroy()
    sys.exit(0 if result.wasSuccessful() else 1)
