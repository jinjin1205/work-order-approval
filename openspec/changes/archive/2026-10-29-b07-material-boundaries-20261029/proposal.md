# Proposal

## Why

原B07用料生成已有验收；本单保存/通用BOM维护及历史结构入口仍待补齐。B06工位隔离已纠正，本包从该有限未完成处继续。

## What Changes

复用原本单编辑、B04数量、审批、库存来源及原生BOM版本，补材料子行和成本旁路结构保护、明确保存作用域与生效数量。待审批来源未接入时明确未知，不新增库存审批。

## Capabilities

### New Capabilities

- `production-material-boundaries`: 本单用料保存范围、历史锁与数量来源。

### Modified Capabilities

无。

## Impact

原制造七文件，两个原子行控制器纳入维护清单；无新事实账、依赖、字段类型或库存核心改动。
