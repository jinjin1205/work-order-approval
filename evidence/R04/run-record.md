> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R04｜执行记录

日期：2026-10-26（Asia/Shanghai）。任务：OpenMES执行与库存适配静态筛选。状态：**静态筛选结束；本轮暂不运行**。根任务已选ERPNext进入有限运行先导；这里不把OpenMES暂缓运行写成运行失败，也不把定向检查写成全功能不支持。

## 1. 输入、版本、环境与动作

| 项目 | 实际记录 |
|---|---|
| 目标卡 | docs/任务卡/01-复用核验与选型.md，R04 |
| 已读约束 | AGENTS.md、docs/开发TODO.md；本轮禁止产品改造、安装和服务启动 |
| 固定来源 | Mes-Open/OpenMes，commit b952915bddb2120737f10a730a1e45b1d162c47e；v0.27.0来源沿用R01 |
| 输入 | evidence/R02/fixture-spec.md v1、expected-results.md；重点CASE-01/02/04～08 |
| 已有证据复用 | R01来源、许可、同仓operator/PWA、部署和测试入口；R04卡片已有两位float与直接原值更正结论。不重做全部介绍/前端可获得性核查 |
| 本地工作目录 | .；本轮只写本目录evidence/R04下两份文档 |
| 环境 | macOS本地Codex读取文档；GitHub connector定向读取公开文件。没有OpenMES checkout、应用数据库、浏览器会话或手机样例实例 |
| 读取工具 | github_fetch固定commit recursive tree；github_fetch_file指定repository_full_name、ref、path |
| 实际结果 | tree返回truncated=false；取得51个固定提交文件的UTF-8内容/元数据。没有运行这些PHP方法或测试 |
| 输出 | fit-matrix.md、run-record.md |
| 未执行 | clone、依赖安装、容器/服务启动、数据库迁移/初始化、业务HTTP调用、单测/集成测试、并发/超时注入、手机操作、AI调用、客户部署 |
| 边界 | 未改TODO/共同任务卡、上游产品、Docker daemon或全局配置；没有使用客户数据 |

实际读取操作模式（工具参数，非应用执行命令）：

    github_fetch(url="https://api.github.com/repos/Mes-Open/OpenMes/git/trees/b952915bddb2120737f10a730a1e45b1d162c47e?recursive=1")
    github_fetch_file(repository_full_name="Mes-Open/OpenMes",
                      ref="b952915bddb2120737f10a730a1e45b1d162c47e",
                      path="<下表真实文件路径>")

本地读取用cat/sed/rg核对任务卡与样例；获取后在工具内按函数名、字段、round/decimal、路由和授权关键字定位，再读取相关方法全文。预期是明确真实调用入口/存储字段/原生行为，不是执行R02或产生通过率。

探索时两个假设路径backend/app/Services/InventoryService.php、backend/app/Models/WorkOrderBatch.php返回GitHub 404；随后按固定仓库树找到真实Warehouse/Material服务和Batch模型。404只说明这两个文件路径不存在，不作为库存/批次功能缺失的依据。

## 2. 核查回执

| 核查动作 | 实际输出／观察 | 与目标关系 | 证据性质 |
|---|---|---|---|
| 跟随createWorkOrder→createBatch→createBatchStepsFromSnapshot | 工单冻结快照；每批复制工序；再次createBatch继续新编号 | 可复用顺序快照；不是生成请求防重；Batch不能直接当派工任务 | 源码静态 |
| 跟随recordQuantity及controller/request | float参数、2位舍入、累计update；未查到请求键或良品独立报工行 | I01/I05缺原结果查回；冲销需要原事实记录 | 源码静态；未发重复请求 |
| 跟随生产模型与迁移 | 生产2位、BOM/分配4位、原料/库位/库存单3位 | 修改面跨字段、服务和入口；不是页面显示问题 | 源码静态；未连数据库 |
| 跟随transfer产量与qualityPct | produced_qty由最后步骤良品而来；qualityPct再次扣scrap | 单步8良2不良推导75%，目标80% | **源码推导未运行** |
| 跟随StockDocumentService::post/cancel | transaction+同单行锁+posted返回；取消反向applyLine | 可优先复用同单重复过账保护，取消不等于部分退料 | 源码静态；未过账 |
| 跟随原生returnQuantity | allocation行锁、可退上限、TYPE_RETURN、累计退、恢复lot | 原生余料退回存在；审批/单据/请求重试语义仍需适配 | 源码静态；未退料 |
| 跟随人工post→start allocation→consume location→完成草稿 | 手工单与allocation分别调整库存，缺同一事实关联；alreadyHas仅工单+type | **重复扣减为待实测风险**；不能说完成必定建重复单或立即重复扣库 | 源码推导未运行 |
| 跟随return/consume请求授权 | 两者调用工单view策略；该策略按角色/产线 | 现有查看权限不能直接当仓库动作权限；三种任务范围需补齐 | 源码静态；未发越权请求 |
| 查fixed tree、web/api路由与warehouse runbook | 服务/测试存在；本轮未定位手工库存网页controller/页面/操作路由，文档却给页面菜单 | 需要解释入口差异；不称库存能力不存在，不猜商业私仓 | 目录/源码/文档交叉核查 |
| 查既有测试 | 有post两次、cancel反向、部分退回、超退/越线等测试方法 | 后续可复用，无需重复写同样测试 | 测试源码存在；**未执行** |

