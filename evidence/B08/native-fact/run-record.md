> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B08 原生逐笔事实最小探针

2026-10-27，按原R07 F-RPT-01/P4先核可运行样例。未修改B08产品代码，未开放预览/确认/快照接口。

环境：xgd-test.localhost，ERPNext15.124.1、Frappe15.124.0；源码对应B14 ui-fixed-runtime.json，本探针使用的JobCard/WorkOrder与上一批B04计算源码一致。无Work Order Workflow，用Administrator只准备/检查原生事实机制，不冒充最小操作工或审批通过。

首次脚本在frappe.init前导入测试工厂导致cache未初始化，native-probe.stderr.log保留；移到连接后运行，未装无关模块。runnable-probe.jsonl实际结果：

| 场景 | 实际结果 | 判断 |
|---|---|---|
| 工单10、三道工序、按工单领料、skip_transfer隔离事实机制 | 三张草稿计划卡，每张for_quantity=10 | fixture可运行，无实际库存过账 |
| 原计划卡保留，另建第一笔数量1的Job Card | ValidationError，卡制造数量超过工单工序数量 | 原生不能直接叠加逐笔卡；后两笔未执行，不伪造三笔通过 |
| 在原计划卡填写良1并保存草稿 | total_completed_qty=1、process_loss_qty=9 | 未报差额被当损耗，不满足显式不良0 |
| 最小岗位父工单回写、冲销保留、确认快照 | 未进入 | G2/G3保留；不能用管理员探针替代 |

脚本`.development/checks/b08_native_fact_probe.py`全程finally回滚；B14最终旧11业务表核对覆盖本次回滚。源输入定义可公开，运行单号/原始错误响应只留本地。

**下一包固定入口：**只沿原report-concurrency.md第3/3.1节已绑定白名单，先把本项目任务保留为Work Order Operation，限定处理本项目自动计划卡冲突和显式良/不良；不删除旧计划卡、不放宽全局超产率、不把9当不良。让新隔离样例完成1＋1＋(6良2不良)，并用无Work Order write/库存写的最小岗位验证仅派生回写。通过后才接已有B04计算、B14内部读取和B08确认/历史快照。若触及全局Frappe或需宽权限，止于对应真实失败并记录，不扩大底座改造。

结束条件：三条独立事实、本道良8/不良2、其余任务未完成、入库0、计划/路线不变；最小角色正常派生和越权拒绝、原记录更正保留成立，才进入P5～P8。当前仅完成原生机制反例，F-RPT-01尚未通过。
