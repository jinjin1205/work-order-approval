// Controlled frontend fault injection. This is not a browser or HTTP transaction test.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('.development/repos/erpnext/erpnext/manufacturing/doctype/work_order/work_order.js','utf8');
const fn=source.slice(source.indexOf('\tasync function submit(args) {'),source.indexOf('\n\tdialog.set_secondary_action',source.indexOf('\tasync function submit(args) {')));
let messages=[],html=[];
const context={api:'test.',storage_key:'request',fingerprint:'known',escape:String,
 localStorage:{removeItem(){}},dialog:{get_primary_btn:()=>({prop(){}}),hide(){},fields_dict:{time_preview:{$wrapper:{html:v=>html.push(v)}}}},
 frappe:{call:async()=>({message:{name:'CONFIRMED'}}),msgprint:m=>messages.push(m)},
 frm:{reload_doc:async()=>{throw {status:403,responseJSON:{exc_type:'PermissionError'}};}}};
await vm.runInNewContext(`(async()=>{${fn};await submit({});})()`,context);
assert.ok(messages.some(m=>JSON.stringify(m).includes('CONFIRMED')),'Saved record identity must remain visible');
assert.ok(!html.some(m=>m.includes('未保存')),'A reload failure must never claim the completed confirmation was not saved');
console.log('PASS: confirmed record retained when subsequent reload fails; controlled frontend fault only');
