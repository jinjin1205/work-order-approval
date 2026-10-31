"""Original B14 remaining configuration; native APIs, isolated fixtures, rollback."""
import json,os,sys,unittest
import frappe
from frappe.tests.utils import FrappeTestCase
from b08_distinct_concurrency_fixture import capture_tables,compare_tables,preserved

class TestB14NativeConfiguration(FrappeTestCase):
 def setUp(self):
  from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrderHeader
  self.h=TestWorkOrderHeader();self.addCleanup(self.h.doCleanups);self.h.setUp();self.f=self.h.f
  frappe.set_user('Administrator')
  self.manager=frappe.get_doc({'doctype':'User','email':self.f.prefix.lower()+'-config@example.invalid','first_name':'编号配置样例','send_welcome_email':0,'roles':[{'role':'System Manager'}]}).insert().name
  self.old=frappe.get_doc('Work Order',self.f.order.name).as_dict()
 def config(self,**overrides):
  frappe.set_user(self.manager)
  args={'doctype':'Document Naming Rule','document_type':'Work Order','prefix':self.f.prefix+'-CFG-','prefix_digits':5,'priority':10,'conditions':[{'field':'production_item','condition':'=','value':self.f.order.production_item}]}
  args.update(overrides);return frappe.get_doc(args)
 def draft(self):
  frappe.set_user(self.f.users['operator']);return self.h.draft()
 def test_rule_conditions_priority_disable_and_counter_conflict(self):
  rule=self.config().insert();low=self.config(prefix=self.f.prefix+'-LOW-',priority=1).insert()
  first=self.draft().insert();self.assertEqual(first.name,rule.prefix+'00001')
  frappe.set_user(self.manager);rule.reload();rule.disabled=1;rule.save(ignore_version=False)
  second=self.draft().insert();self.assertEqual(second.name,low.prefix+'00001');self.assertEqual(frappe.get_doc('Work Order',first.name).name,first.name)
  frappe.set_user(self.manager);rule.reload();rule.disabled=0;rule.counter=0;rule.save(ignore_version=False)
  count=frappe.db.count('Work Order');frappe.db.savepoint('collision')
  with self.assertRaises(frappe.DuplicateEntryError):self.draft().insert()
  frappe.db.rollback(save_point='collision');self.assertEqual(frappe.db.count('Work Order'),count)
  frappe.set_user('Administrator');self.assertTrue(frappe.db.exists('Version',{'ref_doctype':'Document Naming Rule','docname':rule.name}));self.assertEqual(frappe.get_doc('Work Order',self.f.order.name).as_dict(),self.old)
 def test_invalid_rule_and_configuration_permission_revocation(self):
  with self.assertRaises(frappe.ValidationError):self.config(conditions=[{'field':'b14_not_a_field','condition':'=','value':'x'}]).insert()
  with self.assertRaises(frappe.MandatoryError):self.config(prefix='').insert()
  rule=self.config().insert();frappe.set_user(self.f.users['operator'])
  self.assertFalse(frappe.has_permission('Document Naming Rule','read',doc=rule));self.assertFalse(frappe.has_permission('Document Naming Rule','create'))
  with self.assertRaises(frappe.PermissionError):rule.save()
  frappe.set_user('Administrator');frappe.get_doc('User',self.manager).remove_roles('System Manager');frappe.set_user(self.manager)
  with self.assertRaises(frappe.PermissionError):frappe.get_doc('Document Naming Rule',rule.name).check_permission('read')
  with self.assertRaises(frappe.PermissionError):rule.save()
 def test_company_default_save_read_conflict_and_disallowed_value(self):
  from frappe.permissions import add_user_permission
  user=self.f.users['operator'];other='_Test Company' if self.f.company!='_Test Company' else '_Test Company 1'
  frappe.set_user('Administrator');add_user_permission('Company',other,user)
  frappe.set_user(self.manager);row=frappe.get_doc('User Permission',frappe.db.get_value('User Permission',{'user':user,'allow':'Company','for_value':self.f.company}));row.is_default=1;row.save()
  other_row=frappe.get_doc('User Permission',frappe.db.get_value('User Permission',{'user':user,'allow':'Company','for_value':other}));other_row.is_default=1
  with self.assertRaises(frappe.ValidationError):other_row.save()
  frappe.set_user(user);frappe.local.new_doc_templates.clear();doc=frappe.new_doc('Work Order');self.assertEqual(doc.company,self.f.company);self.assertEqual(doc.qty,1);self.assertTrue(doc.planned_start_date)
  frappe.set_user(self.manager);row.is_default=0;row.save();other_row.reload();other_row.is_default=1;other_row.save()
  frappe.set_user(user);frappe.local.new_doc_templates.clear();self.assertEqual(frappe.new_doc('Work Order').company,other)
  # An arbitrary remembered value outside both allowed Companies must not become a default.
  frappe.defaults.set_user_default('company','B14-nonexistent-company');frappe.local.new_doc_templates.clear();self.assertEqual(frappe.new_doc('Work Order').company,other)
  self.assertEqual(frappe.get_doc('Work Order',self.f.order.name).as_dict(),self.old)
 def test_default_is_not_permission_after_revocation(self):
  user=self.f.users['operator'];frappe.set_user(user);frappe.local.new_doc_templates.clear();doc=self.draft();self.assertEqual(frappe.new_doc('Work Order').company,self.f.company)
  frappe.set_user('Administrator');perm=frappe.db.get_value('User Permission',{'user':user,'allow':'Company','for_value':self.f.company});frappe.delete_doc('User Permission',perm)
  count=frappe.db.count('Work Order');frappe.set_user(user)
  with self.assertRaises(frappe.PermissionError):doc.insert()
  self.assertEqual(frappe.db.count('Work Order'),count)

if __name__=='__main__':
 os.chdir('sites');frappe.init(site='xgd-test.localhost');frappe.connect()
 try:
  assert frappe.conf.allow_tests;assert not frappe.db.exists('Workflow',{'document_type':'Work Order'})
  frappe.set_user('Administrator');frappe.flags.in_test=True;frappe.flags.skip_test_records=True
  tables=['Work Order','Work Order Item','Work Order Operation','Job Card','Job Card Time Log','Stock Entry','Stock Entry Detail','Stock Ledger Entry','BOM','BOM Item','BOM Operation','User','Role','Has Role','User Permission','Custom DocPerm','Version','Comment','Workflow','Workflow Action','Document Naming Rule','Document Naming Rule Condition','DefaultValue','Property Setter']
  before=capture_tables(tables);names=sys.argv[1:]or['__main__.TestB14NativeConfiguration'];result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names));frappe.db.rollback();frappe.set_user('Administrator');checks=compare_tables(before);assert preserved(checks),checks
  print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'old_tables_unchanged':len(checks)}))
 finally:frappe.db.rollback();frappe.clear_cache();frappe.destroy()
 sys.exit(0 if result.wasSuccessful() else 1)
