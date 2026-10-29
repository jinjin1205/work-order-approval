# Proposal

## Why

原B05仍缺活动计时收尾、人工结束差额和原因。用户授权先补R07绑定再实现验收，不能用原停止/审批测试代替。

## What Changes

识别真实开放计时，明确人工收尾后才能结束；复用原状态/计时校验/Comment，保存结束差额与原因。范围和步骤唯一引用原R07/B05，不增整卡或并行事实。

## Capabilities

### New Capabilities
- `production-order-closeout`: 记录原B05既定的结束行为。

### Modified Capabilities
无。

## Impact

原WorkOrder控制器/表单/测试、JobCard控制器，共4份产品文件，无元数据/依赖变化。其余边界见原R07。
