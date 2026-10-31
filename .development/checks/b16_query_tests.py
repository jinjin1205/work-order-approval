"""B16 scoped reports; existing real confirmation fixture, rollback, no parallel facts."""
import json,os,sys,unittest
import frappe
from frappe.tests.utils import FrappeTestCase
from b08_distinct_concurrency_fixture import capture_tables,compare_tables,preserved

class TestB16Query(FrappeTestCase):
 def setUp(self):
  from erpnext.manufacturing.doctype.job_card.test_job_card import TestProductionReportConfirmation
  from frappe.permissions import add_permission,update_permission_property
  self.r=TestProductionReportConfirmation();self.addCleanup(self.r.doCleanups);self.r.setUp(before_approval=(lambda f,employee:setattr(f.order.required_items[0],'required_qty',0)) if self._testMethodName=='test_zero_requirement_progress' else None);self.f=self.r.approval;self.card=self.r.report(2,1)['name']
  frappe.set_user('Administrator')
  for dt in ['Work Order','Job Card']:
   for p in ['report','export']:update_permission_property(dt,'生产报工',0,p,1)
  update_permission_property('Job Card','生产报工',0,'cancel',1)
  for report in ['Work Order Consumed Materials','Job Card Summary']:
   doc=frappe.get_doc('Report',report);assert not frappe.db.exists('Custom Role',{'report':report});frappe.get_doc({'doctype':'Custom Role','report':report,'roles':[{'role':row.role}for row in doc.roles]+[{'role':'生产报工'}]}).insert()
  frappe.set_user(self.r.user);self.filters=frappe._dict(company=self.f.company,from_date='2026-10-01',to_date='2026-10-31',production_reports=1)
 def materials(self,**changes):
  from erpnext.manufacturing.report.work_order_consumed_materials.work_order_consumed_materials import execute
  return execute(frappe._dict(self.filters,**changes))
 def reports(self,**changes):
  from erpnext.manufacturing.report.job_card_summary.job_card_summary import execute
  return execute(frappe._dict(self.filters,**changes))
 def test_materials_only_authorized_no_filter_and_missing_consumption(self):
  cols,rows=self.materials();self.assertEqual({r['name']for r in rows},{self.r.order.name});self.assertTrue(rows);self.assertIsNone(rows[0]['consumed_qty']);self.assertEqual(rows[0]['consumption_status'],'未记录');self.assertEqual(rows[0]['raw_material_uom'],'Nos');self.assertEqual(rows[0]['net_qty'],0)
  with self.assertRaises(frappe.PermissionError):self.materials(name=self.f.old_submitted.name)
 def test_reports_saved_metrics_no_plan_cards_and_cancelled_separate(self):
  cols,rows,*rest=self.reports();self.assertEqual([r['name']for r in rows],[self.card]);self.assertEqual(rows[0]['good_qty'],2);self.assertEqual(rows[0]['bad_qty'],1);self.assertAlmostEqual(float(rows[0]['quality_percent']),200/3);self.assertEqual(rows[0]['unit'],'Nos')
  original=frappe.get_doc('Job Card',self.card).as_dict();result=self.r.method('correct_production_report')(self.card,frappe.generate_hash(length=32),1,1,'B16只验证查询口径');_,effective,*_=self.reports();_,cancelled,*_=self.reports(report_state='已取消')
  self.assertEqual([x['name']for x in effective],[result['name']]);self.assertEqual([x['name']for x in cancelled],[self.card]);self.assertEqual(cancelled[0]['good_qty'],original.total_completed_qty);self.assertEqual(effective[0]['amended_from'],self.card)
 def test_mixed_ids_date_and_revocation(self):
  with self.assertRaises(frappe.PermissionError):self.reports(work_order=[self.r.order.name,self.f.old_submitted.name])
  self.assertFalse(self.reports(from_date='2026-01-01',to_date='2026-01-02')[1])
  with self.assertRaises(frappe.ValidationError):self.reports(from_date='2026-11-01',to_date='2026-10-01')
  frappe.set_user('Administrator');frappe.delete_doc('User Permission',frappe.db.get_value('User Permission',{'user':self.r.user,'allow':'Work Order','for_value':self.r.order.name}));frappe.get_doc('User',self.r.user).remove_roles('生产报工');frappe.set_user(self.r.user)
  with self.assertRaises(frappe.PermissionError):self.reports()
 def test_cross_team_parent_read_not_task_or_child_share(self):
  frappe.set_user('Administrator');frappe.share.add('Job Card',self.card,self.f.users['other'],read=1,notify=0);frappe.set_user(self.f.users['other']);self.assertFalse(frappe.has_permission('Work Order','read',doc=self.r.order))
  with self.assertRaises(frappe.PermissionError):self.materials(name=self.r.order.name)
  with self.assertRaises(frappe.PermissionError):self.reports(work_order=[self.r.order.name])
 def test_zero_requirement_progress(self):
  row=self.materials()[1][0];self.assertEqual(row['required_qty'],0);self.assertEqual(row['material_issue_percent'],'—');self.assertIsNone(row['consumed_qty'])
 def test_zero_time_and_missing_snapshot_remain_explicit(self):
  args=dict(work_order=self.r.order.name,operation_id=self.r.operation_id,from_time='2026-10-20 13:00:00',to_time='2026-10-20 13:00:00')
  preview=self.r.method('preview_production_report_time')(**args);result=self.r.method('confirm_production_report')(**args,request_id=frappe.generate_hash(length=32),good_quantity=1,bad_quantity=0,context_fingerprint=preview['context_fingerprint']);row=next(r for r in self.reports()[1]if r['name']==result['name']);self.assertEqual(row['effective_seconds'],0);self.assertEqual(row['actual_efficiency'],'—');self.assertEqual(row['quality_percent'],100)
  # Only this rollback fixture: represent an imported legacy fact missing its historical basis.
  frappe.db.set_value('Job Card',result['name'],'report_metrics_context',None);row=next(r for r in self.reports()[1]if r['name']==result['name']);self.assertEqual(row['basis_status'],'缺少历史指标快照');self.assertEqual(row['actual_efficiency'],'—');self.assertEqual(row['estimated_wage'],'—')
 def test_native_run_csv_matches_rows_and_export_not_read(self):
  from frappe.desk.query_report import run,export_query
  from frappe.permissions import update_permission_property
  filters=dict(self.filters);result=run('Job Card Summary',filters=filters);self.assertEqual([x['name']for x in result['result']],[self.card])
  oldform=frappe.local.form_dict;frappe.local.form_dict=frappe._dict(report_name='Job Card Summary',filters=json.dumps(filters),file_format_type='CSV',export_in_background=0,visible_idx='[]')
  try:
   export_query();csv=frappe.local.response.filecontent;csv=csv.decode('utf-8-sig')if isinstance(csv,bytes)else csv;self.assertIn(self.card,csv);self.assertIn('良品数量',csv);self.assertNotIn(self.r.plan_names[0],csv)
   frappe.set_user('Administrator');update_permission_property('Job Card','生产报工',0,'export',0);frappe.set_user(self.r.user);self.assertTrue(frappe.has_permission('Job Card','read'));frappe.local.form_dict=frappe._dict(report_name='Job Card Summary',filters=json.dumps(filters),file_format_type='CSV',export_in_background=0,visible_idx='[]')
   with self.assertRaises(frappe.PermissionError):export_query()
  finally:frappe.local.form_dict=oldform

if __name__=='__main__':
 os.chdir('sites');frappe.init(site='xgd-test.localhost');frappe.connect()
 try:
  assert frappe.conf.allow_tests;assert not frappe.db.exists('Workflow',{'document_type':'Work Order'});frappe.set_user('Administrator');frappe.flags.in_test=True;frappe.flags.skip_test_records=True
  tables=['Work Order','Work Order Item','Work Order Operation','Job Card','Job Card Time Log','Stock Entry','Stock Entry Detail','Stock Ledger Entry','Bin','BOM','BOM Item','BOM Operation','User','Role','Has Role','User Permission','Custom DocPerm','Version','Comment','Workflow','Workflow Action','Report','Has Role','Custom Field','Custom Role']
  before=capture_tables(list(dict.fromkeys(tables)));result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:]or['__main__.TestB16Query']));frappe.db.rollback();frappe.set_user('Administrator');checks=compare_tables(before);assert preserved(checks),checks;print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'old_tables_unchanged':len(checks)}))
 finally:frappe.db.rollback();frappe.clear_cache();frappe.destroy()
 sys.exit(0 if result.wasSuccessful() else 1)
