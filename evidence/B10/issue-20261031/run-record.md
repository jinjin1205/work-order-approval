> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B10 实际领料：2026-10-31执行记录

入口：原B10卡及R07 `quantity-return.md` 的2026-10-31绑定。只修改已绑定的Work Order草稿生成、Stock Entry领料校验及原测试；不新增字段、账本，不重跑未变的B05～B09/U01。

基线：公共main `d5ea916c1e542e32eae6a8f042c72fa7e2c65bb6`，本轮fetch与远端一致；ERPNext15.124.1上游 `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，Frappe15.124.0。沿用B09的41文件运行清单；启动原Docker隔离DB/Redis/check/UI服务后，修改前哈希一致。

Ruling: 沿用原任务卡和同一OpenSpec变更，不创建第二份清单。OpenSpec apply因引用模式0任务显示blocked，不能写成已完成/已归档。公开推送沿用用户授权；本轮无客户数据。

## 实际执行

所有单元命令：`docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py erpnext.stock.doctype.stock_entry.test_stock_entry.TestProductionMaterialIssue.<method>`，多方法按名称顺序追加。每批结束rollback，并核对23表旧数据哈希。原始日志只在私有目录；以下不含凭据和样例标识。

|批次|实际结果|结论|
|---|---|---|
|p0|1项通过，9.834s，旧23表不变|原生草稿不记账；普通仓管领10、取消恢复；移动平均3|
|entry-red|4项失败，31.630s，旧23表不变|缺父工单read、缺库存create、fg非零超量、换已授权目标仓均未拒绝；真实产品缺陷|
|entry-green|5项通过，40.831s，旧23表不变|补生成权限/数量/目标仓后上述4项及正例通过|
|material-red|4项中2失败2通过，32.886s，旧23表不变|倒冲配置跳过限额、额外物料被接受；拆行累计与成本/重复提交通过|

执行限制：entry-green与material-red曾在同一测试站点重叠；两批均结束、旧23表均保持、无运行错误。后续改为串行；不以该重叠证明并发业务正确。早期每批中间源码哈希未单独保存，不杜撰；最终版本另作清单和必要受影响复测。

## 最终实现与限定验收

本轮仅4个既有源码/测试文件：草稿父单read/库存create；项目实际领料统一用量和明细来源校验；父单先锁，锁后同一对象参与额度校验；取消锁保存原父单，禁止一边取消一边篡改原单。原生库存账、单位换算、事务、成本核心未改。无新增字段/DocType，原报工不写。

- material-green-source-red：3项中2通过1失败，24.112秒；前两修复生效，换已授权来源仓未拒绝，随后修复。
- integrity-red：4项中2通过2失败，35.876秒；来源仓/库存不足通过，取消改数量及伪造original_item未拒绝，随后修复。
- final-affected：20项全通过，194.911秒，23表旧数据哈希保持；包含15个本轮方法及5个直接受锁/取消修改影响的原审批、跨任务、停用流程、退料、停止取消用例。不重跑未变化U01或B05～B09。
- 真实独立事务：计划10，两个连接各领6。首轮实际A提交、B死锁回滚；同时观测INNODB_TRX因缺PROCESS权限失败，保留，未加权。新样例改用同数据库用户可见的SHOW FULL PROCESSLIST：A停在原生on_submit前持有父锁，B处于Work Order FOR UPDATE查询且未进入on_submit，释放后A提交6、B因仅剩4拒绝。实际库源14/值42、线边6/值18、工单领6/耗0；拒绝草稿无SLE。此为独立DB事务验收，不称HTTP并发；完整G3仍开放。
- 中文PC：Playwright CLI实际点击工单“生产领料”，数量5，原生库存表单保存、提交、确认、取消、确认；回读草稿20/60和0/0且累计0，提交15/45和5/15且累计5，取消恢复20/60和0/0、累计0。原单docstatus=2保留，4条SLE包含冲销。页面“已取消”及截图/快照哈希保留在acceptance-summary，原件私有。
- UI首次缺Stock Settings读取权限，提示阻挡保存；当时未保存/过账。仅给本轮新仓管角色补原生设置read、刷新再验成功；旧角色不改。HTTP-only服务的socket.io 404保留，不把实时通知写成通过。
- 两容器41文件匹配、22 Python解析通过；最终累计补丁SHA256 `f534ecfb1420246f7b881011d3e5fbcc95953f19b8d6e8fb9c48cdb801463e74`。维护上游提交不变，实际版本由清单/补丁绑定。末次哈希为测试后核对，未伪造早期中间版本。
- 独立审查：只比4文件本轮差集；无可证实Critical/Important，允许公开限定包；未因审查重复业务测试。

## 实际命令与保持

```sh
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py erpnext.stock.doctype.stock_entry.test_stock_entry.TestProductionMaterialIssue erpnext.stock.doctype.stock_entry.test_stock_entry.TestStockExecutionApproval.test_unapproved_submitted_order_stock_denied erpnext.stock.doctype.stock_entry.test_stock_entry.TestStockExecutionApproval.test_mismatched_job_card_cannot_borrow_approved_order erpnext.stock.doctype.stock_entry.test_stock_entry.TestStockExecutionApproval.test_disabled_workflow_stock_submit_denied erpnext.stock.doctype.stock_entry.test_stock_entry.TestStockExecutionApproval.test_approved_material_return_preserved erpnext.manufacturing.doctype.work_order.test_work_order.TestWorkOrderApprovalChanges.test_stopped_order_preserves_stock_cancellation
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b10_issue_fixture.py setup
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b10_issue_race.py race-red run
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b10_issue_race.py race-green run
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b10_issue_fixture.py ui-permission
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b10_issue_fixture.py audit
playwright-cli -s=b10 open http://127.0.0.1:18090/login
```

浏览器其后使用私有登录脚本，按快照引用click/fill及已观察按钮run-code操作；不公开凭据脚本。保存/提交/取消分别audit。最后31表原行无缺失/变化，含Job Card/Time Log/QI/File/权限/库存/成本/工位。只新增独立合成样例，不以新样例哈希覆盖旧失败。原始日志在私有目录，公开7批测试回执、并发摘要、31表计数/保持结果与源码清单。

## 保留边界与下一入口

当前隔离配置实查：backflush=BOM、material_consumption=0、工单skip_transfer=0、transfer_material_against=Work Order、禁负库存。实际领料仅经人工库存提交；本次未触发报工或制造过账；B08/B09既有报工不产生库存事实证据直接复用。B12完工耗料及手动领料组合不在本包称完成。

Stock Entry活动Workflow=0：仅草稿/已提交/已取消，不能把草稿称“待审批”。B07待审批来源提示仍为未接入，客户库存审批配置/待审批汇总保留；不自行增加主管报工审批。完整G3含取消/退料/制造与跨工单竞争、合法替代料正例、手机、客户角色部署和Z01未验。B10整卡仍部分完成，CASE-06整体验收不关闭。

本轮限定包实现/测试/页面/审查完成；公开代码、精确提交CI与新克隆回读在发布后补。下一步沿原B11退料生成与净领料，先消费本包真实已领事实并核R07差集，不重跑本包已验项。
