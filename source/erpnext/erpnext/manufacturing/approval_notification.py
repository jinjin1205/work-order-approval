import hashlib
import os
from functools import partial
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests
from redis.exceptions import RedisError

import frappe


def mask_order(name):
	return "WO-" + hashlib.sha256(name.encode()).hexdigest()[:12].upper()


def notification_payload(masked_order, state, login_url):
	return {"msgtype": "text", "text": {"content": (
		f"生产工单待办\n工单：{masked_order}\n审批状态：{state}\n请登录系统查看获准待办：{login_url}"
	)}}


def read_config(secret_file, login_url):
	if not isinstance(secret_file, str) or not secret_file or not isinstance(login_url, str):
		raise ValueError("请配置机器人密钥文件和登录地址")
	path = Path(secret_file)
	with path.open(encoding="utf-8") as source:
		stat = os.fstat(source.fileno())
		if stat.st_uid != os.geteuid() or stat.st_mode & 0o077:
			raise ValueError("机器人配置文件必须仅由服务账号读取")
		values = [value.strip() for line in source for key, sep, value in [line.partition("=")]
			if sep and key.strip() == "B18_ASSEMBLY_APPROVAL_WEBHOOK"]
	if len(values) != 1:
		raise ValueError("机器人配置项缺失或重复")
	webhook_url = values[0]
	if len(webhook_url) >= 2 and webhook_url[0] == webhook_url[-1] and webhook_url[0] in "\"'":
		webhook_url = webhook_url[1:-1]
	webhook = urlsplit(webhook_url)
	login = urlsplit(login_url or "")
	query = parse_qs(webhook.query)
	if (webhook.scheme != "https" or webhook.netloc != "qyapi.weixin.qq.com"
		or webhook.path != "/cgi-bin/webhook/send" or webhook.fragment
		or set(query) != {"key"} or len(query["key"]) != 1):
		raise ValueError("请配置审批群的企业微信机器人地址")
	if (login.scheme != "https" or not login.hostname or login.username or login.password
		or login.query or login.fragment):
		raise ValueError("请配置无凭据的HTTPS登录地址")
	return {"webhook_url": webhook_url, "login_url": login_url}


def post_notification(url, payload):
	try:
		response = requests.post(url, json=payload, timeout=5, allow_redirects=False)
	except requests.Timeout:
		return {"status": "failed", "reason": "timeout"}
	except requests.RequestException:
		return {"status": "failed", "reason": "transport_error"}
	if not 200 <= response.status_code < 300:
		return {"status": "failed", "reason": "http_error", "http_status": response.status_code}
	try:
		result = response.json()
	except requests.exceptions.JSONDecodeError:
		return {"status": "failed", "reason": "invalid_response"}
	if not isinstance(result, dict) or type(result.get("errcode")) is not int:
		return {"status": "failed", "reason": "invalid_response"}
	if result["errcode"] != 0:
		return {"status": "failed", "reason": "business_error", "errcode": result["errcode"]}
	return {"status": "accepted"}


def _record_failure(masked_order, state, result):
	frappe.log_error(title="生产工单企业微信提醒失败", message=frappe.as_json({
		"order": masked_order, "state": state, **result,
	}))


def send_notification(masked_order, state):
	try:
		config = read_config(frappe.conf.xgd_wecom_robot_secret_file, frappe.conf.xgd_wecom_login_url)
	except (OSError, ValueError):
		result = {"status": "failed", "reason": "configuration_error"}
	else:
		result = post_notification(config["webhook_url"], notification_payload(masked_order, state, config["login_url"]))
	if result["status"] == "failed":
		_record_failure(masked_order, state, result)
	return result


def _enqueue_notification(masked_order, state):
	try:
		frappe.enqueue("erpnext.manufacturing.approval_notification.send_notification",
			queue="default", masked_order=masked_order, state=state)
	except (RedisError, frappe.ValidationError):
		# The approval transaction has committed; a new DB log could be rolled back at request cleanup.
		frappe.logger("production_approval_notifications").error(frappe.as_json({
			"order": masked_order, "state": state, "status": "failed", "reason": "queue_error",
		}))


def schedule_notification(work_order, state):
	if frappe.conf.get("xgd_wecom_robot_secret_file") and state in ("待审核", "待签批"):
		# Only the committed action enters the queue; no document or credential is serialized.
		frappe.db.after_commit.add(partial(_enqueue_notification, mask_order(work_order), state))
