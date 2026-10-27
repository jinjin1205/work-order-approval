> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R04｜OpenMES 静态适配矩阵

核查日期：2026-10-26。固定版本：Mes-Open/OpenMes，v0.27.0，commit b952915bddb2120737f10a730a1e45b1d162c47e。输入：[R02 fixture v1](../R02/fixture-spec.md) 与 [预期结果](../R02/expected-results.md)。本轮仅定向读取公开源码、迁移、请求、路由及既有测试；**没有安装、启动、执行应用测试或手机操作**。本文的代码推导不等于受控测试，运行结果统一为“未验证”。实际取证与范围见 [run-record](run-record.md)。

## 1. 筛选结论

**本轮不建议优先运行 OpenMES，保留为车间交互与生产追溯参考候选。** 已有源码可以复用工单／批次／工序、路线快照、工位限制、事务与行锁、库存草稿／过账／取消反向流水和部分余料退回；不能说它没有库存能力。但目标所需的六位输入、四位需求、逐笔有效报工与关联冲销、请求重试去重、手工领料与生产扣库一致性，已在关键链路上出现明确静态差异。另有库存网页操作入口与文档未对应，安装不能消除这些差异。

这是本轮“先筛选再限量运行”的投入建议，不是全面否定上游产品、性能结论或最终 R06 选型。没有估算工期、节省比例或跨机器兼容性。

## 2. 业务对象对应关系

| 本项目对象 | 真实候选对象／行为 | 判定及边界 |
|---|---|---|
| 工单计划10，初始任务0 | WorkOrderService::createWorkOrder 保存 planned_qty、process_snapshot，produced_qty=0、pending，不自动建 batch | 可配置后核验。工单已同时冻结 BOM／路线快照；本项目“人确认生成明细”需要另明确生成入口 |
| 3道任务，每道计划10 | createBatch(targetQty=10) 建1个 Batch，再由快照建3个 BatchStep；每步 incomingQty 来自前步 passed_qty，首步来自 Batch.target_qty | **局部改造**。Batch是生产批量；BatchStep是顺序工序节点。BatchStep没有独立任务计划量字段，也不能直接将Batch改名为派工任务 |
| 人员派工与 ALL／DEPT-A／PERSON-A | 步骤有 workstation_id、assigned_by/started_by/completed_by；工单策略按用户产线；可选工位路由限制 | **局部改造／任务授权关系需新增**。实际操作人、工位分派不等于允许报工人员清单；无证据支持本项目三种对象范围直接配置 |
| 3笔独立报工 | recordQuantity 累加 passed_qty、scrap_qty；不良另建 ScrapEntry；没有为每次良品调用建立独立有效报工行 | **必须新增有效报工与冲销关联记录**，复用现有状态、事务和汇总入口，不另造并行工单系统 |
| 最终合格产量10，不能30 | transfer 模式从最后有效步骤 passed_qty 汇总到 Batch，再汇总工单 | 有复用价值；与工序累计产量分开。whole-batch 模式完工会补齐未报余量，不能直接视为真实报工 |
| 首笔确认即开工，达到良品+不良计划即完成 | 原路径须显式 startStep；recordQuantity 要求 in_progress；数量报满后仍须 completeStep，最后批次/工单再推进 | **局部改造**状态推进；不能将按钮操作差异称为满足首笔报工自动开工 |
| 路线历史 | 建工单保存 process_snapshot；建批次保存 snapshot_version，并按该快照复制步骤 | 可配置后核验；复制工单不复制事实、路线切换/删除保护尚未运行 |

