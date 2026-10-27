// UI callback boundary tests only; no HTTP, database, or business-approval assertions.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source = fs.readFileSync(process.argv[2], 'utf8');
const start = source.indexOf('show_production_approval_actions: function (frm) {');
const end = source.indexOf('\n\tset_custom_buttons:', start);
assert(start > 0 && end > start);
const functionSource = source.slice(start, end).replace('show_production_approval_actions: ', '').trim().replace(/,$/, '');
let count = 0;
for (const mode of ['normal', 'dirty-response', 'other-order-response', 'new-version-response', 'dirty-confirm', 'new-version-confirm']) {
  const menu = []; const requests = []; const messages = [];
  let resolveTransitions, confirm;
  const frm = {doc: {name: 'SYNTHETIC-ORDER', modified: 'viewed-v1', approval_requested_by: 'operator', docstatus: 0},
    is_dirty() { return !!this.doc.__unsaved; }, reload_doc() {},
    page: {clear_actions_menu() {menu.length = 0;}, add_action_item(action, callback) {menu.push({action, callback});}},
    states: {setup_btn() {}}};
  const frappe = {workflow: {get_transitions: () => new Promise(resolve => {resolveTransitions = resolve;})},
    session: {user: 'operator'}, user_roles: ['生产工单发起'],
    confirm: (_text, callback) => {confirm = callback;}, msgprint: message => messages.push(message),
    call: request => requests.push(request)};
  const show = vm.runInNewContext('(' + functionSource + ')', {frappe});
  show(frm);
  if (mode === 'dirty-response') {frm.doc.__unsaved = 1; frm.page.clear_actions_menu();}
  if (mode === 'other-order-response') frm.doc.name = 'OTHER-ORDER';
  if (mode === 'new-version-response') frm.doc.modified = 'new-v2';
  resolveTransitions([{action: '送审', allowed: '生产工单发起'}]);
  await Promise.resolve();
  if (mode.endsWith('response')) {assert.equal(menu.length, 0); assert.equal(requests.length, 0);}
  else {
    assert.equal(menu.length, 1); menu[0].callback();
    if (mode === 'dirty-confirm') frm.doc.__unsaved = 1;
    if (mode === 'new-version-confirm') frm.doc.modified = 'new-v2';
    confirm();
    assert.equal(requests.length, mode === 'normal' ? 1 : 0);
    if (mode === 'normal') {
      assert.equal(requests[0].args.work_order, 'SYNTHETIC-ORDER');
      assert.equal(requests[0].args.expected_modified, 'viewed-v1');
    } else assert.equal(messages.length, 1);
  }
  count++;
}
console.log(JSON.stringify({tests: count, passed: true, scope: 'UI async/view boundaries only; not HTTP or business acceptance'}));
