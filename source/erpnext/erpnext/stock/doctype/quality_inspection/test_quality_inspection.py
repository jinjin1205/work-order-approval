# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import nowdate

from erpnext.controllers.stock_controller import (
	QualityInspectionNotSubmittedError,
	QualityInspectionRejectedError,
	QualityInspectionRequiredError,
	make_quality_inspections,
)
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

# test_records = frappe.get_test_records('Quality Inspection')


class TestProductionNativeQuality(FrappeTestCase):
	def setUp(self):
		from erpnext.manufacturing.doctype.job_card.test_job_card import TestProductionReportConfirmation
		self.r = TestProductionReportConfirmation()
		self.addCleanup(self.r.doCleanups)
		self.r.setUp()
		self.report = self.r.report(1, 1)
		self.card = frappe.get_doc("Job Card", self.report["name"])
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.r.user).add_roles("Quality Manager")
		frappe.set_user(self.r.user)

	def make_inspection(self):
		return frappe.get_doc({"doctype": "Quality Inspection", "inspection_type": "In Process",
			"reference_type": "Job Card", "reference_name": self.card.name,
			"company": self.card.company, "item_code": self.card.production_item,
			"sample_size": 1, "inspected_by": self.r.user, "report_date": nowdate(),
			"manual_inspection": 1, "status": "Rejected"}).insert()

	def make_image(self, inspection, **changes):
		import hashlib
		from io import BytesIO
		from pathlib import Path
		from PIL import Image
		buffer = BytesIO()
		Image.frombytes("L", (32, 1), hashlib.sha256(self.r.approval.prefix.encode()).digest()).save(buffer, format="PNG")
		data = {"doctype": "File", "file_name": self.r.approval.prefix + "-quality.png",
			"content": buffer.getvalue(),
			"is_private": 1, "attached_to_doctype": "Quality Inspection", "attached_to_name": inspection.name}
		data.update(changes)
		image = frappe.get_doc(data)
		try:
			image.insert()
		finally:
			if image.file_url:
				path = Path(image.get_full_path())
				self.assertTrue(path.name.startswith(self.r.approval.prefix))
				self.addCleanup(lambda: path.unlink(missing_ok=True))
		return image

	def card_row(self):
		return frappe.as_json(frappe.get_all("Job Card", filters={"name": self.card.name}, fields=["*"])[0])

	def test_00_native_quality_and_private_png_runnable(self):
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		self.assertEqual((inspection.docstatus, inspection.reference_name, image.is_private), (0, self.card.name, 1))
		self.assertTrue(image.get_content())
		self.assertNotIn("System Manager", frappe.get_roles())
		self.assertEqual(type(image).__module__, "erpnext.manufacturing.production_quality")

	def test_saving_inspection_keeps_confirmed_report_row(self):
		before = self.card_row()
		inspection = self.make_inspection()
		inspection.submit()
		self.assertEqual(self.card_row(), before)
		inspection.cancel()
		self.assertEqual(self.card_row(), before)

	def test_owner_cannot_delete_image_after_inspection_submit(self):
		from pathlib import Path
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		path = Path(image.get_full_path())
		content = path.read_bytes()
		inspection.submit()
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("File", image.name)
		self.assertTrue(frappe.db.exists("File", image.name))
		self.assertEqual(path.read_bytes(), content)

	def test_private_file_owner_loses_read_after_quality_role_revoked(self):
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.r.user).remove_roles("Quality Manager")
		frappe.set_user(self.r.user)
		self.assertFalse(frappe.has_permission("Quality Inspection", "read", doc=inspection, throw=False))
		self.assertFalse(frappe.has_permission("File", "read", doc=image, throw=False))

	def test_only_one_shared_parent_can_be_read_and_queried(self):
		inspection = self.make_inspection()
		inspection.remarks = "xgd 100% O'Brien!"
		inspection.save()
		image = self.make_image(inspection)
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.r.user).remove_roles("生产报工")
		frappe.set_user(self.r.user)
		self.assertFalse(frappe.has_permission("Job Card", "read", doc=self.card, throw=False))
		self.assertFalse(frappe.has_permission("File", "read", doc=image, throw=False))
		self.assertEqual(frappe.get_list("Quality Inspection", filters={"reference_name": self.card.name}, pluck="name"), [])
		frappe.set_user("Administrator")
		frappe.share.add("Job Card", self.card.name, self.r.user, read=1, write=0, notify=0)
		frappe.set_user(self.r.user)
		self.assertTrue(frappe.has_permission("File", "read", doc=image, throw=False))
		self.assertEqual(frappe.get_list("Quality Inspection", filters={"remarks": ["like", "%O'Brien!%"]}, pluck="name"), [inspection.name])
		self.assertEqual(frappe.get_list("Quality Inspection", filters={"reference_name": self.card.name, "remarks": ["!=", inspection.remarks]}, pluck="name"), [])

	def test_parent_item_and_saved_reference_cannot_be_changed(self):
		inspection = self.make_inspection()
		other = self.r.report(1, 0, hour=11)
		inspection.reference_name = other["name"]
		with self.assertRaises(frappe.PermissionError):
			inspection.save()
		inspection.reload()
		inspection.item_code = frappe.db.get_value("Item", {"name": ["!=", self.card.production_item]}, "name")
		with self.assertRaises(frappe.ValidationError):
			inspection.save()

	def test_draft_image_delete_allowed_but_cancelled_history_frozen(self):
		from pathlib import Path
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		path = Path(image.get_full_path())
		frappe.delete_doc("File", image.name)
		self.assertFalse(path.exists())
		image = self.make_image(inspection)
		content = Path(image.get_full_path()).read_bytes()
		inspection.submit()
		inspection.cancel()
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Quality Inspection", inspection.name)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("File", image.name)
		self.assertEqual(Path(image.get_full_path()).read_bytes(), content)

	def test_native_plan_inspection_keeps_original_linkback(self):
		plan = frappe.get_doc("Job Card", self.r.plan_names[0])
		self.assertFalse(plan.report_request_id)
		inspection = self.make_inspection()
		# The new project branch may not reparent; create a separate native plan inspection.
		native = frappe.copy_doc(inspection)
		native.reference_name = plan.name
		native.insert().submit()
		self.assertEqual(frappe.db.get_value("Job Card", plan.name, "quality_inspection"), native.name)

	def test_invalid_public_images_and_direct_fact_attachment_rejected(self):
		inspection = self.make_inspection()
		for private in (0, "0"):
			with self.subTest(is_private=private), self.assertRaises(frappe.ValidationError):
				self.make_image(inspection, is_private=private)
		with self.assertRaises(frappe.ValidationError):
			self.make_image(inspection, content=b"not an image " + self.r.approval.prefix.encode())
		with self.assertRaises(frappe.PermissionError):
			self.make_image(inspection, attached_to_doctype="Job Card", attached_to_name=self.card.name)

	def test_locked_image_cannot_be_public_or_replaced(self):
		from pathlib import Path
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		path = Path(image.get_full_path())
		content = path.read_bytes()
		inspection.submit()
		image.file_url = "/private/files/not-this-image.png"
		with self.assertRaises(frappe.PermissionError):
			image.save()
		image.reload()
		image.is_private = 0
		with self.assertRaises(frappe.PermissionError):
			image.save()
		image.reload()
		self.assertEqual(path.read_bytes(), content)

	def test_unrelated_unattached_file_preserves_native_owner_permissions(self):
		from pathlib import Path
		inspection = self.make_inspection()
		image = self.make_image(inspection, attached_to_doctype=None, attached_to_name=None)
		path = Path(image.get_full_path())
		self.assertTrue(frappe.has_permission("File", "read", doc=image, throw=False))
		frappe.delete_doc("File", image.name)
		self.assertFalse(path.exists())

	def test_native_download_denied_after_quality_role_revoked(self):
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.r.user).remove_roles("Quality Manager")
		frappe.set_user(self.r.user)
		self.assertFalse(image.is_downloadable())

	def test_child_shares_cannot_bypass_parent_scope(self):
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		frappe.set_user("Administrator")
		for doc in (inspection, image):
			with self.subTest(doctype=doc.doctype), self.assertRaises(frappe.PermissionError):
				frappe.share.add(doc.doctype, doc.name, self.r.user, read=1, notify=0)

	def test_cancel_cannot_change_inspection_data_or_reference(self):
		for field, value in (("status", "Accepted"), ("reference_name", self.r.plan_names[0]),
			("sample_size", 2), ("readings", [{"specification": "changed", "status": "Rejected"}])):
			with self.subTest(field=field):
				inspection = self.make_inspection()
				inspection.submit()
				inspection.set(field, value)
				with self.assertRaises(frappe.PermissionError):
					inspection.cancel()

	def test_project_draft_with_image_can_be_deleted(self):
		from pathlib import Path
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		path = Path(image.get_full_path())
		frappe.delete_doc("Quality Inspection", inspection.name)
		self.assertFalse(frappe.db.exists("File", image.name))
		self.assertFalse(path.exists())

	def test_native_plan_draft_with_image_can_be_deleted(self):
		from pathlib import Path
		inspection = frappe.copy_doc(self.make_inspection())
		inspection.reference_name = self.r.plan_names[0]
		inspection.insert()
		image = self.make_image(inspection)
		path = Path(image.get_full_path())
		frappe.delete_doc("Quality Inspection", inspection.name)
		self.assertFalse(path.exists())

	def test_public_url_cannot_pretend_to_be_private(self):
		inspection = self.make_inspection()
		public = self.make_image(inspection, attached_to_doctype=None, attached_to_name=None, is_private=0)
		with self.assertRaises(frappe.ValidationError):
			self.make_image(inspection, content=None, file_url=public.file_url, is_private=1)

	def test_unattached_alias_cannot_publish_protected_shared_blob(self):
		from pathlib import Path
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		inspection.submit()
		alias = self.make_image(inspection, attached_to_doctype=None, attached_to_name=None)
		self.addCleanup(lambda: Path(alias.get_full_path()).unlink(missing_ok=True))
		self.assertEqual(alias.file_url, image.file_url)
		alias.is_private = 0
		with self.assertRaises(frappe.PermissionError):
			alias.save()
		image.reload()
		self.assertEqual(image.is_private, 1)
		self.assertTrue(Path(image.get_full_path()).exists())

	def test_file_list_and_shared_blob_download_follow_parent_read(self):
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		alias = self.make_image(inspection, attached_to_doctype=None, attached_to_name=None)
		self.assertEqual(alias.file_url, image.file_url)
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.r.user).remove_roles("生产报工")
		frappe.set_user(self.r.user)
		with self.subTest(boundary="list"):
			self.assertEqual(frappe.get_list("File", filters={"name": image.name}, pluck="name"), [])
		with self.subTest(boundary="download"):
			self.assertFalse(alias.is_downloadable())
		frappe.set_user("Administrator")
		frappe.share.add("Job Card", self.card.name, self.r.user, read=1, write=0, notify=0)
		frappe.set_user(self.r.user)
		self.assertTrue(alias.is_downloadable())
		self.assertEqual(frappe.get_list("File", filters={"name": image.name}, pluck="name"), [image.name])

	def test_zip_download_cannot_bypass_revoked_parent(self):
		from io import BytesIO
		from zipfile import ZipFile
		inspection = self.make_inspection()
		image = self.make_image(inspection)
		method = frappe.override_whitelisted_method("frappe.core.api.file.zip_files")
		frappe.get_attr(method)(frappe.as_json([image.name]))
		with ZipFile(BytesIO(frappe.response.filecontent)) as archive:
			self.assertEqual(archive.read(image.file_name), image.get_content())
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.r.user).remove_roles("Quality Manager")
		frappe.set_user(self.r.user)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_attr(method)(frappe.as_json([image.name]))

	def test_image_optimization_cannot_rewrite_locked_shared_binary(self):
		from io import BytesIO
		from pathlib import Path
		from PIL import Image
		inspection = self.make_inspection()
		buffer = BytesIO()
		Image.new("RGB", (32, 32), color="red").save(buffer, format="PNG", compress_level=0)
		image = self.make_image(inspection, content=buffer.getvalue())
		inspection.submit()
		path = Path(image.get_full_path())
		before = path.read_bytes()
		with self.assertRaises(frappe.PermissionError):
			image.optimize_file()
		self.assertEqual(path.read_bytes(), before)


