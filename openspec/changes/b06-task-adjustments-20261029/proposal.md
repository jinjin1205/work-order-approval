# Proposal

## Why

原B06剩余任务调整与授权需完成；PRD 5.3.2明确允许工序计划小于工单计划，现工序没有独立计划字段。

## What Changes

按原R07七文件绑定接通独立任务计划、原生草稿编辑和冻结保护。已有生成及事实保护复用，不重做B05/B08。

## Capabilities

### New Capabilities

- `production-task-adjustments`: 原B06工序任务调整、独立计划与授权边界。

### Modified Capabilities

无。

## Impact

原ERPNext制造七文件；仅一个任务计划字段。无第二套任务/库存账、无依赖或Frappe修改；不代表整体验收或交付。
