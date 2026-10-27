> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R05｜ERPNext 固定 15 系适配矩阵

最新状态（2026-10-26补证后）：选型核验收口，产品差异未修复。第1～5节为静态阶段，第6节为首次运行，第7节为本轮最新结果；历史“未验证”按所属阶段理解，不覆盖后续实测。

静态核查日期：2026-10-26；本文件静态证据截止 09:34 UTC（17:34 北京时间）。核查范围：R05、R02 fixture v1 的 CASE-01～07 及必要的 PC/手机边界。以下1～5节以静态取证为主；同日后续已执行隔离限量运行，现状见第6节及[运行记录第5节](run-record.md)。没有业务验收或客户部署通过结果，未验部分保留。

**筛选结论：已进行限量运行的有条件候选；R05部分完成。** 固定版本已有工单、工序作业卡、原料转在制、消耗、余料退回、成品入库和统一库存账，可继续验证其复用价值。明确差异集中在报工事实粒度、损耗自动推导、任务与工单状态、十进制计算、重复请求语义及对象授权。尚不足以选定主底座，不能给出节省比例、人天或改造成本结论。静态阶段未启动服务；后续使用隔离官方容器，始终没有改产品代码。

## 1. 版本与判定口径

| 项目 | 核查基线 |
|---|---|
| ERPNext | `v15.124.1`，仓库 commit `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e` |
| Frappe | `v15.124.0`，仓库 commit `f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab`；后续隔离镜像版本一致，8个关键文件blob已比对，非全镜像审计 |
| 来源与许可边界 | 沿用 [R01](../R01/erpnext-evidence.md)，不把旧 `develop` 结果当本版本证据；主许可和完整依赖许可不能混同 |
| 输入与期望 | [R02 fixture v1](../R02/fixture-spec.md)、[R02 expected-results](../R02/expected-results.md)、[C05](../../docs/决策与范围.md) |

下表“直接复用候选”指已定位相关实现，**不是已经可用或已通过**；“配置”指源码存在可调选项；应用过的有限配置见第6节，其余尚未验证；“局部改造”指已见目标规则差异，具体实施仍受 R06/R07 门槛；“未知”表示本轮证据不足。一个需求可同时包含多个类别。

## 2. 对象与数量映射

| 我们的对象／事实 | ERPNext 真实对象／入口 | 可复用及限制 |
|---|---|---|
| 工单 | `Work Order` | 有计划、BOM、仓库、工序子表。工单状态由库存转移／制造事实驱动，不能直接当作“首条生效报工开工”的状态机。见 S01。 |
| 工序任务 | `Work Order Operation` + `Job Card` | 作业卡可以按批量拆分，一个工序不保证只有一张作业卡；不能把卡数当任务总数。见 S02。 |
| 一次报工 | `Job Card Time Log` 是 Job Card 子表，含人员、起止、完成量 | 草稿可改；提交生效单位主要是整张 Job Card。不能直接把每条时间行视为不可改的独立生效报工。见 S03/S04。 |
| 计划／理论用料 | Work Order `required_items`，从 BOM 计算 | 与 `transferred_qty`、`returned_qty`、`consumed_qty` 分开。见 S05。 |
| 领入在制 | `Stock Entry.purpose = Material Transfer for Manufacture`，`is_return=0` | 源仓减、在制仓增，同一库存体系的位置转移。不能标为实际消耗。见 S06/S07。 |
| 消耗 | `Material Consumption for Manufacture`；或 Manufacture 中原材料出库行 | 可独立记录消耗，也可与制造合并；默认生成数可能来自 BOM／已转料推算，未经人员核实不得当测量实耗。见 S07/S08。 |
| 余料退回 | `Material Transfer for Manufacture` + `is_return=1` | 生成从原在制位置回来源仓的单据，与“取消领料单”是不同动作。见 S09。 |
| 成品入库 | `Manufacture` 的成品入库行、`Work Order.produced_qty` | 与各工序完成量分别统计；不能把三道工序各 10 累加成成品 30。见 S01/S06。 |

## 3. CASE-01～07 适配矩阵