class TestQualityInspection(FrappeTestCase):
	def setUp(self):
		super().setUp()
		create_item("_Test Item with QA")
		frappe.db.set_value("Item", "_Test Item with QA", "inspection_required_before_delivery", 1)

	def test_qa_for_delivery(self):
		make_stock_entry(
			item_code="_Test Item with QA", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)

		self.assertRaises(QualityInspectionRequiredError, dn.submit)

		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, status="Rejected"
		)
		dn.reload()
		self.assertRaises(QualityInspectionRejectedError, dn.submit)

		frappe.db.set_value("Quality Inspection", qa.name, "status", "Accepted")
		dn.reload()
		dn.submit()

		qa.reload()
		qa.cancel()
		dn.reload()
		dn.cancel()

	def test_qa_not_submit(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, do_not_submit=True
		)
		dn.items[0].quality_inspection = qa.name
		self.assertRaises(QualityInspectionNotSubmittedError, dn.submit)

		qa.delete()
		dn.delete()

	def test_doc_update_published_for_reference_on_submit(self):
		"""Submitting a QI publishes doc_update so open reference forms resync their timestamp."""
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, do_not_submit=True
		)

		with patch.object(frappe, "publish_realtime") as publish_realtime:
			qa.submit()

		reference_updates = [
			call
			for call in publish_realtime.call_args_list
			if call.args and call.args[0] == "doc_update" and call.kwargs.get("docname") == dn.name
		]
		self.assertEqual(len(reference_updates), 1)

		message = reference_updates[0].args[1]
		self.assertEqual(message["doctype"], "Delivery Note")
		self.assertEqual(message["modified"], frappe.db.get_value("Delivery Note", dn.name, "modified"))

	def test_value_based_qi_readings(self):
		# Test QI based on acceptance values (Non formula)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		readings = [
			{
				"specification": "Iron Content",  # numeric reading
				"min_value": 0.1,
				"max_value": 0.9,
				"reading_1": "0.4",
			},
			{
				"specification": "Particle Inspection Needed",  # non-numeric reading
				"numeric": 0,
				"value": "Yes",
				"reading_value": "Yes",
			},
		]

		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, readings=readings, do_not_save=True
		)

		qa.save()

		# status must be auto set as per formula
		self.assertEqual(qa.readings[0].status, "Accepted")
		self.assertEqual(qa.readings[1].status, "Accepted")

		qa.delete()
		dn.delete()

	def test_formula_based_qi_readings(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		readings = [
			{
				"specification": "Iron Content",  # numeric reading
				"formula_based_criteria": 1,
				"acceptance_formula": "reading_1 > 0.35 and reading_1 < 0.50",
				"reading_1": "0.4",
			},
			{
				"specification": "Calcium Content",  # numeric reading
				"formula_based_criteria": 1,
				"acceptance_formula": "reading_1 > 0.20 and reading_1 < 0.50",
				"reading_1": "0.7",
			},
			{
				"specification": "Mg Content",  # numeric reading
				"formula_based_criteria": 1,
				"acceptance_formula": "mean < 0.9",
				"reading_1": "0.5",
				"reading_2": "0.7",
				"reading_3": "random text",  # check if random string input causes issues
			},
			{
				"specification": "Calcium Content",  # non-numeric reading
				"formula_based_criteria": 1,
				"numeric": 0,
				"acceptance_formula": "reading_value in ('Grade A', 'Grade B', 'Grade C')",
				"reading_value": "Grade B",
			},
		]

		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, readings=readings, do_not_save=True
		)

		qa.save()

		# status must be auto set as per formula
		self.assertEqual(qa.readings[0].status, "Accepted")
		self.assertEqual(qa.readings[1].status, "Rejected")
		self.assertEqual(qa.readings[2].status, "Accepted")
		self.assertEqual(qa.readings[3].status, "Accepted")

		qa.delete()
		dn.delete()

	def test_make_quality_inspections_from_linked_document(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		for item in dn.items:
			item.sample_size = item.qty

		quality_inspections = make_quality_inspections(dn.company, dn.doctype, dn.name, dn.items)
		self.assertEqual(len(dn.items), len(quality_inspections))

		# cleanup
		for qi in quality_inspections:
			frappe.delete_doc("Quality Inspection", qi)
		dn.delete()

	def test_rejected_qi_validation(self):
		"""Test if rejected QI blocks Stock Entry as per Stock Settings."""
		se = make_stock_entry(
			item_code="_Test Item with QA",
			target="_Test Warehouse - _TC",
			qty=1,
			basic_rate=100,
			inspection_required=True,
			do_not_submit=True,
		)

		readings = [{"specification": "Iron Content", "min_value": 0.1, "max_value": 0.9, "reading_1": "1.0"}]

		qa = create_quality_inspection(
			reference_type="Stock Entry", reference_name=se.name, readings=readings, status="Rejected"
		)

		frappe.db.set_single_value("Stock Settings", "action_if_quality_inspection_is_rejected", "Stop")
		se.reload()
		self.assertRaises(
			QualityInspectionRejectedError, se.submit
		)  # when blocked in Stock settings, block rejected QI

		frappe.db.set_single_value("Stock Settings", "action_if_quality_inspection_is_rejected", "Warn")
		se.reload()
		se.submit()  # when allowed in Stock settings, allow rejected QI

		# teardown
		qa.reload()
		qa.cancel()
		se.reload()
		se.cancel()
		frappe.db.set_single_value("Stock Settings", "action_if_quality_inspection_is_rejected", "Stop")

	def test_qi_status(self):
		make_stock_entry(
			item_code="_Test Item with QA", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, status="Accepted", do_not_save=True
		)
		qa.readings[0].manual_inspection = 1
		qa.save()

		# Case - 1: When there are one or more readings with rejected status and parent manual inspection is unchecked, then parent status should be set to rejected.
		qa.status = "Accepted"
		qa.manual_inspection = 0
		qa.readings[0].status = "Rejected"
		qa.save()
		self.assertEqual(qa.status, "Rejected")

		# Case - 2: When all readings have accepted status and parent manual inspection is unchecked, then parent status should be set to accepted.
		qa.status = "Rejected"
		qa.manual_inspection = 0
		qa.readings[0].status = "Accepted"
		qa.save()
		self.assertEqual(qa.status, "Accepted")

		# Case - 3: When parent manual inspection is checked, then parent status should not be changed.
		qa.status = "Accepted"
		qa.manual_inspection = 1
		qa.readings[0].status = "Rejected"
		qa.save()
		self.assertEqual(qa.status, "Accepted")

	@change_settings("System Settings", {"number_format": "#.###,##"})
	def test_diff_number_format(self):
		self.assertEqual(frappe.db.get_default("number_format"), "#.###,##")  # sanity check

		# Test QI based on acceptance values (Non formula)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		readings = [
			{
				"specification": "Iron Content",  # numeric reading
				"min_value": 60,
				"max_value": 100,
				"reading_1": "70,000",
			},
			{
				"specification": "Iron Content",  # numeric reading
				"min_value": 60,
				"max_value": 100,
				"reading_1": "1.100,00",
			},
		]

		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, readings=readings, do_not_save=True
		)

		qa.save()

		# status must be auto set as per formula
		self.assertEqual(qa.readings[0].status, "Accepted")
		self.assertEqual(qa.readings[1].status, "Rejected")

		qa.delete()
		dn.delete()

	def test_delete_quality_inspection_linked_with_stock_entry(self):
		item_code = create_item("_Test Cicuular Dependecy Item with QA").name

		se = make_stock_entry(
			item_code=item_code, target="_Test Warehouse - _TC", qty=1, basic_rate=100, do_not_submit=True
		)

		se.inspection_required = 1
		se.save()

		qa = create_quality_inspection(
			item_code=item_code, reference_type="Stock Entry", reference_name=se.name, do_not_submit=True
		)

		se.reload()
		se.items[0].quality_inspection = qa.name
		se.save()

		qa.delete()

		se.reload()

		qc = se.items[0].quality_inspection
		self.assertFalse(qc)

		se.delete()

	def test_job_card_qi_keeps_manually_rejected_reading(self):
		create_quality_inspection_parameter("Finish")
		parameter = {"specification": "Finish", "numeric": 0, "value": "OK"}
		if not frappe.db.exists("Quality Inspection Template", "_Test QI Template Finish"):
			frappe.get_doc(
				{
					"doctype": "Quality Inspection Template",
					"quality_inspection_template_name": "_Test QI Template Finish",
					"item_quality_inspection_parameter": [parameter],
				}
			).insert()
		item = create_item("_Test Item QI Finish")
		item.db_set("quality_inspection_template", "_Test QI Template Finish")

		qa = create_quality_inspection(
			item_code=item.name,
			inspection_type="In Process",
			reference_type="Job Card",
			reference_name=make_minimal_job_card(production_item=item.name),
			readings=[
				dict(parameter, reading_value="Scratched", manual_inspection=1, status="Rejected"),
			],
			do_not_submit=True,
		)

		self.assertEqual(qa.readings[0].status, "Rejected")
		self.assertEqual(qa.status, "Rejected")


