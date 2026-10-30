# Copyright (c) 2026, Contributors
# License: GNU General Public License v3. See license.txt

"""Native inspection/file boundaries for confirmed production reports only."""
from io import BytesIO

import frappe
from frappe.core.doctype.file.file import File
from frappe.model.db_query import DatabaseQuery
from frappe.utils import cint


def report_for_inspection(doc):
	if doc.reference_type != "Job Card" or not doc.reference_name:
		return None
	card = frappe.get_doc("Job Card", doc.reference_name)
	return card if card.get("report_request_id") else None


def validate_inspection(doc):
	from erpnext.manufacturing.doctype.work_order.work_order import _check_production_approval_scope

	old = doc.get_doc_before_save()
	if old and report_for_inspection(old) and (old.reference_type, old.reference_name) != (doc.reference_type, doc.reference_name):
		frappe.throw("关联报工不能改挂，请另建质检草稿", frappe.PermissionError)
	card = report_for_inspection(doc)
	if not card:
		return
	card.check_permission("read")
	_check_production_approval_scope(frappe.get_doc("Work Order", card.work_order), team_required=True)
	if card.docstatus != 1 and not (old and old.docstatus == 1 and doc.docstatus == 2):
		frappe.throw("只能为已确认且未冲销的报工新建或提交质检", frappe.PermissionError)
	if doc.inspection_type != "In Process" or doc.item_code != card.production_item:
		frappe.throw("质检类型或物料与关联报工不一致")
	if doc.company and doc.company != card.company:
		frappe.throw("质检公司与关联报工不一致", frappe.PermissionError)
	doc.company = card.company


def protect_inspection_delete(doc):
	if report_for_inspection(doc) and frappe.db.get_value("Quality Inspection", doc.name, "docstatus"):
		frappe.throw("已提交或取消的报工质检必须保留历史，不能删除", frappe.PermissionError)


def protect_inspection_cancel(doc):
	old = doc.get_doc_before_save()
	if not (report_for_inspection(old) or report_for_inspection(doc)):
		return

	def persisted_values(value):
		fields = value.get_valid_dict(convert_dates_to_str=True)
		for field in ("docstatus", "modified", "modified_by"):
			fields.pop(field, None)
		for field in value.meta.get_table_fields():
			fields[field.fieldname] = [persisted_values(row) for row in value.get(field.fieldname)]
		return fields

	if persisted_values(old) != persisted_values(doc):
		frappe.throw("取消质检不能夹带修改检验数据或关联，请保留原单另建质检", frappe.PermissionError)
	validate_inspection(doc)


def has_inspection_permission(doc, ptype=None, user=None, debug=False):
	card = report_for_inspection(doc)
	if card and ptype == "share":
		return False
	if card and not frappe.has_permission("Job Card", "read", doc=card, user=user, throw=False):
		return False
	return None  # Native inspection roles remain required; share the parent report only.


def _read_match(doctype, user):
	perms = frappe.permissions.get_role_permissions(frappe.get_meta(doctype), user=user)
	if perms.get("read"):
		return DatabaseQuery(doctype, user=user).build_match_conditions() or "1=1"
	shared = frappe.share.get_shared(doctype, user, rights=["read"])
	return f"`tab{doctype}`.name in ({', '.join(frappe.db.escape(name) for name in shared)})" if shared else "0=1"


def inspection_query_conditions(user=None):
	match = _read_match("Job Card", user or frappe.session.user)
	# Native match SQL is already escaped. Do not apply a second %-formatting pass.
	return f"""(`tabQuality Inspection`.reference_type != 'Job Card'
		or not exists (select 1 from `tabJob Card` where
			`tabJob Card`.name = `tabQuality Inspection`.reference_name
			and coalesce(`tabJob Card`.report_request_id, '') != '')
		or exists (select 1 from `tabJob Card` where
			`tabJob Card`.name = `tabQuality Inspection`.reference_name and ({match})))"""


def file_query_conditions(user=None):
	user = user or frappe.session.user
	card_match = _read_match("Job Card", user)
	inspection_match = _read_match("Quality Inspection", user)
	return f"""(not exists (select 1 from `tabJob Card` where
		`tabFile`.attached_to_doctype = 'Job Card' and `tabJob Card`.name = `tabFile`.attached_to_name
		and coalesce(`tabJob Card`.report_request_id, '') != '' and not ({card_match}))
		and not exists (select 1 from `tabQuality Inspection` join `tabJob Card`
		on `tabQuality Inspection`.reference_type = 'Job Card'
		and `tabQuality Inspection`.reference_name = `tabJob Card`.name
		where `tabFile`.attached_to_doctype = 'Quality Inspection'
		and `tabQuality Inspection`.name = `tabFile`.attached_to_name
		and coalesce(`tabJob Card`.report_request_id, '') != ''
		and not (({card_match}) and ({inspection_match}))))"""


