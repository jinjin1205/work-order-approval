# Spec Delta

## Purpose

把原生产工单CASE-01的人确认边界落实为可验收行为：先保存工单，再预览并确认工序计划和用料计划；准备明细与批准后的执行事实分别记录，避免自动生成及重复追加。

## ADDED Requirements

### Requirement: Empty production draft

新审批工单 SHALL 允许保存并重开空工序和空用料，页面提示先预览/确认；空明细不能送审。

#### Scenario: Save and reopen
- **WHEN** 普通有权发起人保存一张未准备明细的新工单
- **THEN** 重开后工序和用料均为0，报工和库存事实为0

### Requirement: Human confirmed details

系统 SHALL 以原权威计算提供只读预览，由当前有权发起人在草稿/退回状态确认后生成计划；来源变化、无权及冻结状态拒绝，已有不同明细不得自动覆盖。

#### Scenario: Preview confirm and replay
- **WHEN** 计划10、三道工序、BOM单位用量0.5、父基数1、损耗0，发起人预览后确认并重试
- **THEN** 预览不写入；确认后3个有序任务和1行需求5；重试保留同明细，不生成Job Card或库存事实

#### Scenario: Changed or unauthorized context
- **WHEN** 工单或BOM/路线在预览后变化，或角色/公司/班组/状态不允许
- **THEN** 拒绝新生成且工单/明细/事实无部分修改
