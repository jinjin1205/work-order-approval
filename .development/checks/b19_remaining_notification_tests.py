"""WeCom adapter checks use real local HTTP, native callbacks and isolated business fixtures."""
import importlib
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import frappe
from b08_distinct_concurrency_fixture import capture_tables, compare_tables, preserved
from b10_issue_fixture import TABLES

MODULE = 'erpnext.manufacturing.approval_notification'


class TestWeComNotification(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), 'B19 single-channel adapter is missing')
        self.n = importlib.import_module(MODULE)

    def start_server(self, status=200, body=b'{"errcode":0,"errmsg":"ok"}', delay=0):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(inner):
                received.append(json.loads(inner.rfile.read(int(inner.headers['Content-Length']))))
                time.sleep(delay)
                inner.send_response(status)
                inner.end_headers()
                try:
                    inner.wfile.write(body)
                except BrokenPipeError:
                    pass  # The timeout case closes its client before this fixture replies.
            def log_message(*args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(worker.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return 'http://127.0.0.1:'+str(server.server_port)+'/send?key=SYNTHETIC-SECRET', received

    def test_real_http_success_means_accepted_and_payload_is_minimal(self):
        url, received = self.start_server()
        masked = self.n.mask_order('Customer-order-with-private-name')
        payload = self.n.notification_payload(masked, '待审核', 'https://example.invalid/login')
        self.assertEqual(self.n.post_notification(url, payload), {'status':'accepted'})
        self.assertEqual(received, [payload])
        content = payload['text']['content']
        self.assertNotIn('Customer-order-with-private-name', content)
        self.assertRegex(masked, r'^WO-[0-9A-F]{12}$')
        self.assertEqual(set(payload), {'msgtype','text'})
        self.assertEqual(set(payload['text']), {'content'})
        self.assertIn('https://example.invalid/login', content)

    def test_business_failure_http_failure_invalid_json_and_timeout_are_explicit(self):
        for status, body, reason in [(200,b'{"errcode":93000,"errmsg":"SYNTHETIC-SECRET"}','business_error'),
                (503,b'SYNTHETIC-SECRET','http_error'), (200,b'SYNTHETIC-SECRET','invalid_response'),
                (200,b'{"errcode":false}','invalid_response')]:
            with self.subTest(reason=reason, body=body):
                url, received = self.start_server(status, body)
                result = self.n.post_notification(url, {'msgtype':'text','text':{'content':'合成提醒'}})
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['reason'], reason)
                self.assertNotIn('SYNTHETIC-SECRET', json.dumps(result))
                self.assertEqual(len(received), 1)
        url, received = self.start_server(delay=5.3)
        self.assertEqual(self.n.post_notification(url, {'msgtype':'text','text':{'content':'超时样例'}}),
                         {'status':'failed','reason':'timeout'})
        self.assertEqual(len(received), 1)

    def test_configuration_is_private_single_group_and_fixed_wecom_host(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'local.env'
            webhook = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=SYNTHETIC-SECRET'
            path.write_text('B18_ASSEMBLY_APPROVAL_WEBHOOK='+webhook+'\n'); path.chmod(0o600)
            self.assertEqual(self.n.read_config(str(path), 'https://example.invalid/login'),
                             dict(webhook_url=webhook, login_url='https://example.invalid/login'))
            path.chmod(0o644)
            with self.assertRaises(ValueError): self.n.read_config(str(path), 'https://example.invalid/login')
            path.chmod(0o600)
            path.write_text('B18_ASSEMBLY_APPROVAL_WEBHOOK=https://example.invalid/send?key=secret\n')
            with self.assertRaises(ValueError): self.n.read_config(str(path), 'https://example.invalid/login')
            path.write_text('B18_ASSEMBLY_APPROVAL_WEBHOOK='+webhook+'\n')
            with self.assertRaises(ValueError): self.n.read_config(str(path), 'http://example.invalid/login')
            for secret_file, login in [(None, 'https://example.invalid/login'), (str(path), 123)]:
                with self.assertRaises(ValueError): self.n.read_config(secret_file, login)

    def test_no_configuration_or_non_pending_state_adds_no_callback(self):
        frappe.db.after_commit.reset()
        with patch.dict(frappe.conf, {'xgd_wecom_robot_secret_file':None}):
            self.n.schedule_notification('synthetic-order','待审核')
        self.assertFalse(frappe.db.after_commit._functions)
        with patch.dict(frappe.conf, {'xgd_wecom_robot_secret_file':'/not-read-by-scheduler'}):
            self.n.schedule_notification('synthetic-order','已批准')
        self.assertFalse(frappe.db.after_commit._functions)

    def test_native_commit_enqueues_only_masked_arguments_and_rollback_discards(self):
        frappe.db.after_commit.reset()
        from frappe.utils.background_jobs import get_queue
        queue = get_queue('default')
        before = set(queue.job_ids)
        self.addCleanup(self.cleanup_jobs, queue, before)
        with patch.dict(frappe.conf, {'xgd_wecom_robot_secret_file':'/not-read-by-scheduler'}):
            self.n.schedule_notification('SYNTHETIC-RAW-ORDER','待审核')
            frappe.db.rollback()
            self.assertEqual(set(queue.job_ids), before)
            self.n.schedule_notification('SYNTHETIC-RAW-ORDER','待签批')
            frappe.db.commit()
        added = set(queue.job_ids)-before
        self.assertEqual(len(added), 1)
        job = queue.fetch_job(added.pop())
        kwargs = job.kwargs['kwargs']
        self.assertEqual(set(kwargs), {'masked_order','state'})
        self.assertEqual(kwargs, dict(masked_order=self.n.mask_order('SYNTHETIC-RAW-ORDER'), state='待签批'))
        self.assertNotIn('SYNTHETIC-RAW-ORDER', str(job.kwargs))
        self.assertNotIn('SYNTHETIC-SECRET', str(job.kwargs))

    def cleanup_jobs(self, queue, before):
        for name in set(queue.job_ids)-before:
            queue.fetch_job(name).delete()

    def test_configuration_failure_writes_safe_native_error_log(self):
        with patch.dict(frappe.conf, {'xgd_wecom_robot_secret_file':'/absent/SYNTHETIC-SECRET'}):
            result = self.n.send_notification(self.n.mask_order('private-order'), '待审核')
        self.assertEqual(result, {'status':'failed','reason':'configuration_error'})
        error = frappe.get_all('Error Log', filters={'method':'生产工单企业微信提醒失败'},
                               fields=['error'], order_by='creation desc', limit=1)[0].error
        self.assertIn('configuration_error', error)
        self.assertNotIn('SYNTHETIC-SECRET', error)
        self.assertNotIn('private-order', error)
        frappe.db.rollback()

    def test_real_approval_only_registers_committed_pending_actions(self):
        from erpnext.manufacturing.doctype.work_order.test_work_order import TestWorkOrderApproval
        fixture = TestWorkOrderApproval()
        fixture.setUp()
        self.addCleanup(fixture.clean_fixture)
        frappe.db.after_commit.reset()
        with patch.dict(frappe.conf, {'xgd_wecom_robot_secret_file':'/must-not-be-opened-before-commit'}):
            fixture.act('operator', '送审')
            fixture.act('reviewer', '审核通过')
            fixture.act('director', '签批通过')
        self.assertEqual(fixture.order.workflow_state, '已批准')
        self.assertEqual(fixture.order.docstatus, 1)
        callbacks = [callback for callback in frappe.db.after_commit._functions
                     if getattr(callback, 'func', None) == self.n._enqueue_notification]
        self.assertEqual(len(callbacks), 2)
        self.assertEqual([callback.args[1] for callback in callbacks], ['待审核','待签批'])
        frappe.db.rollback()
        self.assertFalse([callback for callback in frappe.db.after_commit._functions
                          if getattr(callback, 'func', None) == self.n._enqueue_notification])

    def test_queue_failure_after_commit_keeps_safe_persistent_log(self):
        from redis.exceptions import ConnectionError
        logger = frappe.logger('production_approval_notifications')
        with patch.dict(frappe.conf, {'xgd_wecom_robot_secret_file':'/not-read-by-scheduler'}):
            self.n.schedule_notification('SYNTHETIC-RAW-ORDER', '待审核')
            with patch('frappe.enqueue', side_effect=ConnectionError('SYNTHETIC-SECRET')):
                frappe.db.commit()
        frappe.db.rollback()
        for handler in logger.handlers:
            handler.flush()
        persisted = '\n'.join(Path(handler.baseFilename).read_text() for handler in logger.handlers
                              if hasattr(handler, 'baseFilename'))
        self.assertIn('queue_error', persisted)
        self.assertNotIn('SYNTHETIC-SECRET', persisted)
        self.assertNotIn('SYNTHETIC-RAW-ORDER', persisted)


if __name__ == '__main__':
    os.chdir('sites'); frappe.init(site='xgd-test.localhost'); frappe.connect()
    try:
        assert frappe.conf.allow_tests
        frappe.set_user('Administrator'); frappe.flags.in_test=True
        before = capture_tables(TABLES+['Workflow','Workflow Document State','Workflow Transition','Custom Field'])
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(
            sys.argv[1:] or ['__main__.TestWeComNotification']))
        frappe.db.rollback(); retention = compare_tables(before)
        assert preserved(retention), retention
        print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                              old_tables_unchanged=len(retention))))
    finally:
        frappe.db.rollback(); frappe.destroy()
    sys.exit(0 if result.wasSuccessful() else 1)
