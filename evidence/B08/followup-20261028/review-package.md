> 公开归档副本（2026-10-28）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# 本包独立审查
基线交付提交afe5eb894be759fd094f56910058bdb84fa2f24f，维护源码HEAD4e0dce9+原累计补丁。不要把维护HEAD全部累计diff当本包。相对基线差异见followup-only.patch，仅job_card.py历史结果查询1处（_report_task改_report_context）和原测试fixture参数/新增TestProductionReportFollowup。
需求：docs/任务卡/02-生产与物料闭环.md 原B08-02/05/07下一包；evidence/R07/permissions.md明确报工写scope与历史read分开。做/不做和裁决见run-record.md。
实证：权限first 6中3错误（1真实历史读取误拒＋2fixture工序顺序）；fixed4项OK、employee/history regression2项OK；DEPT同部门及原生唯一员工在first已通过。本包7权限测试＋1规则测试分批执行，不是一个全量suite。停用首轮已有旧规则干扰，回滚事务中隔离后1项OK。普通角色Playwright正常剩余10/不良0，3.211秒（确认843ms，含截图291ms），仅合成自动化；现场/手机未验。
请重点核历史结果查询移除写scope是否保留本人、当前公司/班组/角色/父单/Job Card读取边界；员工映射/撤权是否产生漏洞；测试是否仍只测真实业务入口；规则隔离是否会永久动旧资料；事实/原卡不被覆盖。未变化的G1/G2/G3、完整B08/B09和Z01保留，不作为本包被测试通过。
只读，不运行测试或改动文件，不派其他代理。给明确Critical/Important/Minor、文件行号、理由与最小建议，并列Declined to judge。