def make_minimal_job_card(production_item):
	"""db_insert a minimal submitted Job Card row carrying only the columns the
	converted UPDATE reads (name, production_item, quality_inspection, modified)."""
	jc = frappe.new_doc("Job Card")
	jc.name = "_T-Job Card-" + frappe.utils.random_string(10)
	jc.flags.name_set = True
	jc.production_item = production_item
	jc.company = "_Test Company"
	jc.for_quantity = 1
	jc.docstatus = 1
	jc.db_insert()
	return jc.name


def create_quality_inspection(**args):
	args = frappe._dict(args)
	qa = frappe.new_doc("Quality Inspection")
	qa.report_date = nowdate()
	qa.inspection_type = args.inspection_type or "Outgoing"
	qa.reference_type = args.reference_type
	qa.reference_name = args.reference_name
	qa.item_code = args.item_code or "_Test Item with QA"
	qa.sample_size = 1
	qa.inspected_by = frappe.session.user
	qa.status = args.status or "Accepted"

	if not args.readings:
		create_quality_inspection_parameter("Size")
		readings = {"specification": "Size", "min_value": 0, "max_value": 10, "reading_1": "5"}
		if args.status == "Rejected":
			readings["reading_1"] = "12"  # status is auto set in child on save
	else:
		readings = args.readings

	if isinstance(readings, list):
		for entry in readings:
			create_quality_inspection_parameter(entry["specification"])
			qa.append("readings", entry)
	else:
		qa.append("readings", readings)

	if not args.do_not_save:
		qa.save()
		if not args.do_not_submit:
			qa.submit()

	return qa


def create_quality_inspection_parameter(parameter):
	if not frappe.db.exists("Quality Inspection Parameter", parameter):
		frappe.get_doc(
			{"doctype": "Quality Inspection Parameter", "parameter": parameter, "description": parameter}
		).insert()
