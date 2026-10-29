## ADDED Requirements

### Requirement: Independent task plans retain the order plan

系统 SHALL 在原工序行保存独立任务计划，支持小于工单计划的部分任务；报工、计划卡、状态和差额取本道计划，不改工单计划或制造库存事实。

#### Scenario: Partial task completion

- **WHEN** 工单计划10、本道任务计划2，确认良品1和不良1
- **THEN** 本道完成、父计划仍10，其余任务和成品入库不被冒算完成

### Requirement: Task edits follow the parent approval and history boundary

系统 SHALL 复用原生工序表编辑及唯一任务授权；合法草稿调整可保存，送审冻结和历史保护不得被直接子行入口绕过。

#### Scenario: Frozen task without a report

- **WHEN** 工单已送审，用户尝试直接改写或删除尚无报工的任务行
- **THEN** 请求被拒绝、原行及父单不变

#### Scenario: Explicit draft insertion and copy

- **WHEN** 有权发起人在草稿增加、复制、插入、删除并完成原生顺序校验
- **THEN** 重开后的任务行身份和顺序正确，复制形成新行而不继承报工事实