| CASE／要求 | 静态实际行为与差异 | 复用分类及最小后续范围 | 当前结论 |
|---|---|---|---|
| 01：建单时任务0／材料0，人确认生成且不重复 | Work Order.validate 在没有 required_items 时调用 set_required_items；工单提交后自动 create_job_card；取 BOM 工序时先清空 operations。原生生成时机与要求不同，清空重建也不等于业务幂等。S01/S02/S05 | 工单、BOM与明细生成直接复用候选；生成时机及结构锁局部改造，保留一个 BOM 计算入口。 | 源码差异已确认；运行未验证 |
| 01：源仓20→15，WIP＋5，三工序各10，FG＋10 | make_stock_entry 对转制造料指定 WIP 为目标；Manufacture 通常从 WIP出、FG仓入；Stock Entry 提交触发统一库存账和工单回写；工单产量从有效制造单汇总。S01/S06/S07 | 配置仓库、BOM、工序、转料基准后复用。核所有来源行和库存位置，不能只看工单状态。 | 直接复用候选；未运行数值 |
| 02：四位需求、六位输入／中间量、Q05四舍五入 | BOM 用 stock_qty/父项基数×计划量；字段精度优先、全局未设默认3位；可设置2～9位与 Commercial Rounding。MariaDB Float映射 decimal(21,9)，但 flt() 实际调用 Python float，BOM／换算／状态多处浮点计算。S05/S10 | 显示／字段精度可配置；十进制算法要求不能靠设置解决，需局部改造评估或严格实测后记录差距，禁止另造平行计算框架。Q03损耗系数的目标语义也需绑定，BOM过程损耗不能自动当原料损耗加成。 | 静态实现不满足“全程十进制”的直接复用判断；每个Q/U输入结果未验证 |
| 02：1kg=1000g，净0.0006kg；跨单位耗量一致 | Stock Entry.transfer_qty = qty×conversion_factor；领／退汇总使用 transfer_qty，但 WorkOrder消耗汇总 SUM(detail.qty)，余料查询也取 detail.qty。S07/S10/S11 | 保留原生UOM和库存账；重点检查非库存单位输入后，耗量/余料是否与库存单位一致。这里是明确风险入口，未运行前不写成已复现错误。 | 待定向运行；未知影响范围 |
| 02：V01/V02移动平均成本 | Stock Ledger存在 Moving Average 分支，按原库存值加本次入库值后除新数量，更新库存值。S12 | 估价方式配置后直接复用候选；不另写成本账。V01/V02、退料取价、舍入仍需运行。 | 源码入口已定位；数值未验证 |
| 02/07：8良品＋2不良完成，返工独立，零分母“—” | JobCard总完成量取时间行；set_process_loss 将计划−完成量自动填损耗；提交要求完成＋损耗等于计划；工序状态按二者之和完成。已读原生测试明确输入8后自动损耗2，并断言WO产量8、损耗2、状态Completed。S03/S13 | 工序汇总和顺序约束复用候选；明确良／不良输入、不良项、返工独立口径与比例展示局部改造。不可把“未报的2”自动认定为人员确认的不良。 | 关键语义差异已确认；不是 R02 M01～M04通过 |
| 03：工时、休息并集、停工／加班、预计工资 | JobCard校验起止顺序与重叠，服务端用起止差重算 time_in_mins；已读时间行只有起止、人员、完成量、工序等，无本项目休息／停工／允许加班结构；hour_rate用于工作中心运营成本。S03/S14 | 起止／重叠／服务端重算直接复用候选；本项目有效工时和预计工资规则需局部扩展。不能把工作中心成本当个人预计工资。 | T08/T09有静态相关防护；全部T运行未验证 |
| 04：重复报工、超时找回、不同合法请求均保留 | make_time_log 取JobCard后更新未结束行或追加起始行，再save；已读入口未见业务请求键和首次结果找回。框架save有文档锁/版本时间戳检查；这不是请求级幂等。S04/S15 | 复用文档保存／提交／事务边界；请求身份、重复结果找回及跨卡并发限额的适配需定向核验后局改，不能仅凭锁断言失败或通过。 | I01/I03/I04/I05/I06均未验证 |
| 04：同库存单重复过账 | Frappe区分首次submit与已提交后更新；StockEntry库存入账在on_submit；另有同工单制造数量防重复检查。S07/S15 | 原生单据状态及库存账直接复用候选；同单重复、重新建单重试、成功后丢响应分别验证。不能把“已满量时拒绝第二单”当请求去重。 | I02未验证 |
| 05：原报工10→关联冲销重报8，原事实保留 | 已提交普通字段受保护；cancel会重汇总工序；amended_from仅允许指向已取消单。制造入库已引用量时，JobCard取消要求先取消Manufacture。默认Manufacturing User仍含delete/cancel/amend；框架禁止删除submitted，但取消后可进入删除路径并按链接检查，Deleted Document留存不等于原业务事实保留。S04/S16 | 优先评估原生全取消＋修订这一路径，补原因、普通业务不可删除与幂等，避免同时新造两套冲销。仍需解决“整卡取消”与“每笔报工”粒度、10→8自动损耗2使任务仍完成的问题。 | 取消修订可复用候选，严格报工冲销需局改；未运行 |
| 06：领10/退2/净8，待审3不计；实耗未知单列 | WorkOrder领／退／耗三字段分别从docstatus=1单据汇总；返回草稿不会生效；耗量无行时写0.0。原生 consumed_qty=0 不能区分“未记录”和“明确测得0”；需按来源记录解释。S07/S09/S11 | 原库存单据与累计字段复用候选；净领/进度100%/未记录标识为必要查询或展示适配。不得把净领8填成实耗8。 | 原生区分存在；R02数量／展示未验证 |
| 06：未领退／超退／超库存／跨单／净0保历史 | 已读退料由可用料记录生成，领料存在超需求校验，工单取消检查有效库存单；但这些不足以证明所有绕过入口、重复退回及父对象删除均拒绝。S09/S17 | 优先沿用库存和单据保护；按CASE失败分支定向运行后确认是否局改，不能全局宣称不存在校验。 | 未验证 |
| 07：角色／对象／导出／AI权限 | Framework支持Role、owner、User Permission、share及controller检查；JobCard默认Manufacturing User权限宽；save检查write、submit检查submit。make_time_log本身不按登录人匹配传入employee，须结合对象权限与业务身份核对。S04/S18 | 先配置最小岗位和对象授权；ALL/DEPT/PERSON是否仅配置足够未知，必要时用框架已有扩展点局改。AI没有本轮验证入口，不能借内部get_all当授权查询。 | 机制可复用候选；非管理员越权测试未验证 |
| 07：首报开工、人工结束、路线历史及复制 | JobCard有时间行即显示WIP；WorkOrder按转料/制造推进；close_work_order检查对象write和在制作业卡，但已读入口未要求本项目差额/原因。BOM工序复制到WorkOrder.operations，提供快照基础；历史不受所有后续入口影响、复制不带事实需实测。S01/S02/S19 | 历史工序子表复用候选；报工开工时机、人工结束理由和差额局改；路线版本标识及复制保护待验证。 | 有静态差异；运行未验证 |

