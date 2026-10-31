"""Drive the observed native B19 menu controls; no direct approval API calls."""
import json
import subprocess
import sys
from pathlib import Path

P=Path('.development/private/b19-remaining-20261031')


def run(actor,label,code):
    (P/(label+'.js')).write_text(code)
    with (P/(label+'.log')).open('w')as stream:
        result=subprocess.run(['playwright-cli','-s=b19-remaining-'+actor,'run-code',code],stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:raise SystemExit(label+' failed; inspect private log')
    print(label,'CLI exit',result.returncode)


def action(actor,label,name,reason,field,value):
    code='''async(page)=>{
      await page.locator('.page-head button').filter({hasText:'操作'}).click();
      await page.getByRole('link',{name:ACTION,exact:true}).click();
      const dialog=page.getByRole('dialog');
      if(REASON!==null){await dialog.getByRole('textbox').fill(REASON);await dialog.getByRole('button',{name:'确认',exact:true}).click();}
      else{await dialog.getByRole('button',{name:'是',exact:true}).click();}
      await page.waitForFunction(([field,value])=>cur_frm.doc[field]===value,[FIELD,VALUE],{timeout:8000});
      return await page.evaluate(()=>({name:cur_frm.doc.name,state:cur_frm.doc.workflow_state,status:cur_frm.doc.status,reason:cur_frm.doc.approval_note,viewport:{width:innerWidth,height:innerHeight}}));
    }'''.replace('ACTION',json.dumps(name)).replace('REASON',json.dumps(reason)).replace('FIELD',json.dumps(field)).replace('VALUE',json.dumps(value))
    run(actor,label,code)


if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='cancel-main':
        run('director','cancel-main-open',"async(page)=>{await page.reload();await page.waitForFunction(()=>window.cur_frm?.doc?.workflow_state==='已批准');await page.setViewportSize({width:390,height:844});return {ready:true};}")
        action('director','cancel-main','取消修订','B19页面验收：无执行事实取消并修订','workflow_state','已取消')
    elif mode=='terminate-amended':
        action('planner','terminate-amended','终止','B19页面验收：修订草稿需求终止','workflow_state','终止')
    elif mode=='stop':
        name=json.loads((P/'stop-case.json').read_text())['order']
        code="async(page)=>{await page.goto('http://xgd-b08-http.localhost:18090/app/work-order/"+name+"');await page.waitForFunction(name=>window.cur_frm?.doc?.name===name,"+json.dumps(name)+");await page.setViewportSize({width:390,height:844});return {ready:true};}"
        run('director','stop-case-open',code)
        action('director','stop-case','停止执行','B19页面验收：已有领料后停止新增执行','status','Stopped')
    else:
        raise SystemExit('Unknown recorded UI stage')
