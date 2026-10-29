# Proposal

## Why

用户要求收口原B05剩余状态动作及未覆盖入口。前三包已有成果；当前状态菜单仍暴露服务器已禁止的原生停止/恢复入口，复制及父删需要定向核验。

## What Changes

仅执行原R07本轮绑定及原B05三子项，修真实缺口并回填入口矩阵；已验未变项不重跑。

## Capabilities

### New Capabilities

- `production-order-entries`: 登记原B05既有动作及新建、复制、删除边界。

### Modified Capabilities

无。

## Impact

最多原Work Order四文件，元数据仅既有no_copy；无新字段、依赖、状态机或事实账。详细计划仍为原R07/原卡。
