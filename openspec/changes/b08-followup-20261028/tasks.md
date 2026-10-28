# Tasks

## Authoritative task source

当前唯一任务/验收入口为[原B08提交丢响应与更正回滚子节](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-提交丢响应与更正回滚续接)，技术范围/真实API/检查脚本见[原R07本轮绑定](../../../evidence/R07/report-concurrency.md#2026-10-28-提交丢响应与更正回滚续接绑定)。I05/I06两行仅在原卡跟踪，均首次有限验证通过；[I05](../../../evidence/B08/recovery-20261028/http-i05.json)一次POST丢响应后原键GET恢复、20表旧行保留，[I06](../../../evidence/B08/recovery-20261028/i06-controlled.json)1方法12.142秒（runner总计12.409324秒）、0失败/0错误及最终20表恢复。验证提交`83aaf4e`已推送并fresh clone回读，380个跟踪文件/379个内容哈希/25份源码一致，缺失、多余及哈希不一致均0，见[公开回执](../../../evidence/发布/2026-10-28-83aaf4e-remote.json)；仅收口本包两项和保存过程，不为CLI复制清单。

上一包I03/I04各一次有限HTTP通过，[原记录](../../../evidence/B08/distinct-concurrency-20261028/run-record.md)、[20表保留](../../../evidence/B08/distinct-concurrency-20261028/http-retention-final.json)及验证提交`698a780`的[公开回执](../../../evidence/发布/2026-10-28-698a780-remote.json)保留；4次并发确认3成功/1预期冲突、产品源码未改，不重放或计为本包执行。

原记录旁路的5方法分批、13个不同HTTP写入及保留/公开回读已限定收口，沿[历史记录](../../../evidence/B08/history-paths-20261028/run-record.md)和[回执](../../../evidence/发布/2026-10-28-00cfbfc-remote.json)保留。单价/效率沿[metrics记录](../../../evidence/B08/metrics-20261028/run-record.md)保留，10方法分批、中文PC/独立HTTP、源码/数据保留及公开回读不重开。旧成功响应后结果查询和普通确认派生失败不能分别冒充本包I05/I06。

[原B08早期执行卡](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-下一包详细执行卡沿原编号尚未运行)的B08-02/05/07权限、规则停启和PC计量作为历史保留，未变化不重跑；证据见[早期记录](../../../evidence/B08/followup-20261028/run-record.md)。前置和边界沿[design.md](design.md)的R07引用。

## Tracking boundary

这是引用模式。OpenSpec默认apply只解析本文件的复选框，不能直接跟踪链接目标中的任务；本文件有意不复制清单。CLI的规划完成、无任务或apply阻塞状态均不代表原卡完成，也不改变用户已授权的原卡执行顺序。实际实现、测试和业务验收以原卡与证据为准。

## Workflow follow-up

- 原卡I05/I06首次有限验证、旧数据保留和执行前独立审阅已有证据，白名单公开保存及远端回读已完成；仅关闭对应有限子项和保存过程，不重放已通过且未变化的验证。最终文档SHA与CI仅在最终回复，不循环回填。B08/B09整卡仍部分完成，本change保持活动引用记录、不归档；现场、手机、完整G1/G2/G3和Z01边界保留，不恢复后台周期。
