# Proposal

## Why

2026-10-28再次续接：当前只补B08-03/04/06与B09已绑定的I05提交丢响应、I06更正中途回滚缺口。唯一任务和两行矩阵见[原卡当前子节](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-提交丢响应与更正回滚续接)，真实入口、允许脚本和证据边界见[原R07本轮绑定](../../../evidence/R07/report-concurrency.md#2026-10-28-提交丢响应与更正回滚续接绑定)。本包两项均首次有限验证通过，实际证据沿[本包记录](../../../evidence/B08/recovery-20261028/run-record.md)，验证提交`83aaf4e`已推送并fresh clone回读，380个跟踪文件/379个内容哈希/25份源码一致，缺失、多余及哈希不一致均0，见[公开回执](../../../evidence/发布/2026-10-28-83aaf4e-remote.json)；仅收口本包两项和保存过程。

I03/I04有限HTTP及20表保留已核，验证提交`698a780`公开回读已完成，沿[上包记录](../../../evidence/B08/distinct-concurrency-20261028/run-record.md)和[回执](../../../evidence/发布/2026-10-28-698a780-remote.json)保留，不重跑未变化项。历史旁路、单价/效率、权限、规则及PC计量也保留各自版本与证据边界。本change继续引用同一原卡，需求、方案和任务只维护一份。

## What Changes

- 本包实际仅新增3个检查脚本及manifest，未改产品或原测试文件，未出现产品失败、修补、build、重启或旧回归；独立审阅补断言在执行前完成，未重跑。做/不做/通过及状态只在原卡维护。
- 本 change 使用引用模式：原卡、[R07事实/并发绑定](../../../evidence/R07/report-concurrency.md)、[权限绑定](../../../evidence/R07/permissions.md)、[时段绑定](../../../evidence/R07/time-config-binding.md)继续作为权威依据，不复制另一套验收清单。
- 已验且实现/输入/依赖未变化的子项引用历史证据；不扩展工资结算、AI、库存逆向或客户部署。

## Capabilities

### New Capabilities

无。现有需求未增加，`skip_specs: true`用于已有契约的验证续接和流程接入，不新造规格凑齐工具状态。

### Modified Capabilities

不扩展原卡需求。C16补齐既有单价/效率要求的来源选择，技术绑定由R07维护；如需改变需求或白名单范围，先停止受影响方案并记录，不通过本change默许扩张。

## Impact

本包沿原确认、结果查询、更正API及原确认fixture，具体断响应/受控回滚机制由R07规定；本包[开工记录](../../../evidence/B08/recovery-20261028/run-record.md)已核维护25份/运行33份源码一致、累计e15fba未变，[I05](../../../evidence/B08/recovery-20261028/http-i05.json)一次确认后真实丢响应并原键GET找回，20表旧行保留；[I06](../../../evidence/B08/recovery-20261028/i06-controlled.json)1方法12.142秒（runner总计12.409324秒）通过、最终20表恢复。I05只证明提交对独立DB连接可见后丢响应，不声称精确COMMIT时刻；I06真实DB受控故障不称HTTP自动回滚；两样例hour_rate=0，非零成本未验证。历史旁路沿[原记录](../../../evidence/B08/history-paths-20261028/run-record.md)及[回执](../../../evidence/发布/2026-10-28-00cfbfc-remote.json)，单价/效率沿[原记录](../../../evidence/B08/metrics-20261028/run-record.md)，不重开。父删除/复制、完整并发/库存逆向、后台队列、页面/现场/手机、导航/图片/自定义字段、Z01与周期不在本包；B08/B09整卡及G1/G2/G3不随本包关闭，本change不归档。
