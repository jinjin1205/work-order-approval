# Design

## Context

单价/效率子项的方案仅维护在[原R07绑定](../../../evidence/R07/time-config-binding.md#2026-10-28-b08-单价与效率续接来源与实施绑定)。用户已确认工单工序填写并随审批冻结，C16区分来源决定和字段/快照/精度技术选择；本change只引用，不另复制方案。既有公式/权限/确认/更正继续复用，`hour_rate`不作工资；接入、中文配置/报工页面及独立HTTP已取得限定证据，源测试站/UI站数据保留已核，公开保存尚待收口，现场、G1/G2/G3、Z01保持原门槛。

动机和范围见[proposal.md](proposal.md)。当前做/不做/通过条件及必要验收由[原卡单价/效率子节](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-单价与效率来源核对)及其R07链接规定；上一包范围保留为历史，不复制方案正文。

## Goals / Non-Goals

**Goals:** 保持原卡为唯一验收与进度来源，用 OpenSpec 聚合其入口和本批证据。

**Non-Goals:** 不新建权限/计算框架、平行清单或独立工作树；不把工具规划状态当业务通过。

## Decisions

- 复用`.development/repos/erpnext`的`codex/xgd-maintenance`工作副本。上一包24个累计改动文件与交付基线`afe5eb8`核对一致，保留于[开工记录](../../../evidence/B08/followup-20261028/run-record.md)；当前新增原子行控制器后累计25份改动源码，构建/测试/网页三处最终清单均33份一致，证据沿本轮R07引用。新工作树不会自动带入累计补丁，故继续既有维护checkout，不用旧24文件结论替代本轮核对。
- 上一包复用`TestProductionReportConfirmation`并在送审前提供scope参数，结果沿[原R07本包绑定](../../../evidence/R07/report-concurrency.md#2026-10-28-b08-续接包命令绑定)。当前同一fixture支持`TestProductionReportMetrics`和独立`b08_metrics_tests.py`，10方法分批及真实Chrome新合成样例已有结果；生产来源仍随审批冻结。用于故障/历史保持的直接数据库变更仅为回滚受控样例，不能当合法编辑入口。真实方法、命令/结果继续只在当前R07及运行记录维护。
- 使用默认 `spec-driven` 与 `skip_specs: true`：本次没有新增或改写需求，故引用已有契约；`tasks.md` 也只引用原卡。接受 CLI 不解析外部复选框的限制，不另建自定义 schema 或重复任务以凑齐状态。

## Risks / Trade-offs

- [CLI 规划文件状态可能被误读为实现完成] → 原卡和本批实际证据权威；不归档未完成包，不用 CLI 状态增加完成数。
- [历史样例已消耗、旧证据有限] → 不重放旧 HTTP 批，不把受控测试/页面/现场或完整 G1/G2/G3 混为一谈；按原卡保留停止和交付边界。
