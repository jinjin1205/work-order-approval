# Tasks

## Authoritative task source

当前唯一任务/验收入口为[原B08原记录旁路子节](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-原记录旁路续接)，技术范围/实际方法/原生HTTP入口见[原R07续接绑定](../../../evidence/R07/report-concurrency.md#2026-10-28-原记录旁路续接绑定)。本包4组有限矩阵仅在原卡跟踪；5个新增受控方法已分批通过，真实失败与fixture ERROR保留，详见[本包记录](../../../evidence/B08/history-paths-20261028/run-record.md)。[限定HTTP](../../../evidence/B08/history-paths-20261028/http-summary.json)核7个不同拒绝写入（6业务历史保护、1原生取消态417）及6个合法草稿操作，无重复写入；[专用站最终保留](../../../evidence/B08/history-paths-20261028/http-retention-final.json)核旧11业务表/5安全表原行与捕获列未变、库存新增0。本包已随产品提交`00cfbfc`推送并fresh clone回读，344文件/343内容哈希、25份源码一致，见[回执](../../../evidence/发布/2026-10-28-00cfbfc-remote.json)；仅此有限包收口；不为CLI复制清单，不预先勾选。HTTP的独立测试角色/用户不属于产品或旧共享岗位授权变更。

单价/效率包已限定收口，证据沿[metrics记录](../../../evidence/B08/metrics-20261028/run-record.md)；10方法分批、中文PC/独立HTTP、源码/数据保留及公开回读不重开，不把旧结果算作本次执行。当前submitted直接方法及cancelled原Job Card直接delete已有证据，按原卡明确排除重复验证。

[原B08上一包执行卡](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-下一包详细执行卡沿原编号尚未运行)的B08-02/05/07权限、规则停启和PC计量作为历史保留，未变化不重跑；证据见[上一包记录](../../../evidence/B08/followup-20261028/run-record.md)。前置和边界沿[design.md](design.md)的R07引用。

## Tracking boundary

这是引用模式。OpenSpec 默认 apply 只解析本文件的复选框，不能直接跟踪链接目标中的任务；本文件有意不复制清单。CLI 的规划完成、无任务或 apply 阻塞状态均不代表原卡完成，也不改变用户已授权的原卡执行顺序。实际实现、测试和业务验收以原卡与证据为准。

## Workflow follow-up

- 本次原记录旁路包只按原卡有限矩阵推进，完成后也仅关闭对应子项；原B08/B09整卡仍部分完成，本change保持活动引用记录、不归档。人工现场未验证、完整G1/G2/G3和Z01/CASE-11边界继续保留。
