# Tasks

## Authoritative task source

当前唯一任务/验收入口为[原B08不同请求并发余量子节](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-不同请求并发余量续接)，技术范围/真实API/实际脚本和命令见[原R07本轮绑定](../../../evidence/R07/report-concurrency.md#2026-10-28-不同请求并发余量续接绑定)。I03/I04两行各一次有限HTTP通过，仅在原卡跟踪；[I03](../../../evidence/B08/distinct-concurrency-20261028/http-i03.json)/[I04](../../../evidence/B08/distinct-concurrency-20261028/http-i04.json)共4次并发确认3成功/1预期冲突，未重放，setup两笔基线另计。[20表保留](../../../evidence/B08/distinct-concurrency-20261028/http-retention-final.json)已核，产品源码完全未改。本包验证提交`698a780`已推送并fresh clone回读，362文件/361内容哈希、25份源码一致，见[回执](../../../evidence/发布/2026-10-28-698a780-remote.json)；仅此有限包收口；不为CLI复制清单，不提前关闭整卡。

上一包原记录旁路的5方法分批、13个不同HTTP写入及保留/公开回读已限定收口，沿[历史记录](../../../evidence/B08/history-paths-20261028/run-record.md)和[回执](../../../evidence/发布/2026-10-28-00cfbfc-remote.json)保留，不把旧同键并发、顺序异键或历史旁路重计为本包验证。

单价/效率包已限定收口，证据沿[metrics记录](../../../evidence/B08/metrics-20261028/run-record.md)；10方法分批、中文PC/独立HTTP、源码/数据保留及公开回读不重开，不把旧结果算作本次执行。当前submitted直接方法及cancelled原Job Card直接delete已有证据，按原卡明确排除重复验证。

[原B08上一包执行卡](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-下一包详细执行卡沿原编号尚未运行)的B08-02/05/07权限、规则停启和PC计量作为历史保留，未变化不重跑；证据见[上一包记录](../../../evidence/B08/followup-20261028/run-record.md)。前置和边界沿[design.md](design.md)的R07引用。

## Tracking boundary

这是引用模式。OpenSpec 默认 apply 只解析本文件的复选框，不能直接跟踪链接目标中的任务；本文件有意不复制清单。CLI 的规划完成、无任务或 apply 阻塞状态均不代表原卡完成，也不改变用户已授权的原卡执行顺序。实际实现、测试和业务验收以原卡与证据为准。

## Workflow follow-up

- 原卡I03/I04两行的有限HTTP及保留已有证据，当前仅待公开保存/远端回读；不重放已通过项，最终也只关闭对应子项。B08/B09整卡仍部分完成，本change保持活动引用记录、不归档；现场、手机、完整G1/G2/G3和Z01边界保留，不恢复后台周期。
