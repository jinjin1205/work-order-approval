// Executes the maintained UI handlers with controlled Frappe controls and HTTP responses.
// This is a frontend contract test, not real-browser or live-server acceptance.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { randomUUID } from 'node:crypto';
import { test } from 'node:test';

const root = '.development/repos/erpnext/erpnext/manufacturing/doctype/';
const workOrderSource = fs.readFileSync(root + 'work_order/work_order.js', 'utf8');
const jobCardSource = fs.readFileSync(root + 'job_card/job_card.js', 'utf8');
const escape = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[char]);

function metrics({ wage = '20.00', rate = '10', mode = 'hourly', standard = '10', actual = '5.0000', percent = '50.0000' } = {}) {
  return {
    source: { work_order: 'WO-TEST', operation_id: 'OP-ID', operation: '切割<工序>', wage_mode: mode,
      wage_rate: rate, currency: mode ? 'CNY' : null, unit: '件', standard_efficiency: standard,
      calculation_version: 'B08-metrics-v1', currency_precision: 2 },
    result: { estimated_wage: wage, actual_efficiency: actual, efficiency_percent: percent },
  };
}

function response(value, fingerprint = 'current-context') {
  return { message: { context_fingerprint: fingerprint, reported_seconds: 7200, rest_seconds: 0,
    effective_seconds: 7200, rule_message: '未匹配时段规则', metrics: value } };
}

async function openReport() {
  const previews = [], calls = [], messages = [], storage = new Map();
  let dialog;
  class Dialog {
    constructor(config) {
      this.config = config;
      this.values = Object.fromEntries(config.fields.map((field) => [field.fieldname, field.default ?? '']));
      this.fields_dict = Object.fromEntries(config.fields.map((field) => [field.fieldname, {
        df: field, rendered: '', $wrapper: { html: (html) => { this.fields_dict[field.fieldname].rendered = html; } },
      }]));
      dialog = this;
    }
    get_value(name) { return this.values[name]; }
    set_value(name, value) { return this.change(name, value); }
    change(name, value) {
      this.values[name] = value;
      return this.fields_dict[name].df.onchange?.();
    }
    get_primary_btn() { return { prop: () => {} }; }
    set_secondary_action(action) { this.secondary_action = action; }
    set_secondary_action_label() {}
    show() {}
    hide() {}
    html() { return this.fields_dict.time_preview.rendered; }
    confirm() { return this.config.primary_action({ ...this.values }); }
  }
  const context = {
    erpnext: { work_order: {} }, crypto: { randomUUID },
    localStorage: { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) },
    frappe: { session: { user: 'operator@example.invalid' }, utils: { escape_html: escape },
      datetime: { now_datetime: () => '2026-10-28 17:00:00' }, ui: { Dialog },
      msgprint: (message) => messages.push(message),
      call: (method, args) => {
        calls.push({ method, args });
        if (method.endsWith('get_production_report_tasks')) return Promise.resolve({ message: {
          tasks: [{ name: 'OP-ID', operation: '切割', plan: 10, good: 0, bad: 0, unfinished: 10 }], reports: [], unit: '件',
        } });
        if (method.endsWith('preview_production_report_time')) return new Promise((resolve, reject) => previews.push({ args, resolve, reject }));
        if (method.endsWith('confirm_production_report')) return Promise.resolve({ message: { name: 'FACT-1', docstatus: 1 } });
        throw new Error('Unexpected API: ' + method);
      },
    },
  };
  vm.runInNewContext(workOrderSource.slice(workOrderSource.indexOf('erpnext.work_order.open_production_report =')), context);
  await context.erpnext.work_order.open_production_report({ doc: { name: 'WO-TEST' }, reload_doc: async () => {} });
  return { dialog, previews, calls, messages };
}

async function startPreview(ui, value = metrics(), fingerprint) {
  const pending = ui.dialog.change('from_time', '2026-10-28 15:00:00');
  ui.previews.at(-1).resolve(response(value, fingerprint));
  await pending;
}

function openSaved(value) {
  const handlers = {}, messages = [], buttons = {};
  let apiCalls = 0;
  const context = { frappe: { flags: {}, utils: { escape_html: escape },
    ui: { form: { on: (doctype, events) => { handlers[doctype] = events; } } },
    msgprint: (message) => messages.push(message), call: () => { apiCalls++; throw new Error('History must not fetch current pricing'); },
  } };
  vm.runInNewContext(jobCardSource, context);
  const frm = { doc: { report_request_id: 'saved-request', total_completed_qty: 8, process_loss_qty: 2,
    report_time_context: JSON.stringify({ rule: null, result: { effective_seconds: 7200, shutdown_seconds: 0, overtime_seconds: 0,
      timezone: 'Asia/Shanghai' }, calculation_version: 'B04-time-v1', confirmed_at: '2026-10-27 17:00:00' }),
    __onload: { work_order_closed: true, report_metrics: value },
    report_estimated_wage: '999.99', // A decoy: display must use the server's saved-history view.
  }, disable_save() {}, add_custom_button: (label, action) => { buttons[label] = action; }, is_new: () => false };
  handlers['Job Card'].refresh(frm);
  buttons['查看确认依据']();
  return { html: messages.at(-1).message, apiCalls };
}

