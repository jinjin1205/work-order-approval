# Design

## Context

任务用Work Order Operation、事实用Job Card.operation_id；工单计划与本笔卡数量已经分离，但任务计划仍取父数量。

## Goals / Non-Goals

执行原B06及[R07唯一计划](../../../../evidence/R07/card-binding.md#2026-10-29-b06任务调整与授权绑定)。不复制任务列表，不扩审批/委外/客户部署或完整G1/G2/G3。

## Decisions

新增Data型report_plan_qty保留原始精度，权威读取复用B04校验；仅旧空值沿父计划语义。原生行身份/idx/sequence_id与父表保存负责完整链，敏感直接子行编辑拒绝并提示回父表；草稿普通时间/末行删除保留。报工scope仍用已有唯一判定。

## Risks / Trade-offs

不同计划影响计划卡、限额、前后工序、状态和人工结束差额，全部纳入有限受影响范围；不以JSON新增代表真实数据库/页面完成。已有批准记录不批量回填，受控测试回滚、页面只用新样例。
