> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R07｜报工事实保留与请求并发绑定

日期：2026-10-26。范围：B08/B09及其依赖的B05/B06状态、任务关联；关联B02权限、B10～B12库存事务、B13弱网。**本轮仅静态绑定，没有修改产品、启动服务、执行数据库或新增测试。B08/B09仍为条件卡，不能据此宣称可交付或已解决死锁。**

## 1. 依据与版本

- 业务：[决策与范围](../../docs/决策与范围.md) C05；[业务卡](../../docs/任务卡/02-生产与物料闭环.md) B08/B09；[R02 fixture](../R02/fixture-spec.md) v1及[预期](../R02/expected-results.md) CASE-04/05/07。
- 历史运行：[R05权限并发补证](../R05/followup-access.md)、并发请求（仅本地保留；见 publication/evidence-index.json）、重试（仅本地保留；见 publication/evidence-index.json）、删除（仅本地保留；见 publication/evidence-index.json）、独立顺序恢复（仅本地保留；见 publication/evidence-index.json）。本轮直接复用，未重复运行。
- 选型：[R06](../R06/selection.md)：ERPNext v15.124.1 `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；Frappe v15.124.0 `f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab`；官方ARM64镜像 `sha256:4160d3c77aafb41c7770aad3daa67254a13f8750765ee83d632434ed564a4834`。
- 静态源为该基线的本地只读快照 `.evaluation/r07-sources/`。下文路径以仓库内路径表示，ERPNext文件在ERPNext维护分支修改；Frappe仅核查复用，不修改。行号为本轮快照行号，未来实现前按函数定位。
- 本轮用 `rg`、`sed`、Python `ast.parse` 读取函数、签名、调用链和测试名；没有将语法可解析算作业务测试通过。

已复现的边界必须保留：submitted卡改量和直接删除被拒；普通用户取消后可删除原卡及时间行。两人同卡各1只有一笔保留，后续提交自动loss1；不同卡各1一次死锁，顺序恢复成功不覆盖原并发失败。原生重复submit未重复计量，但没有按请求找回首次成功结果。I05/I06仍未验证。

## 2. 已有入口、粒度及派生影响

| 已核文件与函数 | 实际行为 | 复用／改动判断 |
|---|---|---|
| `erpnext/manufacturing/doctype/job_card/job_card.py:1118` `make_time_log(args)` → `JobCard.add_time_log(self,args):515` | `args`可为JSON字符串；按`job_card_id`取卡。start追加时间行，complete填未结束行的`to_time/completed_qty`，末尾`save()`；不提交整卡，无请求身份或原结果返回。 | 复用员工、工时和原表单，不能把此调用成功当一笔已生效报工。新确认动作不能继续只调用它。 |
| 同文件 `validate_time_logs:202`、`before_save:669`、`set_process_loss:756`、`validate_job_card:691` | 时间行汇总成`total_completed_qty`；保存可按`for_quantity-total_completed_qty`自动产生`process_loss_qty`；提交要求完成＋loss等于卡批量。 | 显式良品和不良输入必须改造，不能用未报完的差额冒充不良。 |
| 同文件 `on_submit:673`、`on_cancel:679`、`get_current_operation_data:861` | 按同`work_order/operation_id`且`docstatus=1`、非corrective卡汇总完成量、损耗和工时；cancel后原卡退出有效汇总。 | 优先复用一个汇总和原生submit/cancel；不新增另一套事实汇总账。 |
| 同文件 `update_work_order:766`、`update_work_order_data:825` | 写Work Order Operation的`completed_qty/process_loss_qty/actual_operation_time/actual_start_time/actual_end_time`，重算工序状态、工单作业成本及实际日期，再于859行`wo.save()`；`update_corrective_in_work_order`也于806行保存工单。 | 原生只设`ignore_validate_update_after_submit`，并没有免除工单write权限；窄角色可能无法完成派生回写，见第3.1节。冲销须核这些派生值及工时／日期回退。 |
| `erpnext/manufacturing/doctype/work_order/work_order.py:1066` `update_operation_status(self,operation_id=None)` | 工序状态按良品＋loss与`Work Order.qty`及超产设置比较，原生没有本项目独立的任务计划字段。 | “任务＝Work Order Operation”可作为单一路径候选；B06若要求不同任务计划，必须先明确映射，不得偷偷将卡批量当任务计划。 |
| 同文件 `get_status:434`、`set_actual_dates:1086` | 原生工单开工状态主要依库存转移；仅首笔报工不保证工单变为In Process。实际日期汇总可能在无有效数据时保留原值。 | B05/B08须在原权威状态入口补“首条生效报工开工”，取消后重算；不能用虚构领料促使开工。工序完成、合格成品入库和工单结束分开核对。 |
| 同文件 `on_submit:586` → `create_job_card:744` → 模块函数 `create_job_card(work_order,row,enable_capacity_planning=False,auto_create=False):1874` | 提交工单会按工单量／批量自动建计划Job Card，保存排程行。模块函数把`row.job_card_qty`或工单量写为卡`for_quantity`。 | 不能在现有全量计划卡之外无限叠加报工卡而忽略原计划卡；先做第3节前置试验。 |
| `job_card.py:153` `validate_job_card_qty` | 统计该工序全部非cancel卡的`for_quantity`，结合已完成量判断卡批量上限。 | 自动计划卡与逐笔事实会相互影响，此校验不能直接删掉或放宽来过样例。 |
| `job_card.py:808` `validate_produced_quantity`；`work_order/test_work_order.py:551` `test_job_card` | 取消后工序可支持数量不足以覆盖已制造量时抛`JobCardCancelError`；已有原生测试检查下游Manufacture阻止取消。 | 保留真实下游保护，库存逆向另走原单据；不把报工冲销当退料。 |
| `job_card.json`、`job_card_time_log.json` | 现有`amended_from`、人员和时间行；时间行只有完成量，没有业务请求键、明确不良原因及本项目预计工资的完整事实快照。 | 能复用的字段复用；缺失的请求身份、不良原因、计价来源按已确认范围最小补充，不另造事实DocType。 |

`Job Card.process_loss_qty`会参与工序数量，且库存 `stock_entry.py:set_process_loss_qty` 会取工序loss，成品行生成还会使用loss。**把字段改成“不良”文案并不等于上下游语义已正确。** 第3节试验必须证明报工良8／不良2没有形成虚构入库、扣料或合格交付10；B12仍独立校验入库与状态。

## 3. 只推进一条最小候选，先验证事实粒度

候选为：**任务沿用Work Order Operation；每次有权人员确认生成并立即submit一张原生Job Card；纠错只走原卡cancel＋amend新卡。** 不选择在一张已提交卡里继续追加可改时间行，不开发差额冲销和全冲重报两套路径，不建平行工单、库存账或事件框架。

映射约束：

1. 任务身份为`Work Order Operation.name + parent Work Order`；每张报工卡`operation_id`精确指向它，不能只用工序名称。授权也挂本道工序任务，Job Card本身不是第二套任务。
2. 本笔卡`for_quantity＝本笔显式良品＋本笔显式不良`；良品汇入原`total_completed_qty`，不良必须有输入和依据。工单计划10、任务计划10保持10；报1不能把计划改成1。多人各自提交不同业务请求，分别形成可归属的卡；不做一笔多人分摊。
3. 新确认入口在一次原生事务中完成输入、身份、当前权限／状态／剩余量检查、建卡／提交和回读；成功即生效，无主管报工待审。前台草稿和AI草稿不进入已生效汇总。
4. 显式不良优先复用原`process_loss_qty`承载，但必须限定并替换本项目确认路径的自动差额推断，禁止先把任务剩余量写入卡批量再自动推不良。零良品＋不良、良1＋不良0和良8＋不良2均是不同输入，不允许缺失不良字段自动当作已确认差额。
5. 工单`get_status`及工序状态仍是权威入口；首笔确认推进开工，任务完成依据任务计划。报工不得调用Stock Entry制造／发料，工单不得因一个工序卡Completed就结束。

**前置试验 F-RPT-01（拟验证，当前未执行）：**在一个隔离工单计划10、三道工序、按工单领料的场景中，保留工单和任务计划／路线；使用真实最小角色，操作工只有授权本道任务的报工动作权限，没有Work Order write及库存写／过账权限，记录实际角色、对象授权和登录身份。处理原生自动计划卡后连续确认良1／不良0两次，再确认良6／不良2。检查逐笔3张有效原生Job Card、父工单派生回写成功、当前工序良8／不良2、任务完成、其他任务未完成、工单在制、成品入库0；首条确认即开工，且任何一步没有主管审批。同一操作工直接改工单、改其他任务、伪造工单回写字段仍须拒绝，工单计划、路线、授权及用料不变。再由具有明确更正／cancel／submit权限、但仍无Work Order write的角色对独立良10原卡全冲并amend良8，原卡与时间行保留，净良8、任务回到未完成、工时及派生值一致。不能用管理员或R05默认Manufacturing User大角色代替这项验证。

试验前仅允许将以下三项设计落实到明确改动，不能跳过：

- 在`WorkOrder.create_job_card/prepare_data_for_job_card`和Job Card创建链选择一种计划卡处理：本项目任务保留为Work Order Operation，确认时建事实卡；原自动计划卡的排程／人员资料如何保留并不计入已生效事实，须明确在这组原生文件内完成，不能静默删除原计划资料、重设工单量，或让两套卡都占量。此处是当前未闭合的最小范围，不能凭源码推演记“可用”。
- 在`set_process_loss/validate_job_card/update_work_order_data`与B04权威数量入口确定显式不良和汇总语义；计件／计时、工资来源及工时仍按B08/CASE-03另验，不由本次数量试验代替。
- 在第3.1节范围内闭合“操作工无父工单write，但授权报工可产生限定系统派生回写”；成功、撤权、越任务、伪造派生字段及失败回滚均使用最小角色验证。

成功条件是以上输入、映射、原生派生和取消保护全部有持久化证据，且修改限定在ERPNext制造文件和既有扩展钩子。失败／停止条件：必须把卡批量偷换为任务计划、绕过原权限／原汇总、改Frappe共享保存机制、建立第二套任务／库存事实、或显式不良影响库存但无法限定适配。出现任一项即保留B06/B08/B09门槛，按R06重评相关判断；不无限追加试验或默认转自研。

### 3.1 窄角色与父工单派生写入门槛

已核源码：`JobCard.update_work_order_data:859`和`update_corrective_in_work_order:806`调用`wo.save()`；`frappe/model/document.py:_save:403`先执行`check_permission("write", "save")`。`ignore_validate_update_after_submit`只跳过提交后字段变更限制，不授予write。因此R05大角色成功不能证明本项目最小操作工能报工；本轮未实测窄角色，不预报具体HTTP错误或成功结果。

已存在系统派生写模式可作为局部参考：`WorkOrder.update_production_plan_status:562`按已提交工单汇总产量，对取自数据库的Production Plan对象设置实例级`ignore_permissions`，再调用原派生方法；`production_plan.py:update_produced_pending_qty:568`更新确定行的产量／待产量，`update_status_and_bin_qty:578`更新派生状态。另有`WorkOrder.update_work_order_qty:482`按库存单汇总后`db_set`指定字段。这证明上游存在系统内部派生写，不证明已经提供适合本项目的字段级授权能力，也不授权复制成泛用绕权接口。

**唯一拟候选仍保留原Job Card→工单计算链和Document保存：**授权确认／更正入口检查当前人、本道任务及动作，先锁同工单，从数据库重新取得工单，按已生效卡重算现有派生量。仅在这个已锁、服务端新取且不可接收客户端工单载荷的Work Order实例上，允许一次受限系统派生保存；必要时局部使用原生`wo.save(ignore_permissions=True)`，并在`finally`恢复该实例原flag。不得设置全局`frappe.flags.ignore_permissions`、切换管理员、给操作工全部Work Order write，或把忽略权限扩散到Job Card确认、库存和其他文档。这里新增的是服务器对已授权报工的窄派生权限，仍须由试验证明安全；不是原生现成功能。

该局部保存必须与B02/B05/B06保护合并：在Work Order控制器拟`before_update_after_submit`按原持久化文档核差异，并核第5节服务器上下文的工单／本道任务／动作，**只允许**本道工序`completed_qty/process_loss_qty/actual_operation_time/actual_start_time/actual_end_time/status/actual_operating_cost`及由它们确定的父工单`actual_operating_cost/total_operating_cost/actual_start_date/actual_end_date/lead_time/status`，加原生修改时间／操作者等审计元数据。任务和原事实的改删保护继续执行；不得因系统派生上下文而跳过整份父文档的保护。

工单计划、路线／顺序、用料、任务授权、人员、其他任务事实、`workstation/hour_rate`、计划成本、库存产量／耗料和库存单据不在此允许集合。原`update_work_order_data`可能根据卡改工作站／时费率，`calculate_operating_cost`会重算计划成本并可能补空时费率；必须在本项目确认路径沿用已确定的任务配置，不能让报工载荷改变这些字段。若上述原链实际产生白名单外差异，试验应明确拒绝并定位必要调整，不自动扩大白名单或改用SQL跳过保护。`is_corrective_job_card`是原生返修成本分支，不等同cancel/amend纠错；本候选确认接口不允许用户开启它，其成本字段也不因此放行。

验收须证明：无Work Order write者的授权报工和更正可更新这些派生值；同身份直接PUT工单、改权限／计划／其他工序、伪造上下文或混入客户端工单字段均失败；入口权限撤销或更正新卡失败时整个事务回滚。若必须放开整单权限、扩大字段直写或绕开历史保护才运行成功，此候选不通过，B08/B09门槛继续保留。

## 4. 请求身份、结果找回与全冲重报

现有Document `modified`版本检查、Job Card文档名、时间行名和HTTP请求标签都不能单独回答“这次业务提交是否已成功”。**拟新增最小持久化为现有Job Card字段，不新增通用请求表：**

| 拟新增／已有 | 用途与限制 |
|---|---|
| 拟`report_request_id`，Data、数据库唯一、不可复制 | 标识一次人工确认。客户端首次点击前保存并在超时／刷新重试时沿用；服务端验证格式和归属。普通第二笔即使数量相同也必须新ID。唯一约束配合事务，不能只先查再写。 |
| 拟`report_payload_hash`，服务端计算、不可复制 | 绑定确认人、任务、良／不良、工时、原因及有关计价输入。同键同内容找回；同键改量／换任务拒绝，不能覆盖原卡。哈希不代替完整原记录，规范化依B04。 |
| 复用`owner/creation/time_logs/employee`和`amended_from` | 原事实及修订来源。`modified`不是首次确认时间；人员和时间仍使用原事实字段。amended_from只表关联，不自动保证一个原卡只有一条有效更正。 |
| 拟`correction_reason`及必要确认来源字段 | 更正新卡必填原因，记录当前操作者／时间、原卡ID；原卡事实字段保持。是否需独立确认时间字段按现有creation与业务时刻差异确认，不能拿当前modified伪造。 |

拟新增接口放在**已有**`erpnext/manufacturing/doctype/job_card/job_card.py`中，名称是计划、当前不存在：

- `confirm_production_report(work_order, operation_id, request_id, good_qty, rejected_qty, employee, from_time, to_time, ...)`：参数最后由B08已选字段收敛，不接受客户端传`docstatus`、绕权flags、计算汇总、工单状态。最终完整签名是B08实施前门槛；上面不是可调用的现有接口。
- `get_production_report_result(request_id)`：先检查当前登录身份及该任务read权限；同键命中返回原Job Card ID、首次确认量、当前docstatus及后续更正引用。取消后重试旧请求仍找回旧结果和当前取消状态，不能再新增一笔，也不能泄露别人请求。
- `correct_production_report(original_job_card, request_id, good_qty, rejected_qty, reason, ...)`：当前有更正／cancel／submit权限者，锁原卡关联的同一工单；核依赖与可冲量，cancel原卡、复制为新卡并设置`amended_from`、新的唯一请求ID和原因，清除复制来的旧请求身份，正常submit。一个事务成功或全部回滚；本轮只绑定全冲重报。零量纯冲销列为未覆盖业务点，不阻塞本轮全冲重报绑定，也不得据此暗增另一套模式。

更正请求重试先找新卡结果；同原卡不同请求同时更正仅一笔能生效，另一笔返回当前状态冲突。原卡已取消且无法证明由本次请求完成时，不能再次冲销。不得把普通cancel当无理由冲销入口；需在服务器端限定更正上下文并核权限，不信任客户端Document flags，也不靠隐藏取消按钮。

最小恢复策略：不在业务事务中catch所有异常后继续写或返回成功，不在发生死锁的连接中直接续跑。原生异常让请求回滚；前台显示中文“未完成／结果待确认”，使用原请求ID发新请求查结果。命中即返回原结果；确认为不存在、状态仍允许时才按同ID重新提交一次。有限恢复后仍失败则停留明确失败／待处理状态，不自动换ID、改量或无限重试。I05才能证明丢响应恢复成立。

## 5. 锁与事务：覆盖同工单，而不修改Frappe数据库层

**当前源码顺序，不是实测锁环：**

1. `Document._save:380` → `check_if_latest:852` → `load_doc_before_save:1162`用`frappe.get_doc(...,for_update=True)`锁当前Job Card及子行；资源PUT更早在`api/v1.py:update_doc:49`锁卡。
2. `JobCard.validate` → `set_status` → `update_status_in_workstation:1110`写Workstation。
3. `on_submit/on_cancel` → `get_current_operation_data`先汇总，再读Work Order；`update_work_order_data`中`wo.save()`才进入工单及子行版本锁。
4. 已有死锁堆栈失败在第2步Workstation写入。没有数据库死锁图／双方全部锁记录，**不能断言已证明完整锁环，也不能宣称统一锁已消除所有死锁**。

拟协议：对本项目同工单报工确认／更正、工单计划和任务结构改变，以及关联Stock Entry领／退／耗／成品的submit/cancel，在任何卡、库存单或工作站写锁之前先获取该Work Order行锁；再重读当前状态、任务归属、权限和剩余量；之后沿原生文档事务。以已核`frappe.db.get_value("Work Order", name, "name", for_update=True)`或等价的原API取得锁，非缓存读取；不另建锁表。涉及多个工单的现存路径若出现，须先明确对象并统一排序；首版报工一次只关联一个工单，不因此新增多工单批量功能。

注意：**仅在`JobCard.before_submit/validate`加工单锁太晚**；它们之前原生已锁卡。选择更窄的方案：专用确认／更正方法先检查权限、先锁Work Order，再进入原生保存；通用PUT/submit/cancel虽然可能已锁卡，但在制造控制器的早期保护中立即拒绝，不再取Work Order／Workstation写锁。因此旁路不是转到另一个取锁顺序继续执行。不要修改`frappe/model/document.py`、`frappe/api/v1.py`或数据库实现，不新增全站URL黑名单／before_request拦截层。

早期保护的真实位置为`JobCard.before_validate:138`（在当前`validate_time_logs/set_status`前），并拟在同控制器补`before_cancel`和`before_update_after_submit`；其调用分支已核`Document.run_before_save_methods:1130`。Resource直接操作时间子行不一定先走父卡保护，故现有`JobCardTimeLog`控制器也需早期保护；删除走各自`on_trash`。保护在未获合法命令上下文时只读必要归属并拒绝，不先取得工单写锁。合法草稿／计划卡操作的具体范围随F-RPT-01确定，不借此禁止所有草稿操作。

命令上下文复用已有请求局部存储：`frappe/__init__.py:191`的`flags = local("flags")`和`init:211`的`local.flags`；`BaseDocument._reserved_keywords`含`flags`且`set`忽略此键，客户端文档字段不是服务器`frappe.flags`。拟由专用方法在权限／对象／动作检查、工单锁成功后设置仅含本次工单／任务／动作／请求ID的制造上下文，调用原生Document，再在`finally`恢复旧值；控制器同时核上下文与当前文档相符。上下文不是角色授权、不是通用绕权flag，不设置全局`ignore_permissions`，不得由外部传入或持久化。第3.1节单个父工单实例的限定派生保存是唯一拟评估的局部例外，不能扩到报工或库存事实入口。直接脚本／导入／后台调用也须拒绝或显式走同入口；是否覆盖全部本项目必需调用仍需用例证明。

此协议的实施前门槛：与B10～B12合并列出全部实际生产写入口，证明原生界面正常业务可到同一链、通用入口无提前反向取锁、同工单库存与报工并发没有部分成功。不同工单共享Workstation、库存Bin／账及后台任务仍需相关定向用例，不能由同工单串行化推成全局无死锁。若为覆盖旁路需要广泛改Frappe，应按第3节停止条件重评。

原生事务可复用：`frappe/app.py:136`请求异常后在finally回滚unsafe请求；`sync_database:451`在成功unsafe请求后commit。没有读到本请求自动重新执行。新方法不手动中途commit；数据库唯一键、原事实、派生汇总及更正新卡同一次提交，结果查询使用新请求。测试前后须证明没有卡成功／工单失败、原卡已冲／新卡失败等残留。

## 6. 改写、删除与旁路清单

| 实际入口 | 已核调用及保护要求 |
|---|---|
| `frappe.client.save(doc)`、`set_value(doctype,name,fieldname,value=None)`、`bulk_update(docs)` | 均进入Document保存；set_value对子行取父文档后改行。bulk_update逐单处理，不能当批次原子事务。测试直接改原卡数量、员工、时间、请求键、`amended_from`；提交后及取消后均不能覆盖事实。 |
| `/api/resource/...` POST／PUT及`frappe.client.insert/insert_many` | 允许建草稿不等于允许伪造已生效报工／amended_from。PUT先锁目标，child PUT还会另存父文档；必须覆盖直接时间行、工序子行、伪造父关联，不能仅封表单按钮。 |
| `frappe.client.submit/cancel`；`frappe.desk.form.save.savedocs(doc,action)`和`cancel(doctype,name,workflow_state_fieldname=None,workflow_state=None)` | 原生提交／取消入口都可触发事实变化；保护须同时落在制造入口及控制器。savedocs可排队提交；报工确认不能以后台排队已接收冒充立即生效。Job Card当前元数据未声明queue_in_background，配置改变需重验。 |
| `frappe.handler.run_doc_method`、Resource `execute_doc_method` | 可调用白名单Document submit/cancel等；仍需同一状态／权限／上下文保护，不能漏掉方法调用形式。 |
| `frappe.client.delete(doctype,name)` → `client.delete_doc:528` | child删除会取父文档remove后save；原生submitted／cancelled状态保护可复用，但必须实测子行入口。 |
| `api/v1.py:delete_doc:66` → `frappe.delete_doc` | 与client child删除不同，该入口源码仍标child handling TODO，直接进入删除逻辑。应在Job Card Time Log控制器／doc_events on_trash检查父卡历史，不能只依赖父save。 |
| `frappe.desk.reportview.delete_items:617/delete_bulk:631` | 逐条`frappe.delete_doc`，每条成功立即commit；超过10项进后台，失败条可再次尝试。已生效／已取消事实的on_trash拒绝必须在这里同样生效；测批量、后台，不把部分拒绝当整批原子回滚。 |
| `frappe/model/delete_doc.py:23/218/251` | 原生拒submitted，但允许取消态继续；删除父表直接删所有子表，子行不会逐个走父级保护。Job Card与Work Order层均需历史关系保护；Deleted Document JSON不是业务原事实。 |
| 父Work Order删除／取消、Work Order Operation删行、复制／修订 | `operation_id`在Job Card里是Data，并非Link，不能指望普通Link检查保护工序子行。B05/B06在父文档保存／on_trash核任何历史已生效卡（含cancelled），有历史就拒绝破坏关联；直接Resource工序子行写／删还需现有`work_order_operation/work_order_operation.py`控制器补早期guard／on_trash（当前只有类型声明和pass），不能假定总会经过父保存。复制不能复制报工、请求ID或库存事实。 |

拟允许ERPNext文件：`job_card/job_card.py/.json/.js/test_job_card.py`、`job_card_time_log/job_card_time_log.py/.json`（若子行保护需要）、`work_order/work_order.py/.json/test_work_order.py`、`work_order_operation/work_order_operation.py`、已有`erpnext/hooks.py`及ERPNext中文翻译文件；具体字段用现有DocType元数据／原迁移机制，不能只运行不可复现的现场手改。B02权限函数、B04计算入口和B10～B12库存文件由各所属卡维护，本卡调用，不复制实现。Frappe上述路径只作已核依赖，不在允许改动清单。

原事实保护至少比较工单／任务关联、人员、业务时间、良／不良、工时、计价依据、原因及请求身份。允许原生cancel造成docstatus与审计时间变化，不能借cancel改写上述原事实；新正确值仅在amend新卡。无事实关联的草稿仍按权限处理，不能为了保护历史禁止所有合理草稿操作。

下游处理：先用原生链接／`validate_produced_quantity`查真实Manufacture和工序依赖，已入库或后工序受影响时返回具体阻挡与原单据ID；由有权限人员按逆向顺序处理原库存／后工序单据后再更正。报工入口不自动取消已审批库存、不凭空生成退料，也不以负库存掩盖错误。本轮没有验证这条完整逆向链。

管理员数据库SQL、`ignore_on_trash`、force删除、批量事务删除工具和迁移脚本可绕过普通业务保护。普通岗位不得获得这些管理入口；本绑定不承诺抵抗数据库管理员破坏。若交付保留任何可由业务角色触达的直写／删除工具，B02/B09必须纳入测试后才算覆盖，不能标“全部入口已安全”。

## 7. 验收与真实命令

以下名称均为**拟新增测试**，当前不存在；放入已有`erpnext/manufacturing/doctype/job_card/test_job_card.py`，工单父级结构测试放原`work_order/test_work_order.py`。沿用已有测试设施，不新增依赖或产品故障开关。并发HTTP应复用既有探针的屏障／请求时间／新连接回读方式，但改为新确认接口；原R05探针不修改历史结果，不可直接当新功能测试。

| CASE／拟测试名 | 输入、动作及必须取证 |
|---|---|
| F-RPT-01／`test_report_batch_fact_preserves_task_plan`、`test_report_minimum_role_updates_only_derived_work_order_fields` | 第3节真实最小角色无Work Order write，一工单三工序、连续1＋1＋(6良2不良)，计划不变；第一笔开工、三笔立即生效，父工单仅限定派生字段回写；良8／不良2／入库0，工单不因一道完成而结束。直接改工单、越任务、伪造派生字段／上下文均拒绝；同时观察自动计划卡、排程和卡批量上限。 |
| I01／`test_report_request_replay_returns_original` | 任务10／有效8／余2，同键K-01良1重复；一笔有效1、净9、余1，返回同卡；相同内容新键是另一笔，同键不同内容拒绝。另测取消后的旧键及越权查询。 |
| I02／库存所属卡 | 库存ST-01出2重复过账，来源20→18，仅一笔；由B10～B12验证和提供证据，B09不复制库存实现或把submit冲突当完整防重。 |
| I03／`test_report_concurrent_excess_is_rejected` | 两个普通授权身份，两个独立HTTP连接、不同键，余2各报2；实际请求区间重叠，净增只能2；另一方明确冲突且无残留。同任务不同卡也测，不能只测同卡timestamp。 |
| I04／`test_report_concurrent_distinct_requests_both_apply` | 余2各报1，不同键，净增2、两张事实卡；无自动不良，不能把第二笔去重。记录首次并发和恢复各自结果，不能覆盖首次错误。 |
| I05／`test_report_committed_response_lost_recovers_result` | 在可观察commit之后阻断响应，保留原键重试／查结果，回到原卡，量一次；保存提交时点、阻断点、原ID与新连接回读。不能用延迟客户端读取冒充已证明服务端commit时刻。 |
| I06／`test_report_failure_before_commit_rolls_back` | 测试工具在Job Card写入／工单回写之间及更正cancel后、新卡submit前分别抛可观察错误；检查无部分新事实／汇总／库存变化，同键重试后最多一笔。用测试mock或测试网络设施，不往产品加故障开关。 |
| CASE-05／`test_report_cancel_amend_preserves_original` | 独立有效良10→全冲10＋新良8，原因“录入错误，实为8”；原ID、原量、原人员／时间／工资来源保留；新卡amended_from可查，净8／余2，状态、工时、成本、实际日期一致。重复更正不再减量。 |
| CASE-05／`test_report_history_rejects_all_mutation_paths` | 上节普通PUT、client save/set_value/bulk、直接时间行、submit/cancel方法、普通／批量／后台delete；原卡submitted及cancelled均核，整个时间表替换与改parent也核。拒绝后从独立请求查明细，不只看报错。 |
| CASE-05／`test_work_order_history_blocks_operation_or_parent_delete` | 含已冲销原卡的父任务删行／父工单删或改关联拒绝；净量0不能解锁历史删除；无事实草稿正常操作作为正例；复制不复制事实。 |
| 下游／`test_report_correction_requires_downstream_reversal` | 有Manufacture或后工序事实时更正拒绝并说明依赖；人工按原生逆序解除后再更正；库存账、净领料与实耗来源分别回读，没有自动退料。 |
| 恢复／`test_report_deadlock_retry_uses_same_request` | 受控冲突／死锁使事务回滚，随后新请求先查同键，再显式恢复；无假成功、无无限循环、无新键重复计量。不同工单共享工作站另测；首次失败和恢复成功分列。 |

HTTP并发测试名称是待实现的测试场景标识；单进程Bench单测不能自动证明真实并发。普通账号与管理员断言回读分别记录用途。每项保存版本、输入、fixture、环境／时区、操作者、请求ID、发送与响应时间、事务边界证据、HTTP返回、前后有效卡数／工序／工单／库存及预期。中文界面要显示良品、不良、确认即生效、原记录／更正关联、待确认／失败状态；英文状态字段可保留内部枚举，不得只改中文标签掩盖业务差异。

**已核实的命令语法与已有测试入口，以下为后续执行说明，本轮未运行：**

执行位置为B01新隔离测试环境的Bench目录，站点统一为`xgd-test.localhost`；**该站点当前未建立**。B01先绑定实际Bench目录、固定Frappe版本、包含本次改动的ERPNext维护分支提交及实际挂载／安装源码，记录版本后再执行。不得用仍运行旧源码的镜像检验新实现，也不得在R05旧站点执行实施回归；R05环境、结果和脚本仅作为历史证据与测试设计参考保留。

```bash
# 在B01新隔离环境的实际Bench目录运行；站点未建、改动后源码未绑定时不得执行。
bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.job_card.test_job_card --test test_job_card_proccess_qty_and_completed_qty
bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --test test_job_card
```

原生`test_job_card_proccess_qty_and_completed_qty`的拼写确为`proccess`，它检验自动loss原生语义；改造后须区分仍适用的原路径和本项目新明确输入，不为通过测试保留错误口径。`test_job_card`检查下游制造阻止取消。二者历史已通过，不因本轮写文档重跑。

以下是**未来测试实现后的命令**，当前不得报告为可通过：

```bash
bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.job_card.test_job_card --test test_report_batch_fact_preserves_task_plan --test test_report_minimum_role_updates_only_derived_work_order_fields --test test_report_request_replay_returns_original --test test_report_cancel_amend_preserves_original --test test_report_history_rejects_all_mutation_paths --test test_report_failure_before_commit_rolls_back
bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --test test_work_order_history_blocks_operation_or_parent_delete
```

命令语法来源为已核`frappe/commands/utils.py:757–831`（支持重复`--test`、`--module`、`--app`）；B01的新环境启动／源码挂载命令尚未建立，不能照抄R05旧Compose路径冒充改动后验证入口。并发与断响应的最终脚本路径和完整CLI必须在相应测试文件存在时补齐，并明确只连新隔离站点；当前复用证据是 `.evaluation/r05-erpnext/probes/access_http.py`，其旧接口／旧夹具不能冒充新接口验证命令。本轮没有创建脚本、建立站点或启动服务器。

## 8. 本次绑定结论

已有入口、删除旁路、原生锁先后、请求身份缺口和一个事实承载候选已定位。原生Job Card／cancel-amend仍是优先复用方向，未证明逐笔语义及全部旁路可以在允许范围收敛；F-RPT-01的计划卡／任务映射、显式不良下游影响、最小角色与受限父工单派生写入，以及专用入口前置工单锁的覆盖仍是明确门槛。

因此本报告支持根任务将相关卡写成“真实位置已绑定，前置试验／依赖未满足”；**不支持将B08/B09直接写成可开工或已通过**。需要的局部验证已限定，不启动无边界研究。没有人天、费用、稳定性发生率或节省比例结论。