## 3. CASE执行状态

| CASE | 执行状态 | 不能据本文声称的结果 |
|---|---|---|
| 01 | 未验证 | 创建3任务、实领5、3笔报工、入库10已运行成功 |
| 02 | 未验证；精度与质量指标静态差异已登记 | 应用算术通过、库存均价正确、导出和AI取数一致 |
| 04 | 未验证 | 行锁即并发通过、status去重即所有重试通过 |
| 05 | 未验证；直接改原值静态不符合 | 有审计日志即完成关联冲销 |
| 06 | 未验证；原生部分退回已定位 | 测试源码即领退耗全链通过、库存取消即余料退回 |
| 07 | 未验证 | 权限/状态全部安全、历史不可连删、复制不带事实 |
| 08 | 未验证 | PWA源码即中文/手机易用、弱网恢复或现场稳定 |

实际样例ID、身份、输入输出、库存前后、请求区间、手机型号与浏览器均没有生成；不得填写虚构值。客户环境未提供不影响此轮公开代码筛选，也不能解释为不存在遗留系统。

## 4. 若后续重新进入运行的最小入口

以下只是绑定到已有文件的后续入口，**本轮没有执行，也不是已审批的安装命令**。

- 固定同一commit，先解释手工库存网页入口差异；使用R01已有隔离部署入口，不复用客户库。
- 后端已有phpunit.xml/composer test；可用php artisan test的文件参数限定StockDocumentServiceTest、WorkOrderStockDocumentTest、ReturnAllocationTest、PartialLotReturnTest、BatchServiceTest。依赖/数据库未就绪前不执行；默认SQLite测试不能代替PostgreSQL并发验收。
- 界面/HTTP只使用已核路由：网页operator/batch、operator/batch-step/{batchStep}/start、/quantity、/complete；API /api/v1/material-allocations/{allocation}/return、/consume。实际部署前缀、session/auth、样例真实ID届时记录，不在这里伪造curl请求。
- CASE-04先跑库存同单过账和报工重试差异；CASE-06分别核allocation退回与库存单取消；CASE-01核手工发料与自动allocation的同源余额，不将“源仓→在制仓”未发生的转移写成事实。
- 需要运行时只覆盖所选风险分支；未选择本候选则停在此记录，不扩成安装、修复或功能开发。

## 5. 本轮取得的文件与blob SHA

以下51个SHA是Git文件blob SHA，**不是仓库commit**。全部使用本页固定commit读取。正文引用按GitHub固定提交行号定位；没有完整克隆仓库，也不将这些文件当成完整软件交付包。

