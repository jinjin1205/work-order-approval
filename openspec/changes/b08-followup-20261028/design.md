# Design

## Context

动机和范围见 [proposal.md](proposal.md)。技术方案继续由[原卡下一包](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-下一包详细执行卡沿原编号尚未运行)及其 R07 链接规定；这里仅记录本次接入选择，不复制方案正文。

## Goals / Non-Goals

**Goals:** 保持原卡为唯一验收与进度来源，用 OpenSpec 聚合其入口和本批证据。

**Non-Goals:** 不新建权限/计算框架、平行清单或独立工作树；不把工具规划状态当业务通过。

## Decisions

- 复用 `.development/repos/erpnext` 的 `codex/xgd-maintenance` 工作副本。其 24 个累计改动文件已由本轮主执行代理与交付基线 `afe5eb8` 核对一致；新工作树不会自动带入这些累计补丁，故继续既有维护 checkout，保留本包基线差异。具体证据记录于[开工记录](../../../evidence/B08/followup-20261028/run-record.md)。
- 复用 `TestProductionReportConfirmation`，在送审前提供 scope 测试参数；独立 runner 只补原卡缺失组合，不修改已批准冻结依据来造样例。真实方法名、命令和执行输出在[原 R07 本包绑定](../../../evidence/R07/report-concurrency.md#2026-10-28-b08-续接包命令绑定)更新。
- 使用默认 `spec-driven` 与 `skip_specs: true`：本次没有新增或改写需求，故引用已有契约；`tasks.md` 也只引用原卡。接受 CLI 不解析外部复选框的限制，不另建自定义 schema 或重复任务以凑齐状态。

## Risks / Trade-offs

- [CLI 规划文件状态可能被误读为实现完成] → 原卡和本批实际证据权威；不归档未完成包，不用 CLI 状态增加完成数。
- [历史样例已消耗、旧证据有限] → 不重放旧 HTTP 批，不把受控测试/页面/现场或完整 G1/G2/G3 混为一谈；按原卡保留停止和交付边界。
