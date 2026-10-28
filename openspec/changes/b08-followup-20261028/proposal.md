# Proposal

## Why

原 B08 核心逐笔报工已有局部证据，权限组合、规则停用/重启和真实入口体验仍有明确缺口。本 change 接入原任务卡的 2026-10-28 续接包，需求、方案和任务只维护一份。

## What Changes

- 依照[原 B08 下一包详细执行卡](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-下一包详细执行卡沿原编号尚未运行)，仅补 B08-02、B08-05、B08-07 的缺失证据；真实失败才在既有绑定入口作最小修补。
- 本 change 使用引用模式：原卡、[R07 事实/并发绑定](../../../evidence/R07/report-concurrency.md)、[权限绑定](../../../evidence/R07/permissions.md)、[时段绑定](../../../evidence/R07/time-config-binding.md)继续作为权威依据，不复制另一套验收清单。
- 已验且实现/输入/依赖未变化的三笔正例、防重和依赖子项直接引用历史证据；不扩展工资结算、AI、库存逆向或客户部署。

## Capabilities

### New Capabilities

无。现有需求未增加，`skip_specs: true` 用于此次已有契约的验证续接和流程接入，不新造规格凑齐工具状态。

### Modified Capabilities

无需求变更。允许的最小修补只使既有实现满足原卡；如需改变需求或白名单范围，先停止受影响方案并记录，不通过本 change 默许扩张。

## Impact

沿原卡绑定的 ERPNext 报工读取/确认、B14 内部规则读取及原生中文入口；测试复用 `TestProductionReportConfirmation` fixture。运行、结果、源码版本和限制记于[本包记录](../../../evidence/B08/followup-20261028/run-record.md)。B08/B09 整卡、G1/G2/G3 和 Z01/CASE-11 不随本包关闭；新测试和现场体验尚未验证，change 不归档。