| 文件 | blob SHA |
|---|---|
| backend/app/Http/Controllers/Api/V1/BatchStepController.php | 9d6056c177538339c4a268e49d5324c75dc9575a |
| backend/app/Http/Controllers/Api/V1/MaterialAllocationController.php | 11c8c00e60d1ab6254197176ddba9005b6d8e61c |
| backend/app/Http/Controllers/Web/Operator/BatchController.php | 5fb5617ebee82d9ce86701fa27b70e7767069774 |
| backend/app/Http/Requests/Api/V1/RecordConsumptionRequest.php | 3f72b59d1b419bf266f424d5b693992114fdb05a |
| backend/app/Http/Requests/Api/V1/ReturnAllocationRequest.php | 2bdbd11c3c7ca28eb37fcffbc43d4f780fbd6f33 |
| backend/app/Http/Requests/Operator/RecordStepQuantityRequest.php | 7d2fdf025016800e0b46e49d8a52aa7edfca9ddc |
| backend/app/Http/Requests/Web/Admin/StoreBomItemRequest.php | b1f0bb37e01d746657be8ca0a0dd214835b9cc40 |
| backend/app/Http/Requests/Web/Admin/StoreStockDocumentRequest.php | 91d947b4a871ad708878f9525bd731aad9040b69 |
| backend/app/Listeners/GenerateWorkOrderStockDocuments.php | 3eb378f8a62a96ef16739c50f72b2b44132a60d9 |
| backend/app/Models/Batch.php | 9ccb2f57f2e5fe7c795553e246e8a3b52da41664 |
| backend/app/Models/BatchStep.php | 5a78d23a35bddcfa9339d401f4793219e80fdb42 |
| backend/app/Models/BomItem.php | 4bae4ad621144182660bb8c993b7276b2d665ded |
| backend/app/Models/Material.php | 3ec2c7eeb3880b4a9699a9c9f6e4f1d31663cbb5 |
| backend/app/Models/MaterialAllocation.php | 3ee4b2ca4dfd253e86858031d7e2acdf5f965ad4 |
| backend/app/Models/StockDocument.php | ac0e7543ec752dba892a596ab88c0c7829cfa96f |
| backend/app/Models/StockDocumentLine.php | 296eb3636f585c95a56a59e0a4fc411dabfd906d |
| backend/app/Models/StockMovement.php | b83a8eea74015d3e04d4a36aa98a37b245c59413 |
| backend/app/Models/WarehouseStock.php | 4a0d2690b99fbdcfb62027e0280264be598f54df |
| backend/app/Models/WorkOrder.php | d571f7f24401e374d492175388647d108a4e3f7b |
| backend/app/Policies/WorkOrderPolicy.php | 47d117e5e9556b809ce4f110f8990849f206e6ab |
| backend/app/Services/Material/BomService.php | 0818bfc90d950662cfc9acc114664f02fab86800 |
| backend/app/Services/Material/ConsumptionLocationService.php | 1a110255d41551554a5f209e82d62de1b8370bce |
| backend/app/Services/Material/ManualMaterialReceiptService.php | 2633db22ae79b7d1eb55fb2fb337272b68d0b8c5 |
| backend/app/Services/Material/MaterialAllocationService.php | 652bc2bb9411d1758e14f08dc9b75125dad0daba |
| backend/app/Services/Material/StockMovementService.php | 39fc489256f5627712f11e6c131c48933de486ba |
| backend/app/Services/Warehouse/StockDocumentService.php | f54429ec923ffa83fdd0e577549b3eccd40bd381 |
| backend/app/Services/Warehouse/WarehouseStockService.php | cad4b89ac07b6725700f165671f2ffe15f8d7e47 |
| backend/app/Services/Warehouse/WorkOrderStockDocumentService.php | 43295c2b2556affb1f1847ec6a46243f4005292d |
| backend/app/Services/WorkOrder/BatchService.php | 7489bdf4a15d54063d2623562846618c53746189 |
| backend/app/Services/WorkOrder/WorkOrderService.php | ad27b04a4497b1f392a4312d8f476d7b693508a9 |
| backend/app/Support/ModuleRegistry.php | 82d9d8863cc41ed1ca7f0c74da333402aacd7477 |
| backend/config/openmmes.php | 58e920879b51577a7d31ecf7ba25385d5961b9f3 |
| backend/database/migrations/2026_02_16_210136_create_work_orders_table.php | e6ef06bc99c64c24cc34b7fe8f78b809c30ba658 |
| backend/database/migrations/2026_02_16_210137_create_batches_table.php | aef93ce6851b8afff0e80586e612fbeaaf782b8c |
| backend/database/migrations/2026_04_29_100005_create_bom_items_table.php | 22a3832c49e482c54fdccf3b9a767b07293c086a |
| backend/database/migrations/2026_05_09_100001_add_stock_quantity_to_materials_table.php | f2d40a5439747af984b73d43992e1cfa4afec229 |
| backend/database/migrations/2026_05_09_100002_create_material_allocations_table.php | d68fd717a992a62b7f221fa8226d07821049d15e |
| backend/database/migrations/2026_05_22_121955_create_stock_movements_table.php | ba8711b502d67f207f4772f99485508da4ea0232 |
| backend/database/migrations/2026_05_22_122832_add_consumption_split_to_material_allocations.php | 1b4441bb373f01408e289c4f9b252adbe4e64743 |
| backend/database/migrations/2026_08_03_100001_create_warehouse_stocks_table.php | 163a30c1d9dae20f1e66a003bd3534f87429db8d |
| backend/database/migrations/2026_08_03_100002_create_stock_documents_table.php | 859db7fc99f6423dbdf08028ffec73a5d25ff602 |
| backend/database/migrations/2026_08_03_100003_create_stock_document_lines_table.php | 17a892c13fb7abe448e1f09206a9fbd4e60bdae0 |
| backend/database/migrations/2026_08_27_100001_add_passed_qty_to_batch_steps.php | f17ae8ae9c4fcada6cad678358ffd45f7aae5895 |
| backend/database/migrations/2026_09_15_100000_add_flow_ledger_to_batch_steps.php | 42923274080d5243b82dd3d18b635677bef3ef84 |
| backend/routes/api.php | 19cdfe6ebc09c0d86b5e0be3c9e9318a581f6c37 |
| backend/routes/web.php | df3ea827f9ba991140d76df284efe0296fefae51 |
| backend/tests/Feature/Api/V1/ReturnAllocationTest.php | 0f89a55cf16d2072e20e603d3475a6cc06d11533 |
| backend/tests/Feature/Material/PartialLotReturnTest.php | f79b45271dfca6a7e6b18758965bf1b571087969 |
| backend/tests/Feature/Warehouse/StockDocumentServiceTest.php | cdce6fe67a3564e0e2a04d753324b859555332f1 |
| backend/tests/Feature/Warehouse/WorkOrderStockDocumentTest.php | 1566cf38b08061bd5b77d07094dfd0ad8701b6a4 |
| docs/warehouse-erp-rollout.md | f469ad7054b291255f1f1872ce5f80a9a1043fdd |

## 6. 收口

R04本轮完成静态适配和筛选，运行阶段未执行。详细可复用／配置／局部改造／新增矩阵、最小文件边界及限制见[fit-matrix](fit-matrix.md)。本记录不替代R06最终选型、R07实施绑定、受控业务验收或现场验收。

