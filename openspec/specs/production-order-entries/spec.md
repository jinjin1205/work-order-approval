# production-order-entries Specification

## Purpose

规范生产工单普通新建、复制、取消修订和父单删除入口，保持审批、计划与执行事实的边界。复用原有状态、权限、编号及历史保护，让有权人员能够操作、失败有明确提示，并保留原生产与库存记录。

## Requirements

### Requirement: Controlled state actions

审批工单页面 SHALL 与原服务器动作一致，停止使用厂长、当前版本和原因，不提供原生恢复旁路。

#### Scenario: View state actions

- **WHEN** 普通岗位打开已批准或已停止工单
- **THEN** 不显示原生停止/恢复，授权动作使用既有审批菜单，服务器权限不弱化

#### Scenario: Cancel stopped order

- **WHEN** 厂长带当前版本和原因取消无执行历史的停止工单
- **THEN** 允许取消修订，保留原单；已有计时、报工或库存历史仍拒绝取消

#### Scenario: Amend cancelled order

- **WHEN** 有原生新建和修订权限的发起人打开已取消的审批单
- **THEN** 可使用修订入口，新单清除旧审批、计划和实绩，重新准备并审批，原单不变

### Requirement: Fresh copy and preserved facts

新建或复制工单 SHALL 从未执行草稿开始，任务及用料为空，不能继承实际生产事实；父单删除不得抹除历史。

#### Scenario: Copy executed order

- **WHEN** 发起人原生复制后保存重开
- **THEN** 新号、草稿、空明细，不带实际日期/报工/库存事实，原单不变

#### Scenario: Fabricate facts on create

- **WHEN** 新建输入包含实际生产日期或实际数量
- **THEN** 服务器拒绝且无半张单或事实残留

#### Scenario: Delete parent

- **WHEN** 有权人删除无历史新草稿或有历史原单
- **THEN** 前者可完成，后者沿原权限和历史保护拒绝，原记录保持
