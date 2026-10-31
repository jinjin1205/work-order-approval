// Execute production form handlers with controlled UI dependencies; real browser acceptance is separate.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const calls=[];const handlers={};let active;const selected=process.argv[2];
const payload={work_order:'WO-B13',operation_id:'OP-B13',request_id:'preserved-key',good_quantity:'2',bad_quantity:'0',from_time:'2026-10-31 08:00:00',to_time:'2026-10-31 09:00:00',shutdown_seconds:0,overtime_seconds:0,context_fingerprint:'original-fingerprint'};
const stored=new Map([['production-report:user:WO-B13',JSON.stringify(payload)]]);
class Dialog {
 constructor(options){this.options=options;this.values={};this.fields_dict={};for(const f of options.fields){this.values[f.fieldname]=f.default;this.fields_dict[f.fieldname]={$wrapper:{html(){},append(){}}};}active=this;}
 set_value(k,v){this.values[k]=v;return Promise.resolve();}
 async set_values(values){Object.assign(this.values,values);}
 get_value(k){return this.values[k];}
 set_df_property(){} set_secondary_action(fn){this.secondary=fn;} set_secondary_action_label(){} show(){} hide(){}
 get_primary_btn(){return {prop(){}};}
}
const context={erpnext:{work_order:{}},__:s=>s,flt:Number,crypto:{randomUUID:()=>{throw Error('Recovery must not allocate a new key');}},localStorage:{getItem:k=>stored.get(k),removeItem:k=>stored.delete(k)},
 frappe:{tour:{},provide(){},ui:{form:{on:(dt,h)=>handlers[dt]=h},Dialog},model:{can_create:()=>true},session:{user:'user'},datetime:{now_datetime:()=> '2026-10-31 12:00:00'},utils:{escape_html:String},msgprint(){},call:async method=>{calls.push(method);assert.ok(method.endsWith('get_production_report_tasks'));return {message:{tasks:selected==='restore-empty'?[]:[{name:'OP-B13',idx:1,operation:'加工',unfinished:10,plan:10,good:0,bad:0,status:'Pending'}],reports:[],unit:'Nos'}};}}};
vm.runInNewContext(fs.readFileSync('.development/repos/erpnext/erpnext/manufacturing/doctype/work_order/work_order.js','utf8'),context);
if(selected==='return'){
 const buttons=[];const frm={doc:{docstatus:1,status:'In Process',approval_requested_by:'owner',workflow_state:'已批准',required_items:[{transferred_qty:10,returned_qty:2,consumed_qty:3}]},add_custom_button:label=>buttons.push(label)};
 handlers['Work Order'].add_custom_button_to_return_components(frm);
 assert.equal(buttons.length,1,'In-process authorized order with available material needs its native return action');
 buttons.length=0;frm.doc.required_items[0].consumed_qty=8;handlers['Work Order'].add_custom_button_to_return_components(frm);assert.equal(buttons.length,0);
}else if(['restore','restore-empty'].includes(selected)){
 await context.erpnext.work_order.open_production_report({doc:{name:'WO-B13'}});
 for(const key of ['good_quantity','bad_quantity','from_time','to_time'])assert.equal(active.values[key],payload[key],key+' must retain the uncertain original input');
 for(const field of active.options.fields.filter(f=>f.onchange)) await field.onchange();
 assert.equal(calls.length,1,'Pending form callbacks must not request a new preview');
 for(const field of active.options.fields.filter(f=>Object.hasOwn(payload,f.fieldname)))assert.equal(field.read_only,1);
 assert.equal(JSON.parse(stored.get('production-report:user:WO-B13')).request_id,'preserved-key');
}else throw Error('Choose return or restore');
console.log('PASS controlled UI behavior: '+selected+'; not real browser/HTTP acceptance');
