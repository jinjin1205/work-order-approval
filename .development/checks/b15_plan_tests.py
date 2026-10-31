"""B15 plan conversion and soft grouping, original fixtures and rollback."""
import json,os,sys,unittest
import frappe
from frappe.tests.utils import FrappeTestCase
from b08_distinct_concurrency_fixture import capture_tables,compare_tables,preserved

class TestB15Plan(FrappeTestCase):
 def setUp(self):
  from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrderHeader
  from frappe.permissions import add_permission,update_permission_property
  self.h=TestWorkOrderHeader();self.addCleanup(self.h.doCleanups);self.h.setUp();self.f=self.h.f
  frappe.set_user('Administrator')
  for dt in ['Production Plan','Project']:
   add_permission(dt,self.f.roles[0],ptype='read')
   for perm in ['write','create']:update_permission_property(dt,self.f.roles[0],0,perm,1)
  self.project=frappe.get_doc({'doctype':'Project','project_name':self.f.prefix+'-assembly','company':self.f.company}).insert()
  bom=frappe.copy_doc(frappe.get_doc('BOM',self.f.order.bom_no));bom.docstatus=0;bom.is_default=0;bom.with_operations=1
  for i,operation in enumerate(self.f.operations,1):bom.append('operations',{'operation':operation,'workstation':self.f.workstation,'time_in_mins':1,'sequence_id':i})
  bom.insert().submit()
  self.plan=frappe.get_doc({'doctype':'Production Plan','company':self.f.company,'project':self.project.name,'po_items':[{'item_code':self.f.order.production_item,'bom_no':bom.name,'planned_qty':10,'planned_start_date':frappe.utils.now(),'warehouse':self.f.order.fg_warehouse,'stock_uom':'Nos'}]}).insert();self.plan.submit()
  self.args={'production_plan':self.plan.name,'production_plan_item':self.plan.po_items[0].name,'production_team':self.f.teams[0],'expected_delivery_date':self.f.order_args['expected_delivery_date']}
  self.old=frappe.get_doc('Work Order',self.f.order.name).as_dict();frappe.set_user(self.f.users['operator'])
 def preview(self,**overrides):
  from erpnext.manufacturing.doctype.production_plan.production_plan import preview_approval_work_order
  return preview_approval_work_order(**dict(self.args,**overrides))
 def confirm(self,preview=None,**overrides):
  from erpnext.manufacturing.doctype.production_plan.production_plan import confirm_approval_work_order
  return confirm_approval_work_order(**dict(self.args,fingerprint=(preview or self.preview())['fingerprint'],**overrides))
 def test_00_fixture(self):
  self.assertEqual(self.plan.docstatus,1);self.plan.check_permission('write');self.project.check_permission('read')
 def test_preview_confirm_retry_and_details(self):
  preview=self.preview();count=frappe.db.count('Work Order');self.assertEqual(preview['fields']['qty'],10);self.assertEqual(frappe.db.count('Work Order'),count)
  result=self.confirm(preview);order=frappe.get_doc('Work Order',result['work_order']);self.assertEqual(order.production_plan,self.plan.name);self.assertEqual(order.project,self.project.name);self.assertEqual(order.workflow_state,'草稿');self.assertFalse(order.operations or order.required_items)
  self.assertEqual(self.confirm(preview)['work_order'],order.name);self.assertEqual(frappe.db.count('Work Order'),count+1)
  from erpnext.manufacturing.doctype.work_order.work_order import preview_production_order_details,confirm_production_order_details
  details=preview_production_order_details(order.name,str(order.modified));confirm_production_order_details(order.name,str(order.modified),details['fingerprint']);self.assertTrue(order.reload().operations);self.assertEqual(frappe.get_doc('Work Order',self.f.order.name).as_dict(),self.old)
 def test_changed_source_bad_row_and_old_entry(self):
  preview=self.preview();frappe.set_user('Administrator');frappe.db.set_value('Production Plan Item',self.args['production_plan_item'],'planned_qty',11);frappe.set_user(self.f.users['operator'])
  with self.assertRaises(frappe.TimestampMismatchError):self.confirm(preview)
  with self.assertRaises(frappe.ValidationError):self.preview(production_plan_item='not-this-plan')
  with self.assertRaises(frappe.PermissionError):frappe.get_doc('Production Plan',self.plan.name).make_work_order()
 def test_permissions_revocation_and_no_provenance_spoof(self):
  preview=self.preview();frappe.set_user(self.f.users['outsider'])
  with self.assertRaises(frappe.PermissionError):self.confirm(preview)
  frappe.set_user(self.f.users['operator'])
  with self.assertRaises(frappe.PermissionError):self.h.draft(production_plan=self.plan.name,production_plan_item=self.args['production_plan_item']).insert()
  frappe.set_user('Administrator');frappe.delete_doc('User Permission',frappe.db.get_value('User Permission',{'user':self.f.users['operator'],'allow':'Company','for_value':self.f.company}));frappe.set_user(self.f.users['operator'])
  with self.assertRaises(frappe.PermissionError):self.confirm(preview)
 def test_soft_group_unlink_history_and_no_cascade(self):
  result=self.confirm();order=frappe.get_doc('Work Order',result['work_order']);order.project=None;order.save(ignore_version=False);self.assertTrue(frappe.db.exists('Version',{'ref_doctype':'Work Order','docname':order.name}));self.assertEqual(order.production_plan,self.plan.name)
  before=frappe.get_doc('Work Order',order.name).as_dict();frappe.set_user('Administrator');self.project.project_name+=' changed';self.project.save();frappe.db.set_value('Production Plan',self.plan.name,'project',None);self.assertEqual(frappe.get_doc('Work Order',order.name).as_dict(),before)
  frappe.set_user(self.f.users['operator']);order.production_plan=None;order.production_plan_item=None
  with self.assertRaises(frappe.PermissionError):order.save()
  frappe.set_user('Administrator')
  with self.assertRaisesRegex(frappe.ValidationError,'Submitted Record'):frappe.delete_doc('Production Plan',self.plan.name)
  self.assertEqual(frappe.get_doc('Work Order',order.name).as_dict(),before)
 def test_plan_approval_cancel_and_same_source_amendment(self):
  from frappe.permissions import update_permission_property
  from frappe.tests.utils import change_settings
  from erpnext.manufacturing.doctype.work_order.work_order import preview_production_order_details,confirm_production_order_details
  result=self.confirm();order=frappe.get_doc('Work Order',result['work_order']);order.source_warehouse=self.f.order.source_warehouse;order.wip_warehouse=self.f.order.wip_warehouse;order.save();details=preview_production_order_details(order.name,str(order.modified));confirm_production_order_details(order.name,str(order.modified),details['fingerprint']);self.f.order=order.reload()
  self.f.act('operator','送审');self.f.act('reviewer','审核通过')
  with change_settings('Manufacturing Settings',{'disable_capacity_planning':1}):self.f.act('director','签批通过')
  self.assertEqual(self.f.order.docstatus,1);self.assertEqual(frappe.db.get_value('Production Plan Item',self.args['production_plan_item'],'ordered_qty'),10)
  frappe.set_user('Administrator');update_permission_property('Work Order',self.f.roles[2],0,'cancel',1);self.f.act('director','取消修订',reason='B15计划修订验收')
  cancelled=frappe.get_doc('Work Order',order.name).as_dict();frappe.set_user(self.f.users['operator'])
  amended=self.h.draft(bom_no=order.bom_no,project=order.project,amended_from=order.name,production_plan=self.plan.name,production_plan_item=self.args['production_plan_item']).insert()
  self.assertEqual(amended.production_plan,self.plan.name);self.assertFalse(amended.operations or amended.required_items);self.assertEqual(amended.amended_from,order.name);self.assertEqual(frappe.get_doc('Work Order',order.name).as_dict(),cancelled)
  with self.assertRaises(frappe.PermissionError):self.h.draft(amended_from=order.name,production_plan=self.plan.name,production_plan_item='forged-source-row').insert()
 def test_cross_company_project_and_foreign_row(self):
  frappe.set_user('Administrator');other=frappe.get_doc({'doctype':'Project','project_name':self.f.prefix+'-other','company':'_Test Company' if self.f.company!='_Test Company' else '_Test Company 1'}).insert();frappe.set_user(self.f.users['operator'])
  with self.assertRaises(frappe.PermissionError):self.h.draft(project=other.name).insert()
  with self.assertRaises(frappe.ValidationError):self.preview(production_plan_item=self.f.order.name)

if __name__=='__main__':
 os.chdir('sites');frappe.init(site='xgd-test.localhost');frappe.connect()
 try:
  assert frappe.conf.allow_tests;assert not frappe.db.exists('Workflow',{'document_type':'Work Order'});frappe.set_user('Administrator');frappe.flags.in_test=True;frappe.flags.skip_test_records=True
  tables=['Work Order','Work Order Item','Work Order Operation','Job Card','Job Card Time Log','Stock Entry','Stock Entry Detail','Stock Ledger Entry','Bin','BOM','BOM Item','BOM Operation','User','Role','Has Role','User Permission','Custom DocPerm','Version','Comment','Workflow','Workflow Action','Production Plan','Production Plan Item','Project']
  before=capture_tables(tables);result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:]or['__main__.TestB15Plan']));frappe.db.rollback();frappe.set_user('Administrator');checks=compare_tables(before);assert preserved(checks),checks;print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'old_tables_unchanged':len(checks)}))
 finally:frappe.db.rollback();frappe.clear_cache();frappe.destroy()
 sys.exit(0 if result.wasSuccessful() else 1)