await test('quantity changes request a new server preview with both quantities', async () => {
  const ui = await openReport();
  await startPreview(ui);
  const oldCount = ui.previews.length;
  const goodChange = ui.dialog.change('good_quantity', '4');
  assert.equal(ui.previews.length, oldCount + 1, 'good quantity change must invalidate and request a preview');
  assert.equal(ui.previews.at(-1).args.good_quantity, '4');
  assert.equal(ui.previews.at(-1).args.bad_quantity, '0');
  ui.previews.at(-1).resolve(response(metrics({ wage: '37.25', mode: 'piece' })));
  await goodChange;
  assert.match(ui.dialog.html(), /37\.25/, 'display the server amount, without computing good × rate in the client');
  const badChange = ui.dialog.change('bad_quantity', '2');
  assert.equal(ui.previews.at(-1).args.bad_quantity, '2');
  ui.previews.at(-1).resolve(response(metrics({ actual: '3.0000' })));
  await badChange;
  assert.match(ui.dialog.html(), /3\.0000/);
});

await test('pending and failed previews clear the old amount and block confirmation', async () => {
  const ui = await openReport();
  await startPreview(ui, metrics({ wage: '37.25' }));
  assert.match(ui.dialog.html(), /37\.25/);
  const pending = ui.dialog.change('to_time', '2026-10-28 18:00:00');
  assert.doesNotMatch(ui.dialog.html(), /37\.25/, 'pending preview must clear the previous amount');
  await ui.dialog.confirm();
  assert.equal(ui.calls.filter((call) => call.method.endsWith('confirm_production_report')).length, 0);
  ui.previews.at(-1).reject({ status: 403 });
  await pending;
  assert.doesNotMatch(ui.dialog.html(), /37\.25/);
  assert.match(ui.dialog.html(), /失败|未完成|重新核对/);
  await ui.dialog.confirm();
  assert.equal(ui.calls.filter((call) => call.method.endsWith('confirm_production_report')).length, 0);
});

await test('late responses cannot overwrite a newer amount or confirmation fingerprint', async () => {
  const ui = await openReport();
  const first = ui.dialog.change('from_time', '2026-10-28 15:00:00');
  const firstRequest = ui.previews.at(-1);
  const second = ui.dialog.change('to_time', '2026-10-28 18:00:00');
  ui.previews.at(-1).resolve(response(metrics({ wage: '52.50' }), 'new-context'));
  await second;
  firstRequest.resolve(response(metrics({ wage: '11.00' }), 'old-context'));
  await first;
  assert.match(ui.dialog.html(), /52\.50/);
  assert.doesNotMatch(ui.dialog.html(), /11\.00/);
  await ui.dialog.confirm();
  assert.equal(ui.calls.find((call) => call.method.endsWith('confirm_production_report')).args.context_fingerprint, 'new-context');
});

await test('zero amounts remain zero and missing sources are explicit', async () => {
  const ui = await openReport();
  await startPreview(ui, metrics({ wage: '0.00', rate: '0', standard: '0', actual: null, percent: null }));
  assert.match(ui.dialog.html(), /0\.00/);
  assert.match(ui.dialog.html(), /CNY/);
  assert.match(ui.dialog.html(), /预计|结算/);
  assert.match(ui.dialog.html(), /—/);
  assert.match(ui.dialog.html(), /WO-TEST/);
  assert.match(ui.dialog.html(), /切割&lt;工序&gt;/);
  assert.doesNotMatch(ui.dialog.html(), /切割<工序>/);
  const pending = ui.dialog.change('to_time', '2026-10-28 18:00:00');
  ui.previews.at(-1).resolve(response(metrics({ wage: null, rate: null, mode: null, standard: null })));
  await pending;
  assert.match(ui.dialog.html(), /未配置/);
  assert.doesNotMatch(ui.dialog.html(), /预计工资：<b>0\.00/);
});

await test('reopened reports display only their server-provided saved metrics', () => {
  const result = openSaved(metrics({ wage: '18.25', rate: '9', standard: '8' }));
  assert.match(result.html, /18\.25/);
  assert.match(result.html, /CNY/);
  assert.match(result.html, /WO-TEST/);
  assert.match(result.html, /切割&lt;工序&gt;/);
  assert.doesNotMatch(result.html, /999\.99/);
  assert.equal(result.apiCalls, 0);
});

await test('legacy history reports missing metrics instead of using current values', () => {
  const result = openSaved(null);
  assert.match(result.html, /历史未记录/);
  assert.doesNotMatch(result.html, /999\.99/);
  assert.equal(result.apiCalls, 0);
});
