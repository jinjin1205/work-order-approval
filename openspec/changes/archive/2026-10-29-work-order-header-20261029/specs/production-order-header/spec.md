# Spec Delta

## Purpose

使有权人员能用现有字段和编号准备产品、计划数量及交期明确的工单，并在送审前识别缺失资料。草稿完整性提示和正式送审约束分别处理，保留已有事实、编号和审批冻结边界，不补造交期或自动生成执行事实。

## ADDED Requirements

### Requirement: Native header and identifier
系统 SHALL 使用原工单字段及原生唯一编号，保存重开不改号，重复编号不得产生第二张有效业务单。

#### Scenario: Unique saved orders
- **WHEN** 有权发起人保存两张有效草稿并重开
- **THEN** 使用不同原生编号，字段保持，重复同号写入被拒绝

### Requirement: Delivery readiness before review
交期 SHALL 可在草稿暂空并明确提醒；送审必须填交期，填写的交期早于计划开始时只提示可能逾期并保留原值；非法日期仍拒绝。已有批准单的报工与合法收尾不强迫追补新字段。

#### Scenario: Fill delivery before review
- **WHEN** 无交期草稿尝试送审，再由发起人补齐合法交期
- **THEN** 首次拒绝且状态/事实不变，补齐后按原审批送审并冻结依据

#### Scenario: Overdue delivery remains truthful
- **WHEN** 交期早于计划开始但日期合法
- **THEN** 提示可能逾期并保留输入交期，不迫使改期来通过保存

### Requirement: Specific missing prerequisites
前置提示 SHALL 区分缺BOM、缺工序路线、缺用料，复用原校验/权限/展开，不自动产生半张有效单。

#### Scenario: Missing source data
- **WHEN** 缺BOM、工序路线或生产用料而保存或预览
- **THEN** 指出具体缺项与修复方向，不写入任务、用料或执行事实
