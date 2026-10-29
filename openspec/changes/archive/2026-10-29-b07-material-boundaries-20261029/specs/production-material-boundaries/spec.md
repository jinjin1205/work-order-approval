## ADDED Requirements

### Requirement: Local material saves retain the shared BOM

系统 SHALL 允许有权发起人在草稿或退回的本工单保存用料，明确作用域；通用BOM维护独立确认并遵守原权限和版本保护。

#### Scenario: Local quantity adjustment

- **WHEN** 发起人将本单需求5调整为6并保存重开
- **THEN** 本单保持6，原产品BOM用量不被改写

### Requirement: Material history locks survive zero net issue

系统 SHALL 在领退历史存在时保留结构追溯，不能由净额归零或直接子行入口绕过冻结和归属检查。

#### Scenario: Fully returned material

- **WHEN** 工单已领10并退10后试图删除或改挂物料行
- **THEN** 请求被拒绝，原行与库存事实保留

### Requirement: Material quantities expose their actual source

系统 SHALL 区分库存单位的需求、累计领退、净领与实耗；没有接入的待审批来源明确未知。

#### Scenario: Pending approval source unavailable

- **WHEN** 当前库存审批状态未接入
- **THEN** 待审批数量显示未接入，不能用草稿或0冒充已验证来源
