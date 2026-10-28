# Proposal

## Why

2026-10-28再次续接：用户要求继续原B08剩余已绑定项。当前仅推进B08-06/B09原记录旁路，唯一任务入口为[原卡当前有限矩阵](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-原记录旁路续接)，方案/文件/真实入口和实际测试沿[原R07续接绑定](../../../evidence/R07/report-concurrency.md#2026-10-28-原记录旁路续接绑定)。本包5个新增方法已分批通过；限定HTTP与专用站最终保留已核；本包已随产品提交`00cfbfc`推送并fresh clone回读，344文件/343内容哈希、25份源码一致，见[回执](../../../evidence/发布/2026-10-28-00cfbfc-remote.json)；仅此有限包收口。完整G2保留不阻止已绑定子项推进；无新增产品API/角色权限，HTTP使用独立测试角色和用户，旧共享岗位未改。

单价/效率包已按C16完成限定实施、受控/真实PC/HTTP和公开回读，证据沿[原记录](../../../evidence/B08/metrics-20261028/run-record.md)；更早权限组合、规则停用/重启和PC计量也保留其版本边界，不重开未变化项。本change继续引用同一原卡，需求、方案和任务只维护一份。

## What Changes

- 当前只补工序子行历史改挂/删除、取消态时间子行delete/reparent、对应Resource/client/同步批量路径和无事实草稿正例；两处真实失败后仅补原工序控制器历史引用保护，必要样例和阶段状态只在原卡维护。
- 本 change 使用引用模式：原卡、[R07 事实/并发绑定](../../../evidence/R07/report-concurrency.md)、[权限绑定](../../../evidence/R07/permissions.md)、[时段绑定](../../../evidence/R07/time-config-binding.md)继续作为权威依据，不复制另一套验收清单。
- 已验且实现/输入/依赖未变化的三笔正例、防重和依赖子项直接引用历史证据；不扩展工资结算、AI、库存逆向或客户部署。

## Capabilities

### New Capabilities

无。现有需求未增加，`skip_specs: true` 用于此次已有契约的验证续接和流程接入，不新造规格凑齐工具状态。

### Modified Capabilities

不扩展原卡需求。C16补齐既有单价/效率要求的来源选择，技术绑定由R07维护；如需改变需求或白名单范围，先停止受影响方案并记录，不通过本change默许扩张。

## Impact

本包实际仅改原Work Order Operation控制器及原测试；`TestProductionReportHistoryPaths`复用既有fixture，5方法分批、两次真实失败和fixture错误见[本包记录](../../../evidence/B08/history-paths-20261028/run-record.md)。本轮2文件、累计25源码、三处33运行文件一致及源站11表保留已核；[HTTP汇总](../../../evidence/B08/history-paths-20261028/http-summary.json)核7个不同拒绝写入及6个合法草稿操作，未重放写入；6次业务保护与1次原生取消态417分开记录。[专用站保留](../../../evidence/B08/history-paths-20261028/http-retention-final.json)核旧11业务表/5安全表原行与捕获列未变、库存新增0。本包已随产品提交`00cfbfc`推送并fresh clone回读，344文件/343内容哈希、25份源码一致，见[回执](../../../evidence/发布/2026-10-28-00cfbfc-remote.json)；仅此有限包收口。旧submitted直接保存/取消/删除、cancelled原Job Card直接删除不重跑。B08/B09整卡、人工现场、G1/G2/G3和Z01/CASE-11不随本包关闭；本change保持引用记录，不归档。