依据：[backend/app/Services/WorkOrder/WorkOrderService.php:173](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/WorkOrder/WorkOrderService.php#L173)、[backend/app/Services/WorkOrder/WorkOrderService.php:695](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/WorkOrder/WorkOrderService.php#L695)、[backend/app/Models/BatchStep.php:349](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Models/BatchStep.php#L349)、[backend/app/Services/WorkOrder/BatchService.php:608](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/WorkOrder/BatchService.php#L608)。

生成防重差异：createBatch 在工单行锁下计算下一个 batch_number，每次合法调用继续新建一批，而非识别原“生成3任务”的确认请求。行锁保证顺序，不保证第二次确认返回第一次结果。

## 3. 数量差异的实际改造面

不是只有一个 round(..., 2)。下列字段／服务同时参与同一条事实链；所列迁移是固定提交中的真实定义，未连接数据库核验最终 schema。

| 层次 | 已核实字段／计算 | 影响与最小检查／改动位置 |
|---|---|---|
| 生产计划与产出 | WorkOrder planned_qty/produced_qty、Batch target_qty/produced_qty 的模型为 decimal:2；建表为 decimal(10,2) | 影响建单、建批、汇总、存储；Models/WorkOrder.php、Models/Batch.php；对应 2026_02_16_210136/210137 迁移 |
| 工序良品与不良 | BatchStep passed_qty/scrap_qty 为 decimal:2；flow_ledger迁移 decimal(12,2)；availableQty 舍入2位 | Models/BatchStep.php；2026_09_15_100000_add_flow_ledger_to_batch_steps.php；BatchService 的 recordQuantity、recordQuantityThroughStation、completeStep、correctGoodQuantity、rollUpProducedQty |
| BOM输入与需求 | BomItem.quantity_per_unit decimal:4，scrap_percentage decimal:2；perUnitQuantity先保留6位；calculateRequiredQuantity最终4位 | 六位用量输入在持久化/模型读取处已受限；Models/BomItem.php、2026_04_29_100005_create_bom_items_table.php、BOM请求校验 |
| 需求计算入口 | BomItem最终舍入4位；BomService先分别舍入base/scrap再相加；MaterialAllocationService::calculateRequiredQty最终舍入4位 | 现有不止一条计算路径。需复用并统一权威口径，不能仅修改其中一个；涉及计划预览、快照分配、完工自动草稿 |
| 领退耗分配 | MaterialAllocation allocated/expected/returned/consumed/adjustment/scrap 均decimal:4；方法参数使用float | Models/MaterialAllocation.php；2026_05_09_100002和2026_05_22_122832迁移；MaterialAllocationService |
| 原料总量与预留 | Material stock_quantity/reserved_quantity 为decimal:3；stock_quantity建表为decimal(12,3) | Models/Material.php、对应库存/预留迁移；StockMovementService虽保留流水4位，不能替代总量精度修正 |
| 库位与库存单 | WarehouseStock.quantity、StockDocumentLine.quantity 为decimal:3，表decimal(14,3)；WarehouseStockService::adjust舍入3位 | 库位存量、单据行、过账/取消均受影响；Models/WarehouseStock.php、Models/StockDocumentLine.php、2026_08_03_100001/100003迁移 |
| 消耗与批次余额 | ConsumptionLocationService扣库差额按3位量化并忽略小于0.0005；StockDocumentService调整lot按4位 | ConsumptionLocationService、StockDocumentService；还须核实际使用lot模型／迁移／拣料路径的端到端精度，不能声称本轮已覆盖所有lot路径 |
| HTTP输入 | RecordStepQuantityRequest允许numeric但无单位精度规则；返回float；StoreStockDocumentRequest数量numeric>0；ReturnAllocationRequest最小0.0001 | 接受输入不代表保留精度；上述请求与对应界面/导出需同步，显示层和导出本轮未核验 |

关键来源：[backend/app/Models/BomItem.php:38](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Models/BomItem.php#L38)、[backend/app/Services/Material/BomService.php:105](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Material/BomService.php#L105)、[backend/app/Services/Material/MaterialAllocationService.php:824](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Material/MaterialAllocationService.php#L824)、[backend/app/Services/Warehouse/WarehouseStockService.php:28](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Warehouse/WarehouseStockService.php#L28)、[backend/app/Services/Material/ConsumptionLocationService.php:78](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Material/ConsumptionLocationService.php#L78)。

CASE-02 子项结论：

- Q01 的 0.5495 可表达，源码有最终4位需求计算；**运行未验证**。
- Q02/Q04/Q05 的原始用量需要5～6位，而 BOM 模型和字段是4位，不能原样持久化这些输入。不是只补显示四位即可。具体数据库舍入结果本轮未运行，不伪造结果。
- Q03 的任意父项基数不等于现有 per=unit/carton/pallet；basisDivisor 在包装容量缺失/非正时回退1。可以手工折算每件用量，但不等于具备独立基数、校验及单位换算来源。
- U01 的0.0004退料可进入allocation API，但3位原料总量/库位/库存单行不能保证0.0006端到端准确。千克↔克的完整单位换算入口未定位，未验证。
- V01/V02：原料有unit_price及消耗时的price snapshot；当前已查库存单行没有单价/金额字段，过账服务只移数量。没有取得移动加权平均库存计价的实现证据，记能力缺口／待查，不能标不适用。
- M01：transfer流最终produced_qty取良品8，但 WorkOrder::qualityPct 再计算 (produced−scrap)/produced。单步骤良品8、不良2按已读代码推导为75%，目标80%；**静态口径不匹配，未运行**。原生报工并不因8+2自动complete。
- M02返工独立统计、M03含返工的分母、M04零任务比例：未取得完整适用路径，未验证。qualityPct在produced<=0返回null可复用，但不能替代全部分支。

M01来源：[backend/app/Models/WorkOrder.php:698](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Models/WorkOrder.php#L698)、[backend/app/Services/WorkOrder/BatchService.php:689](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/WorkOrder/BatchService.php#L689)。

## 4. 库存服务、余料退回与重复扣料

### 4.1 可复用的库存生命周期与入口限制

StockDocumentService::createDraft 不动库存；post 在事务内锁单据、posted直接返回，之后同时更新库位、原料总量、流水及lot；cancel对已过账单反向应用，并将原单标cancelled。可以复用这些生命周期方法，但取消整张单据不能冒充“领10退2”。

公开固定仓库树有库存模型、迁移、服务、请求与服务测试；**本轮没有定位到手工Warehouse/StockDocument网页控制器或对应资源页面**。web.php第870～872行只有仓库段注释，后面直接进入Costing。api.php可定位到ERP库存单导出/ack，未见相应手工create/post/cancel路由。官方文档却写Admin→Warehouses操作，需后续解释文档与当前代码入口差异。不能把服务存在说成客户可以直接从现成页面完成领退入库。

warehouse开关是ModuleRegistry的核心可选区，源码明确与独立modules插件不同；**不据此猜测库存属于付费私有模块**。来源：[backend/routes/web.php:870](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/routes/web.php#L870)、[backend/routes/api.php:144](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/routes/api.php#L144)、[docs/warehouse-erp-rollout.md:136](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/docs/warehouse-erp-rollout.md#L136)、[backend/app/Support/ModuleRegistry.php:8](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Support/ModuleRegistry.php#L8)。

### 4.2 原生余料退回确实存在

API：POST /api/v1/material-allocations/{allocation}/return → ReturnAllocationRequest → MaterialAllocationController::return → MaterialAllocationService::returnQuantity。

它锁定并重新读取allocation，要求状态allocated、qty>0、退量不超过allocated−consumed−scrap；写TYPE_RETURN库存流水、释放预留、恢复lot picks、allocated_qty减退量、returned_qty加退量。和returnForBatch/cancel是不同路径。已有ReturnAllocationTest覆盖部分退回、退后完工不二次退回、超退、零量、未登录、产线外操作；PartialLotReturnTest覆盖lot回补。**只读到测试代码，没有执行。**

差异仍然存在：

1. 这是对生产allocation的即时退回，不是带审批／过账生命周期的独立退料单；重复同一qty没有请求关联键，余额足够时可再次退。
2. allocated_qty退后被改为净分配；累计领、累计退、净领须从原流水／退量按统一规则得出，不能直接将allocated_qty当“累计领”。
3. 普通material_receipt支持入库，但StoreStockDocumentRequest只校验仓、工单存在及lot所属material，没有原领料行引用、剩余可退量或跨工单原领料关系校验；不能直接拿它代替CASE-06完整退料规则。
4. 未填写实耗时，consumeForBatch用allocated_qty补consumed_qty；这与“未记录实耗就保持未记录”的目标不符。实际人工填consumption_recorded=true时可区分显式0，可复用该标记继续完善。
5. allocation退回主要对应此前扣过的全局stock/lot，location扣库另有时间点。不能用某一个余额变化声称所有仓位、单据和净领料已一致。

来源：[backend/app/Services/Material/MaterialAllocationService.php:586](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Material/MaterialAllocationService.php#L586)、[backend/app/Services/Material/MaterialAllocationService.php:373](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Material/MaterialAllocationService.php#L373)、[backend/app/Http/Requests/Web/Admin/StoreStockDocumentRequest.php:18](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Http/Requests/Web/Admin/StoreStockDocumentRequest.php#L18)。

### 4.3 人工发料与完工自动草稿不只是“会不会再建一单”

- generateForCompletion的alreadyHas按work_order_id+type判断，不检查该单是手工/自动、draft/posted/cancelled。有一张关联的手工material_issue时，通常会跳过再次自动生成；因此**不能断言完工一定再建一张重复发料单**。
- 该判断是“存在即跳过”，不能补足部分发料，也不能证明已取消或待过账单代表材料已发。未关联工单的手工单不能触发这个跳过。
- startStep会按BOM创建allocation并通过StockMovementService再次减少materials.stock_quantity；allocateMatching只查batch_id+material_id的allocation，不查手工stock document。后续consumeForBatch又按location_deducted_qty差额扣location。
- StockDocumentService::post则独立减少同一全局stock及warehouse stock，并未更新allocation/location_deducted_qty。**在同一仓/物料上将手工发料与上述生产路径组合，静态上存在同一事实重复扣减风险；待实测，本轮没有实际扣库故障结果**。这不是R02允许的“源仓转入在制仓后从在制仓消耗”：已查路径没有对应成对转仓事实。
- 无已存在material_issue时，完工自动草稿取lot consumed，若无记录则回退BOM×产量；之后过账仍走同一个独立扣库路径。自动草稿本身不动库存，风险发生在之后过账，不能写成完工立即扣库存。
- 可关闭WAREHOUSE_AUTO_DOCUMENTS减少自动草稿，但这不会解决先手工发料、后自动allocation之间的重叠。最小改造需选择唯一领用/消耗事实来源并关联现有服务；本轮不实施、不新增第二本库存账。

依据：[backend/app/Services/Warehouse/WorkOrderStockDocumentService.php:34](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Warehouse/WorkOrderStockDocumentService.php#L34)、[backend/app/Services/Warehouse/StockDocumentService.php:237](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Warehouse/StockDocumentService.php#L237)、[backend/app/Services/Material/MaterialAllocationService.php:676](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Material/MaterialAllocationService.php#L676)、[backend/app/Services/Material/ConsumptionLocationService.php:14](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Material/ConsumptionLocationService.php#L14)、[backend/app/Listeners/GenerateWorkOrderStockDocuments.php:23](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Listeners/GenerateWorkOrderStockDocuments.php#L23)。

## 5. 防重、冲销、权限：可复用与缺口

| 检查 | 有证据的能力 | 当前差异／限制 |
|---|---|---|
| 生产并发超报 | BatchService先锁工单再锁步骤，按当前availableQty限制；transaction包装 | I03/I04具备机制，数据库并发未执行；行锁不能替代I01/I05请求去重 |
| 同请求报工重试 | 请求只接受good_qty/scrap_qty/notes/through_station；recordQuantity每次增量更新 | 无请求键/原结果查回。余2、报1再重试1可在剩余范围内继续加1，是静态可见风险；实际HTTP未验证 |
| 同单库存重复过账 | post锁同单且posted立即返回；已有test_posting_twice_does_not_double_count | 可复用候选；I02未运行。创建两张不同单不受同单status去重保护 |
| 生成去重 | 完工草稿已有工单+类型exist检查；批次有编号唯一/行锁 | 自动草稿exist检查没有在已查服务内锁定生成或工单+type唯一约束；并发生成未验证。批次不同编号不等于请求去重 |
| 原报工更正 | correctGoodQuantity检查full策略、本人/主管、expected当前值、下游处理量，并写AuditLog | 仍直接update passed_qty，不是原报工保留+关联冲销；当前只允许运行中步骤，CASE-05已完成10→8不能照搬 |
| 历史连删 | WorkOrder软删除级联Batch、ScrapEntry等；Batch软删除级联BatchStep | 需要有事实后禁止连删的完整入口核验；软删/审计本身不能代替业务事实不可抹除；批量/永久删除路径未核完 |
| 普通报工权限 | 网页有Operator/Supervisor/Admin角色门槛、选择产线匹配；服务有可选workstation_routing | 工作站配置关闭或操作工无工作站时不限制工位；ALL/DEPT/PERSON语义仍缺；无现场越权实测 |
| 余料退回／实耗权限 | ReturnAllocationRequest和RecordConsumptionRequest调用工单view策略；策略检查view work orders并按产线 | “可查看工单”即能进入这些动作，不能等同本项目仓库领退料/记实耗的独立动作权限；应复用策略并收紧动作范围 |
| 库存数据授权 | 请求验证仓、工单和物料存在以及lot所属物料 | 实际网页控制器/路由未定位，不能凭request.authorize=true证明公开绕过，也不能声称仓库对象权限通过 |
| 状态失效 | BatchStep.productionBlocker检查批次/工单终态、暂停、阻塞等 | 当前状态再检查可复用；AI草稿过期确认未接入，未验证 |

来源：[backend/app/Http/Requests/Operator/RecordStepQuantityRequest.php:14](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Http/Requests/Operator/RecordStepQuantityRequest.php#L14)、[backend/app/Services/WorkOrder/BatchService.php:319](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/WorkOrder/BatchService.php#L319)、[backend/app/Services/Warehouse/StockDocumentService.php:95](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/Warehouse/StockDocumentService.php#L95)、[backend/app/Services/WorkOrder/BatchService.php:253](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/WorkOrder/BatchService.php#L253)、[backend/app/Policies/WorkOrderPolicy.php:32](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Policies/WorkOrderPolicy.php#L32)、[backend/app/Http/Requests/Api/V1/ReturnAllocationRequest.php:14](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Http/Requests/Api/V1/ReturnAllocationRequest.php#L14)。

## 6. CASE-01、02、04～08 总矩阵

“直接使用”以下仅指现有机制可优先复用；**没有任何CASE被记为运行通过**。

| CASE | 直接使用候选 | 配置后使用候选 | 局部改造／必须新增 | 本轮运行结论 |
|---|---|---|---|---|
| 01主链 | 工单/批次/步骤快照；最后工序产出汇总；库存服务 | 3步路线、BOM、两个仓、transfer模式、operator计数 | 人确认生成防重；任务授权；报工状态推进；库存UI入口待查；手工领料/自动allocation统一 | 未验证；原样完整链静态不匹配 |
| 02数量成本 | 可复用已有需求计算位置、库存流水 | 整数主链及损耗配置、明确模式 | 跨模型/迁移/服务精度；统一舍入；一般基数/单位换算待查；移动均价缺证据；良品率口径 | 未验证；六位精度及M01存在静态差异 |
| 04重复并发 | 库存同单post状态幂等、生产行锁 | PostgreSQL隔离库及负库存配置 | 报工请求去重/查回、生成请求去重；I05/I06故障实测入口另绑定 | 未验证；I01/I05无已查闭环 |
| 05冲销 | 现有状态/下游检查和审计可复用 | 禁止普通原值更正的策略可作为临时约束 | 必须新增逐笔有效报工/关联冲销事实；重算状态、下游逆序与连删保护 | 未验证；现有直接更正不符合目标 |
| 06领退耗 | allocation部分退回、反向流水；单据draft/post/cancel | block_negative_stock需启用；lot按需配置 | 退料单与原领用关系/审批、重复退回、累计领口径；停止把未记录实耗补成分配量；统一扣库 | 未验证；不可用取消替代退2 |
| 07权限状态历史 | 角色/产线策略、快照、当前状态检查 | 将样例角色映射现有角色/产线，仅作为起点 | ALL/DEPT/PERSON与仓库动作范围；确认即生效的状态规则；复制/删除保护待查 | 未验证；无越权请求或AI运行证据 |
| 08手机 | R01已确认同仓operator网页/PWA源码，沿用不重做 | 真实手机浏览器和样例角色 | 领退料网页入口待查；报工去重补齐后才能完整验证断网重试 | 未验证：手机尺寸、扫码、摄像头拒绝、刷新恢复、中文和现场稳定均无实际操作证据 |

## 7. 最小后续文件边界与停止条件

如果R06仍选OpenMES，先在R07绑定下面真实入口；**本轮不修改产品**：

1. 数量口径：backend/app/Models/{WorkOrder,Batch,BatchStep,BomItem,Material,MaterialAllocation,StockMovement,WarehouseStock,StockDocumentLine}.php；backend/app/Services/Material/{BomService,MaterialAllocationService,ConsumptionLocationService,StockMovementService}.php；backend/app/Services/Warehouse/{WarehouseStockService,StockDocumentService,WorkOrderStockDocumentService}.php；上表对应迁移。已有数据的精度迁移应新增迁移文件，不能直接改历史迁移冒充客户升级方案。
2. 报工事实/幂等/冲销：backend/app/Services/WorkOrder/{BatchService,WorkOrderService}.php；backend/app/Http/Controllers/Web/Operator/BatchController.php；backend/app/Http/Requests/Operator/{RecordStepQuantityRequest,CorrectStepQuantityRequest}.php。新增逐笔事实表/冲销关联的具体文件名尚未设计，不编造已有文件。CorrectStepQuantityRequest本轮未取正文，只由真实controller引用定位，后续需读。
3. 权限：backend/app/Policies/WorkOrderPolicy.php；backend/app/Http/Requests/Api/V1/{ReturnAllocationRequest,RecordConsumptionRequest}.php；backend/routes/{web,api}.php；相关operator controller。保留现有权限体系，补动作及对象边界。
4. 库存唯一事实来源：上述库存服务、backend/app/Listeners/GenerateWorkOrderStockDocuments.php、backend/config/openmmes.php；先解释文档中的网页入口在哪里，再决定复用还是补最小页面/调用入口。
5. 沿用已有测试：StockDocumentServiceTest、WorkOrderStockDocumentTest、ReturnAllocationTest、PartialLotReturnTest，以及BatchServiceTest。仅新增目标差异案例，不重建一套测试框架；既有测试没有运行就不记通过。

本轮达到静态筛选结束条件：已明确复用点、必要改造面、调用链和运行限制。不继续扩展设备采集、离线、商业模块、全仓审计或应用安装。若仍需比较交互，待根任务选定有限候选后再运行对应CASE；不能为凑三套候选同时启动服务。

