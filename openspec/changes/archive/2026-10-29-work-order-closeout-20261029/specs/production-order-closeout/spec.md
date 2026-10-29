# Spec Delta

## Purpose

实现生产工单现有人工结束要求：在受权人员确认既有活动计时已经收尾后，按当时有效事实保留差额、原因、操作者和时间；结束不得改写原报工或被当作成品全部合格交付。

## ADDED Requirements

### Requirement: Explicit timer finish before close
系统 SHALL 拒绝带开放计时结束工单，并允许有权人员按明确实际时刻收尾既有草稿计时；停止状态不阻止合法收尾，但不得恢复或新增执行。

#### Scenario: Finish existing timer
- **WHEN** 已批准工单存在开放计时，人员选择合法结束时间
- **THEN** 仅原开放时间行结束，不提交报工或改变数量，之后才可人工结束工单

### Requirement: Authorized manual close with historical gap
人工结束 SHALL 核最新状态/授权/版本并强制原因，在同一事务保存各工序和成品入库差额及处理人/时间；重复不得改写原结束记录。

#### Scenario: Close with partial production
- **WHEN** 厂长结束计划10、某工序良8不良2、成品入库0的工单
- **THEN** 保留该工序未清0及成品未入库10、原因和原事实，不记成已合格交付10

#### Scenario: Invalid close
- **WHEN** 无权/撤权/陈旧请求、开放计时、原因缺失或保存记录失败
- **THEN** 拒绝或回滚，状态/原事实/结束记录无部分成功