## 4. 关键源码依据

链接均固定至本次仓库 commit。括号内行号是实际读取范围，文件 blob 身份见 run-record；不引用动态develop作为结论。

- **S01 工单状态与产量：**[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L434)（434～560），状态看转料与制造；制造量汇总为 `fg_completed_qty-process_loss_qty`；不是工序量求和。
- **S02 工序与卡生成：**[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L586)（586～603、744～766、984～1042），提交生成作业卡，按批次拆分；BOM工序按idx复制。
- **S03 时间行与汇总：**[job_card.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/job_card.py#L202)（202～234、669～728、756～764）；[time_log.json](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card_time_log/job_card_time_log.json#L16)（16～62）。
- **S04 报工保存入口：**[job_card.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/job_card.py#L515)（515～562、1117～1125）；[job_card.json](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/job_card.json#L148)（148～166、522～573）；[base_document.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/model/base_document.py#L1054)（1054～1089）提交后字段保护。
- **S05 理论用料：**[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L150)（150～178、1220～1284）；[bom.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/bom/bom.py#L1159)（1159～1258）。
- **S06 单据与仓库方向：**[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L1632)（1632～1684）；[stock_entry.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L2072)（2072～2086、2109～2146、2170～2212）源仓负、目标仓正。
- **S07 生效／取消／工单回写：**[stock_entry.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L532)（532～588、2285～2313）；[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L1197)（1197～1208、1286～1409）。
- **S08 消耗生成依据与配置：**[stock_entry.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L2654)（2654～2789、3192～3219、1484～1510）；[manufacturing_settings.json](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/manufacturing_settings/manufacturing_settings.json#L101)（101～114、207～212）。默认backflush=BOM，material_consumption默认0；配置后可先独立消耗再制造，是否重复扣仍需验证。
- **S09 余料退回：**[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L2017)（2017～2035）；[stock_entry.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L3262)（3262～3296、3324～3363、4378～4439）。
- **S10 精度与计算类型：**[stock_entry.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L682)（682～693）；Frappe [data.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/utils/data.py#L939)（939～971、1070～1141），[meta.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/model/meta.py#L831)（831～843），[system_settings.json](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/core/doctype/system_settings/system_settings.json#L190)（190～201、556～562），[MariaDB database.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/database/mariadb/database.py#L174)（174～178）。
- **S11 耗量单位与未记录：**[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L1382)（1382～1409）SUM(detail.qty)再flt；[stock_entry.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L4442)（4442～4502）余料查询取qty及stock_uom，须重点检验非库存单位。
- **S12 移动平均：**[stock_ledger.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/stock_ledger.py#L1107)（1107～1125、1818～1855）。
- **S13 完成与损耗：**[job_card.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/job_card.py#L756)（756～764、982～1015、1049～1095）；[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L1066)（1066～1084）；[原生测试](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/test_job_card.py#L703)（703～762），静态阶段只读；后续该测试实际通过，见第6节。
- **S14 工时与成本：**[job_card.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/job_card.py#L202)（202～234、795～805、825～859）。corrective_job_card用于更正性工序成本，不能因名字含corrective就当作原报工冲销；其生成在1304～1333。
- **S15 状态与并发保护：**Frappe [document.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/model/document.py#L380)（380～431、852～946、1163～1174）；ERPNext [stock_entry.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L1143)（1143～1177）。
- **S16 更正及历史：**[job_card.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/job_card.py#L673)（673～681、766～875）；Frappe [document.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/model/document.py#L439)（439～444、1087～1128）；[delete_doc.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/model/delete_doc.py#L120)（120～184、251～273）。
- **S17 数量与取消限制：**[stock_entry.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L1257)（1257～1308）；[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L815)（815～830）。
- **S18 权限：**Frappe [permissions.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/permissions.py#L77)（77～166、211～259、327～369），[document.py](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/model/document.py#L402)（402～420、894～922）；默认角色见S04。管理员有特例，不可用于证明普通用户权限通过。
- **S19 关闭与历史：**[work_order.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L1780)（1780～1805）；工序复制见S02；[job_card.py](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/job_card.py#L1097)（1097～1108）关闭/停止拒绝改卡。

## 5. 最小运行范围与结束边界

先核运行镜像内 ERPNext/Frappe 真实版本，再用 [run-record 的已读原生测试入口](run-record.md) 做有限先导；原生测试通过也不等于 R02。优先补同一合成案例下的四组关键区别：

1. CASE-01/06：转WIP、独立或合并消耗、提交退料、成品入库分别取库存账及工单字段，确认不从原料仓重复扣。退料必须实际submit；仅生成草稿不能过CASE-06。
2. CASE-02：Q02/Q04/Q05、U01和跨单位消耗；同时核配置、服务端计算、保存回读与库存入账。先读现有权威计算入口，不为先导开发新公式。
3. CASE-05：先保存原卡10，再按原生cancel/amend走一条更正为8路径，记录原卡、修订卡、状态和剩余量；观察自动损耗2的差异；有下游则只核原生阻止取消。不要以“corrective Job Card”代替冲销。
4. CASE-04/07：在准备好普通角色后核同单重试与两个授权用户并发；当前尚未有业务请求去重、ALL/DEPT/PERSON或AI权限通过证据。

PC/手机本轮没有界面操作、扫码、弱网恢复或点击数证据；仅沿用R01已定位的原生Desk/表单入口，不声称中文现场适用。维护需同时锁ERPNext、Frappe及运行依赖；R01记录的容器默认16系不适用于本基线。首版AI-1/2/3仍是待接入能力，未取得模型／语音配置，不能因已有正常业务接口就标AI可用。

本轮静态证据已经足够筛选并限定下一步，不继续全库审计。R06比较时须保留上述差异；R07前不改产品、不重写库存、不启动B/A/Z实施卡。


## 6. 同日运行追加：只更新有实际证据的部分

完整输入、命令、原始JSON、失败尝试及限制见[run-record第5节](run-record.md)。运行对象是本机ARM64隔离站点，管理员CLI；没有UI、普通角色、客户部署或AI结论。

| 对应静态项 | 实测追加 | 仍然不能推导 |
|---|---|---|
| CASE-01数量主链 | 三工序各10，源15/WIP0/FG10，工单产出10；已提交且新连接回读一致 | 不等于人确认生成、防重、全部状态/权限通过 |
| CASE-06领退/草稿 | 领10退2，源12/WIP8；待提交领3不记库存；回读一致 | 无实耗记录不等于实耗0；未配置审批或核领料进度UI |
| CASE-02 Q02/Q04/Q05 | 全局6位+Commercial Rounding：保存需求8.3333、0.0167、0.00015；前两项符合固定期望，Q05未得到0.0002 | 不等于全程十进制；字段精度最小配置、U01/跨单位/库存及V01/V02仍未验 |
| 原生完成/损耗 | 上游定向测试通过：计划10报8自动损耗2，最后WO产出8仍Completed | 未报2不能被本项目自动认定为已确认不良 |
| CASE-04同库存单重提 | 同单submit再次返回，账条数与源/WIP数量不变 | 不是请求身份去重、并发或丢响应找回 |
| CASE-05取消/修订 | 保持卡批量10仅改完成8被拒；原卡取消后把修订卡批量设8，成功保留关联原卡，工单计划10/工序完成8且进行中 | 只是整卡原生路径，逐笔Time Log冲销、禁止原事实删除及更正重试未验 |
| CASE-06超退/重复生成 | 库存8试退9被NegativeStockError拒，脚本事务回滚恢复；二次生成退料草稿出现两行反向转移（10、2） | 尚未证明工单关联退料上限；二次生成的两行未提交，UI后处理与正确路径待核 |

原生定向测试合计4项通过，与自定义数量子集分开计数。新连接持久化回读（仅本地保留；见 publication/evidence-index.json）确认两个主链及取消/修订数据已提交；制造设置、精度与舍入恢复初值。手机、并发、普通角色、完整CASE-01～07和适配成本未完成，因此任务总表不勾选R05整卡。R06/R07、产品修改尚未开始。

## 7. 最新补证与复用分类

| 能力 | 已核实边界 | 当前分类／下一步 |
|---|---|---|
| 原生库存和显式实耗 | 领10退2、耗7对应净领8/实耗7/WIP1；U01库存换算正确 | 复用原生Stock Entry/Stock Ledger/UOM，配置独立消耗；保留单据来源 |
| 需求精度／单位汇总 | Q05工单存0.00015而库存0.0002；消耗0.5g正确扣0.0005kg，但工单汇总0.5kg | 配置＋必要计算入口改造；全程Decimal影响面未验证，不能承诺只改显示 |
| 退料生成／限额 | 二次退料生成正反两行；仓库有其他库存时本工单超额退料接受 | 改造现有净额/单位/工单关联校验，保留仓库负库存检查；不增第二套账 |
| 原生权限 | 显式Work Order白名单受测资源接口生效；辅助方法返回受限子行，默认制造岗位能写库存草稿 | 复用Role/User Permission，最小角色配置＋入口权限适配；部门自动映射/导出/AI权限未验 |
| 并发／请求重试 | 同卡版本冲突能防同次加2重复，但两笔合法+1不能全保留；跨卡出现一次死锁；查单后顺序恢复成功 | 复用事务/版本锁，绑定请求身份、结果找回及锁顺序/受控恢复；不把自动重试当万能修复 |
| 原事实／冲销 | 原生submitted改删保护可留；取消后普通账号可删原卡/时间行，审计副本另存 | 明确逐笔事实粒度及取消后的保护；整卡amend不等于每笔冲销已满足 |
| 小屏网页 | 普通工人报10提交/刷新成功；仓库角色提交既有领5成功；进行中无原生退料按钮、Stock Settings读取权限提示 | 复用Desk表单，配置＋必要操作适配；真实手机/扫码/弱网/网页退料完成未验 |

原始输入、真实ID、命令、实际/预期和限制分别见[物料](followup-material.md)、[权限并发](followup-access.md)、[小屏](followup-mobile.md)报告。R05按评估结束条件收口；全部CASE、产品修复与业务验收仍未完成。R06的统一比较和有条件选择见[选型记录](../R06/selection.md)。
