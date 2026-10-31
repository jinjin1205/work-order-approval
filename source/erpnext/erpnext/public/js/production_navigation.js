// Copyright (c) 2026, Contributors
// License: GNU General Public License v3. See license.txt
frappe.provide("erpnext.production_navigation");

erpnext.production_navigation.open = function () {
	const origin_route = frappe.get_route_str();
	let scanner;
	const dialog = new frappe.ui.Dialog({
		title: "扫码或输入定位",
		fields: [
			{fieldname: "code", fieldtype: "Data", label: "工单号、作业卡号或本站单据链接", reqd: 1},
			{fieldname: "status", fieldtype: "HTML", options: "<p>扫码只定位有权单据，不会报工或过账。摄像头不可用时可手动输入单号。</p>"},
		],
		primary_action_label: "定位",
		primary_action: ({code}) => locate(code),
	});
	async function locate(code) {
		dialog.get_primary_btn().prop("disabled", true);
		try {
			const {message: target} = await frappe.call({method: "erpnext.manufacturing.doctype.work_order.work_order.resolve_production_code", args: {code}});
			if (frappe.get_route_str() !== origin_route || !dialog.$wrapper.is(":visible")) return;
			dialog.hide();
			await frappe.set_route("Form", target.doctype, target.name);
		} catch (error) {
			// UI boundary: preserve the scanned/input value and make failure actionable.
			dialog.fields_dict.status.$wrapper.html("<p>定位未完成，请按错误提示核对单号或联系负责人授权；也可从工单列表手动查找。</p>");
		} finally {
			dialog.get_primary_btn().prop("disabled", false);
		}
	}
	dialog.set_secondary_action(() => {
		let received = false;
		scanner = new frappe.ui.Scanner({dialog: true, multiple: false, on_scan: (result) => {
			received = true;
			dialog.set_value("code", result.decodedText);
			locate(result.decodedText);
		}});
		scanner.dialog.$wrapper.one("hidden.bs.modal", () => {
			if (!received) dialog.fields_dict.status.$wrapper.html("<p>扫描未完成或摄像头不可用。请检查相机权限、使用安全连接，或手动输入单号定位。</p>");
		});
	});
	dialog.set_secondary_action_label("打开摄像头");
	dialog.show();
};