def _file_parents(doc):
	if not doc.attached_to_name:
		return None, None
	if doc.attached_to_doctype == "Quality Inspection":
		inspection = frappe.get_doc("Quality Inspection", doc.attached_to_name)
		return inspection, report_for_inspection(inspection)
	if doc.attached_to_doctype == "Job Card":
		card = frappe.get_doc("Job Card", doc.attached_to_name)
		return None, card if card.get("report_request_id") else None
	return None, None


def has_file_permission(doc, ptype=None, user=None, debug=False):
	inspection, card = _file_parents(doc)
	if not card:
		return None
	if ptype == "share":
		return False
	if not frappe.has_permission("Job Card", "read", doc=card, user=user, throw=False):
		return False
	if inspection and not frappe.has_permission("Quality Inspection", "read", doc=inspection, user=user, throw=False):
		return False
	if ptype in ("write", "create", "delete") and (not inspection or inspection.docstatus != 0):
		return False
	return None


def protect_quality_share(doc, method=None):
	if doc.share_doctype == "Quality Inspection":
		protected = report_for_inspection(frappe.get_doc(doc.share_doctype, doc.share_name))
	elif doc.share_doctype == "File":
		protected = _file_parents(frappe.get_doc("File", doc.share_name))[1]
	else:
		return
	if protected:
		frappe.throw("报工质检及其图片不能单独分享，请在父报工授权并保留质检岗位权限", frappe.PermissionError)


def _file_download_scope(doc):
	for alias in frappe.get_all("File", filters={"file_url": doc.file_url}, pluck="name"):
		if has_file_permission(frappe.get_doc("File", alias), "read") is False:
			return False
	return True


@frappe.whitelist()
def zip_quality_files(files):
	from frappe.core.api.file import zip_files
	for name in frappe.parse_json(files):
		if isinstance(name, str) and not _file_download_scope(frappe.get_doc("File", name)):
			frappe.throw("没有关联报工或质检的图片读取权限", frappe.PermissionError)
	return zip_files(files)


class ProductionQualityFile(File):
	def has_permission(self, permtype="read", *, debug=False, user=None):
		if has_file_permission(self, permtype, user, debug) is False:
			return False
		return super().has_permission(permtype, debug=debug, user=user)

	def is_downloadable(self):
		# Native downloads call this directly, bypassing generic has_permission hooks.
		return _file_download_scope(self) and super().is_downloadable()

	def set_is_private(self):
		super().set_is_private()
		if _file_parents(self)[1] and cint(self.is_private) != 1:
			frappe.throw("报工质检图片必须使用本地私有附件")

	def save_file(self, content=None, decode=False, ignore_existing_file_check=False, overwrite=False):
		if overwrite:
			for name in frappe.get_all("File", filters={"file_url": self.file_url}, pluck="name"):
				if _file_parents(frappe.get_doc("File", name))[1]:
					frappe.throw("报工质检图片不能覆盖，请在质检草稿移除后重新上传", frappe.PermissionError)
		return super().save_file(content, decode, ignore_existing_file_check, overwrite)

	def _validate_quality_write(self):
		from erpnext.manufacturing.doctype.work_order.work_order import _check_production_approval_scope

		old = self.get_doc_before_save()
		protected = None
		for candidate in (old, self):
			if not candidate:
				continue
			inspection, card = _file_parents(candidate)
			if not card:
				continue
			if candidate is self:
				protected = card
			card.check_permission("read")
			_check_production_approval_scope(frappe.get_doc("Work Order", card.work_order), team_required=True)
			if not inspection or inspection.docstatus != 0:
				frappe.throw("已确认报工或已提交/取消质检的图片不能改写或删除，请使用质检草稿追加资料", frappe.PermissionError)
			inspection.check_permission("write")
			if cint(self.is_private) != 1 or self.is_remote_file:
				frappe.throw("报工质检图片必须使用本地私有附件")
			if old and any(old.get(field) != self.get(field) for field in (
				"attached_to_doctype", "attached_to_name", "file_url", "content_hash", "file_name"
			)):
				frappe.throw("质检图片不能改挂或覆盖，请在草稿中移除后重新上传", frappe.PermissionError)
		return protected

	def before_insert(self):
		protected = self._validate_quality_write()
		super().before_insert()
		if protected:
			from PIL import Image, UnidentifiedImageError
			try:
				with Image.open(BytesIO(self.get_content())) as image:
					if image.format not in ("PNG", "JPEG", "WEBP"):
						frappe.throw("本包只支持PNG、JPEG或WebP图片")
					image.verify()
			except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
				raise frappe.ValidationError("质检图片内容无效，请上传有效PNG、JPEG或WebP图片") from error

	def validate(self):
		if not self.is_new():
			self._validate_quality_write()
			old = self.get_doc_before_save()
			if cint(old.is_private) != cint(self.is_private):
				# Native privacy changes move the binary and update same-content aliases.
				for name in frappe.get_all("File", filters={"content_hash": old.content_hash}, pluck="name"):
					if _file_parents(frappe.get_doc("File", name))[1]:
						frappe.throw("共享图片仍关联报工质检，不能改变私有性", frappe.PermissionError)
		super().validate()

	def on_trash(self):
		self._validate_quality_write()
		super().on_trash()
