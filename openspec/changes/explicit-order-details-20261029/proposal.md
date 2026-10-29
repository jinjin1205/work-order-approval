# Proposal

## Why

原CASE-01要求空明细建单后由人确认生成；现客户端和服务端自动补明细。用户2026-10-29授权按R07绑定完成B05/B06/B07本包实现和验收。

## What Changes

本包仅实现新审批工单的空明细保存、只读预览和明确确认生成，保留原BOM计算/权限/审批/事务。详细范围及验收唯一入口为原R07本包绑定和原B05/B06/B07；不重开不变的已验子项。

## Capabilities

### New Capabilities

- `production-order-details`: 将原CASE-01既有要求登记为OpenSpec行为契约，不增加业务范围。

### Modified Capabilities

无既有主规格。

## Impact

只改原Work Order控制器/表单/测试三文件；原计算、报工、库存及Frappe不改，无新增元数据或依赖。检查脚本/运行环境/结束条件见原R07绑定。
