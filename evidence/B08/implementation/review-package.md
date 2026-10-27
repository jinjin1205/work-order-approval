> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B08 本次一次性审查

基线公开提交 c064b6caf33b3cf8b440e02cf6f0926d06455b1f，产品HEAD为固定上游4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e，维护分支codex/xgd-maintenance的累积未提交修改属于正常交付结构，不要重置。上轮B14源码在.publication/work-order-approval/source/erpnext；本次差异只看b08-only.patch，必要时看.development/repos/erpnext下对应原生调用。

规格：AGENTS.md；docs/任务卡/02-生产与物料闭环.md 的B08、B09；evidence/R07/report-concurrency.md、time-config-binding.md、permissions.md。记录及本轮决议：run-record.md。用户补充：起止时间不变的更正沿用原时段依据。

已执行：9项确认测试通过，随后普通操作工计划卡改量新增反例修补后2项通过；实际HTTP同键并发曾Unique/旧快照404失败已修（两个并发请求200且同一结果）；HTTP零时长同内容两请求曾误判重叠，已修且续测成功。超量HTTP失败零残留，父单/子行/原卡HTTP403。核心中文PC三笔普通岗位已实际完成1+1+(6良2不良)，查看原笔快照成功。完整G1/G2/G3继续保留；完整体验10秒未判定通过，自动化输入诊断耗时不当成人工计时；正常默认量样例待收尾。

请一次性只读审查本轮局部产品实现，发现具体Critical/Important给文件行号、触发条件与实际影响。不要重跑已完成项，不启动Docker，不重做五产品选型，不开子代理，不编辑文件。尤其检查服务端权限/来源、原记录旁路、正常/失败/恢复、数量/已批准状态、并发当前读和原生派生链是否有真实业务缺陷。不能因为G3整门槛保留而忽略本包具体漏洞。列出Declined to judge和理由。实现者会做一次必要修补而不是开循环审查。

文件：
- erpnext/manufacturing/doctype/job_card/job_card.js
- erpnext/manufacturing/doctype/job_card/job_card.json
- erpnext/manufacturing/doctype/job_card/job_card.py
- erpnext/manufacturing/doctype/job_card/test_job_card.py
- erpnext/manufacturing/doctype/job_card_time_log/job_card_time_log.py
- erpnext/manufacturing/doctype/work_order/work_order.js
- erpnext/manufacturing/doctype/work_order/work_order.py
- erpnext/manufacturing/doctype/work_order_operation/work_order_operation.json
