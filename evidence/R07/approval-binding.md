> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R07｜生产工单审批复用、入口与最小范围

> 本页保留此前R07静态阶段记录。2026-10-27后续已按用户新授权执行B19，真实运行和修补见[B19记录](../B19/run-record.md)；本页“未实施/未运行”指当时状态。

日期：2026-10-27（北京时间）。授权：核查与更新计划/证据，**不写审批产品代码、不启用Workflow、不运行业务测试**。C10业务规则由本轮用户回答确认，唯一决策入口在[决策与范围](../../docs/决策与范围.md)。本页为原R07/B19的绑定证据，不另起任务表。

## 1. 结论及证据等级

采用建议：**复用Frappe原生Workflow、权限、Version、Comment、Workflow Action及原工单网页；在ERPNext制造业务层补必要的动作入口、执行门槛和记录保护。** 不重写引擎、不改Frappe、不增加第二套工单/审批数据库。只配置目前不足以证明满足本项目；具体静态缺口见第3节。

本轮实际完成：固定源码阅读、Git blob身份比对、真实函数/字段定位、五项目有限比较、业务确认和验收绑定。未读取站点当前Workflow配置，未创建角色/流程/单据，未启动Docker或调用业务API。**源码存在不代表本机已配置、运行通过或客户可用。** G1数量、G2逐笔报工/最小岗位、G3并发仍未通过。

主底座：ERPNext `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e` / v15.124.1；Frappe `f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab` / v15.124.0。ERPNext阅读对象是`.development/repos/erpnext`，含此前B02/B10六文件补丁；本轮前后补丁SHA256须保持`221937fbf2f011d04012aa6e0a602a982d65edb5e9a72b7b53f40060322ec5d3`。Frappe使用既有只读快照及本轮固定提交补读，文件/来源/哈希见[源码登记与静态核对](approval-source-check.json)。

## 2. 五项目实际核查与取舍

| 项目/固定commit | 本轮已查位置与事实 | 本次取用方式及限制 |
|---|---|---|
| ERPNext/Frappe（上列版本） | Frappe `model/workflow.py`、Workflow控制器与配置、Workflow Action、表单workflow.js、Version/Comment；ERPNext Work Order/Job Card/Stock Entry | **配置后使用＋局部改造**。沿用现有Python/Frappe数据与界面，无新增审批引擎。ERPNext GPL、Frappe MIT沿用[R01许可记录](../R01/license-inventory.md)，不等于全依赖许可认证。 |
| [快格云](https://github.com/kuaigeyun/kuaigeyun-mes/blob/32c46b01c1881863f4ced2db9412a4a9a68b7902/riveredge-backend/src/apps/kuaizhizao/services/document_action_policy/work_order.py) `32c46b01c1881863f4ced2db9412a4a9a68b7902` | `release_allowed`在`audit_required`时区分待审/驳回/已通过；撤回区分已有作业及下游单据（113–145行） | **借鉴规则和反例**：审核状态与执行放行分开，已有事实不能当空单撤回。只核该策略文件，未跟完全部API调用链、未运行；不将条件开关当全产品必审证据。不复制依赖其模型的规则引擎。固定LICENSE为Apache-2.0；README仍提示预览、勿正式生产。 |
| [OpenMES](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/app/Services/WorkOrder/ChangeRequestService.php) `b952915bddb2120737f10a730a1e45b1d162c47e` | `submit/approve/reject/apply`记录原因、处理人和时间；apply在事务内重读加锁并生成变更版本（149–189、216–298行） | **借鉴变更留痕及重新校验的设计**。这是生产变更申请，不等同本项目执行前两级审批。沿用R01核心AGPL及模块边界；不复制PHP服务、不引入其批次/快照模型。未运行。 |
| [qcadoo](https://github.com/qcadoo/mes/blob/94fd649003287b73a46e3ad1340eb3b4ddbb5f30/mes-plugins/mes-plugins-orders/src/main/resources/orders/model/orderStateChange.xml) `94fd649003287b73a46e3ad1340eb3b4ddbb5f30` | `orderStateChange.xml`有源/目标状态、处理结果、时间、worker、原因与日期变更；`OrderState.java`有pending/accepted/inProgress等状态 | **借鉴留痕字段与状态分离**。状态名称不证明两级岗位审批。所读文件头AGPL-3.0-or-later，README仍区分商业功能；未核商业源码、未运行，不移植Java状态框架。 |
| [t3rik](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/t3rik-mes/src/main/java/com/t3rik/mes/pro/controller/ProWorkorderController.java) `8a40bfe241178c00394cc8011b6bfee1b3a12655` | `edit/remove/doFinish`有动作权限与操作日志；edit改产品/数量时重建BOM明细，doFinish改工单及任务状态（121–155、243–265行） | **借鉴中文动作命名和权限拆分**。所读控制器未给出本项目两级审批完整证据；不宣称全仓没有审批。沿用R01主仓Apache-2.0及依赖待项；不复制Java控制器、不过度重核其他模块。 |

后四者本轮只作设计/用例参考，没有复制进产品源码。不同技术栈不是版权禁止；本次不移植的理由是当前底座已有相应构件，移植这些依赖各自模型的服务会扩大集成范围，尚无必要性证据。未量化成本或节省比例。

## 3. 原生可复用能力与明确缺口

F路径相对Frappe仓库；E路径相对ERPNext仓库内`erpnext/`。行号绑定本轮登记的实际文件。

| 能力 | 已核入口/行为 | 复用判定、边界 |
|---|---|---|
| 状态、角色、条件和动作 | F `model/workflow.py:get_transitions`39–72、`apply_workflow`99–154；`workflow/doctype/workflow/workflow.py`创建状态字段、校验docstatus | **配置复用**。独立`workflow_state`表示审批；草稿/待审核/待签批/退回/终止均docstatus=0，最终批准才=1；取消=2。不能把生产`status`改为审批状态。 |
| 原表单/列表/中文动作 | F `public/js/frappe/form/workflow.js`111–135调用原生审批；Workflow JSON中`override_status`实际标签是Don't Override Status | **复用页面，局部接动作**。将`override_status=1`作为保留生产列表状态的配置建议；另显示中文审批字段。PC/手机仍需实测，不按文件存在称手机通过。 |
| 单据/角色/对象权限 | F `model/workflow.py`52检查read，66–70检查角色条件；E `setup/doctype/department/department.json`有parent_department/company，Employee已有user_id/department | **复用＋补本项目规则**。用Department表达车间/班组，Work Order缺班组归属时只补一个Link字段；沿用B02的公司、班组和仓库授权，不新建组织模型。全厂指本公司工厂，不等于全站所有公司。 |
| 自批、普通保存/直接提交 | F `apply_workflow`116调用`has_approval_access`，225–226仅比较owner且Administrator例外；`validate_workflow`170–218未调用该自批函数；`set_workflow_state_on_action`366–380按docstatus选状态；Document `_validate/validate_workflow`635、687–695 | **需局部业务校验**。原生开关不等于发起/审核/签批三人分离。静态调用链存在与按钮不同的直接save/submit路径；尚未运行反例，不宣称已实测越权。审批角色、真实发起人、当前环节、三方分离须在制造控制器覆盖。 |
| 旧页面/旧轮次 | F `apply_workflow`101–102从数据库重新加载，不比较客户端提交的modified；入口参数只有doc/action | **需工单专用薄动作入口**：接受用户看过的版本，锁定同一工单并重读核对，再调用原生apply_workflow；防止退回重提后旧页面批了新依据。原生重读有价值，但不是“批准本人看过的版本”的证明。与G3共用工单先锁，不另造锁框架。 |
| 待办及经办人 | F `workflow_action.py:process_workflow_actions`、`update_completed_workflow_actions_using_role`写completed_by/modified；`create_workflow_actions_for_roles`按角色建待办 | **复用**。按角色待办仍需核对象/班组可见性。其`on_trash→clear_workflow_actions`可删除工单待办；F `model/delete_doc.py:delete_dynamic_links`461–468还会删除Version/Comment关联，不能把待办表当不可删除的唯一历史。 |
| 修改痕迹及原因 | Work Order原JSON `track_changes=1`；F Document `save_version`1315–1346、Version `set_diff`保存字段变化；apply_workflow152加状态Comment | **复用Version＋Comment并补原因和保护**。原生状态Comment只写状态；Version是差异，不是完整依据快照、也不是不可删除承诺。真实审批动作补中文原因/前后状态/依据版本，保护原工单及关联历史。不得只留“最后审批人”覆盖全部历史。 |
| 流程启用与历史单据 | F `workflow.py:on_update→update_default_workflow_status`73–89给状态空白的既有单据按docstatus回填 | **必须做启用前检查**。不得将既有submitted工单静默补成“已批准”。试点只接新单；保留旧测试单，在核对激活影响前不在共享已有单据站点直接保存流程（on_update并非只在激活时运行）。最小配置候选是把首个docstatus=1状态设为无执行权限的“存量待核”，正常新单通过显式转换进入另一“已批准”状态；此隔离标签不是批准或历史迁移，先由V09验证，失败就停止配置，不清空旧数据。 |
| 外部提醒候选 | F `integrations/doctype/webhook/webhook.py:enqueue_webhook/get_webhook_data/log_request`支持JSON模板、HTTP超时/有限重试/请求日志 | **待渠道协议核查**。默认企业微信单一渠道预案，客户部署前确定。此实现检查HTTP状态，但没有证明识别目标平台业务失败码，且日志存url/headers/data；不能照搬带密钥URL到公开日志。本轮无发送。 |

## 4. 审批与执行的真实入口

| 业务入口（现有） | 已核行为/缺口 | B19允许接入与其他卡归属 |
|---|---|---|
| E `manufacturing/doctype/work_order/work_order.py:WorkOrder.validate`150–178、`before_submit`583、`on_submit`586–603、`on_cancel`605–609 | before_submit建序列/批次；on_submit更新计划/预留并创建Job Card。批准触发提交有这些副作用，但不是报工或库存过账 | 在原生命周期补审批状态、变更与取消边界；直接Resource/Desk/client保存提交同样受限。保留原生提交事务。自动全量Job Card与逐笔方案冲突仍归B06/G2，不在B19另写生成器。 |
| 同文件 `make_job_card`1764、`create_job_card`1874；WorkOrder `create_job_card`744 | 能建立任务/Job Card | 批准前不允许下达可执行任务；批准后允许待执行准备。B19只放行门槛，任务粒度/派工仍归B06。 |
| E `job_card.py:make_time_log`1118→`add_time_log`515→save；`validate`141、`validate_work_order`1097；`on_submit`673 | 当前validate_work_order只拒Closed/Stopped，并非检查审批；计时本身会保存 | 在既有保存和生效入口复用同一批准判定，覆盖计时/报工/手工建卡，不能只保护按钮。记录/冲销/岗位派生回写仍归B08/B09/G2。 |
| E `work_order.py:make_stock_entry`1632、`make_stock_return_entry`2017；E `job_card.py:make_stock_entry`1195 | helper生成库存草稿，不等于正式过账 | 源对象read/目标create归B02；批准前执行放行与库存正式动作再查当前状态，不能把草稿生成时校验当提交校验。 |
| E `stock/doctype/stock_entry/stock_entry.py:validate`242、`validate_work_order`969、`on_submit`532、`on_cancel`556、`update_work_order`2285 | update_work_order现有检查submitted/Stopped；on_submit先写库存账再更新工单，取消顺序不同；未检查本项目审批依据 | B19仅补与生产工单关联的准入；业务事实、库存账、数量和锁序仍沿B10–B12/G3。保留原事务回滚，不能把“先写账”推成已发生部分提交。停止新增执行后，退料/冲销的合法纠错路径须区别处理，不能一刀切封死。 |
| E `WorkOrder.get_status`434–460、`update_status`421；JobCard `update_work_order_data`825 | 原生领料可把状态推为In Process，与“首条有效报工才开工”不同 | 差异仍归原B05/B08/G2；B19不得把批准或领料当已开工，也不在审批卡重写产量/状态计算。 |
| E `work_order.js`既有add_custom_button；F `Workflow Action/Comment/Version` | 有原生表单/时间线/待办 | B19局部接中文审批动作及版本/原因输入；B13负责手机操作验收，B16负责权限一致的记录/查询。不新建审批前端。 |

## 5. B19最小改动清单（拟实施，本轮零实现）

1. **一套原生流程配置**：Workflow/State/Transition/角色权限；本轮C10确定两级串行，不启用车间主管额外审批。复用F `utils/fixtures.py:export_fixtures/sync_fixtures`携带配置；拟新增E `fixtures/`中仅命名过滤后的本流程/必要Custom Field配置，E `hooks.py`只注册限定fixtures或相关doc_events。不得导出User、业务单据或凭据；保存流程会回填旧单，激活与历史处理先验证。
2. **原Work Order上的最少数据**：`workflow_state`由原生创建；拟新增`production_team`（Department Link）、`approval_requested_by`和`approval_reviewed_by`（User Link、仅服务端写）、`approval_note`（本次原因）。历史使用Version/Comment，时间/经办人不重复建一套表。已有执行后新单的关联拟用`previous_work_order`（Work Order Link）；`amended_from`只用于原生取消修订，不伪装未取消原单的修订。字段名均为拟新增，本轮未创建；确认只缺上述字段后才落地，不增加通用字段平台。
3. **一个工单专用薄动作入口**：拟在现有`work_order.py`新增`apply_production_approval(work_order, action, expected_modified, reason=None)`，仅为当前流程绑定身份/版本/原因/原子记录，实际转换继续调用原生`frappe.model.workflow.apply_workflow`。由服务器读取当前用户与记录，客户端不能提交已审核人/批准标志或可信flags。同一事务按工单先锁→重读→验证→原生动作→留痕；不手动中途commit、不吞异常。WorkOrder控制器同时拒绝未经该业务边界的状态/依据改写；草稿仅发起人可编辑，审核/签批角色即便因原生save需要基础write也不能直接改业务依据，普通操作工不因此获得他人工单结构写权（需B02正反例）；原生按钮/批量/通用API/后台方法不能形成第二条宽松通道。原页面只替换本工单的动作调用，不覆盖所有DocType的全局审批API。
4. **一个权威批准判定**：放在同一制造业务位置，供上述Job Card和Stock Entry关联入口复用；权限沿用B02，不在每张卡复制角色规则。审批停用/角色撤销/来源过期不默认放行。库存纠错与新增执行分别判定；完整锁序与并发仍须G3通过。`production_team`采用既有Department层级；班组长/操作工同班组、厂长同公司全厂，仓管限制到本车间线边仓，实际仓库集合由B02配置。
5. **原生记录与最小保护**：Version保存状态、原因和人员字段变化；Comment补业务动作说明和依据版本，Workflow Action继续作待办。仅对本生产工单关联的Version/Comment/审批依据附件及原单补必要修改/删除限制（沿E hooks原扩展点，函数放同一制造文件）；直连数据库/超级管理员运维不宣称不可篡改。若原生记录不能可靠还原依据，先保存失败反例、提出最小字段补充，不自动新建审批流水库或整套快照服务。
6. **提醒只接一个实际渠道**：系统内待办保留，外部提醒是用户新增必要项。默认企业微信预案，客户可在部署前改定其实际渠道；不预建三家SDK/适配层。优先核原生Webhook JSON模板；目标平台协议、收件范围、登录链接可达性、业务返回码、有限重试及凭据日志处理未验证，暂不冻结发送实现。失败不能改变审批结果或显示假送达。B01当前Compose没有完整workers配置，不能承诺背景消息已可运行。客户配置缺失只阻塞此发送子项，不阻止审批核心开发。

允许文件：上述Work Order/Job Card/Stock Entry原控制器、Work Order原JSON/JS或原生Custom Field配置、E hooks/限定fixtures，以及三者现有test文件。对象/列表权限若需代码，复用B02已绑定拟新增的`manufacturing/permissions.py`，仅补本生产工单和关联Workflow Action的范围条件，不另建第二套权限模块。只读参考Frappe和其他候选；不升级底座、不增加公共审批服务、外部审批按钮、会签/代签/催办升级、第二套库存账或额外候选部署。外部提醒若最终需要超出原生配置的代码，先补实际渠道入口再局部实施。

## 6. 最小样例与验收入口（未运行）

复用B01隔离`xgd-test.localhost`、原生FrappeTestCase及B02/B10显式最小fixture方式，禁止重新全量递归装载或安装Payment Gateway。生产样例沿用R02产品/BOM/三工序及既有仓库原生创建方法；新增合成组织“车间甲/班组甲、乙；车间乙/班组丙”，两个操作工、两班组长、厂长、线边仓管、无权观察者；全是合成账号，不导入试点真实信息。首次先证明最小fixture和源文件身份，再执行用例。无产品变更的原生核验沿当前已验源清单；加入B19测试/补强后生成独立的拟新增`.development/checks/b19-source-manifest.json`，复用现有`check_source.py`核Web/Bench实际文件，不覆盖B02/B10历史清单；构建、资源和元数据同步按B01 README已绑定命令执行，只同步本次变化。

| 编号/归原CASE | 输入与动作 | 必须观察的预期 |
|---|---|---|
| B19-V01 / CASE-01 | 本班组操作工送审→本班组长审核→厂长签批，刷新重读 | 逐级记录操作者/时间/原因/依据版本；只有最终通过才提交工单；批准本身无报工、库存账或开工事实。 |
| B19-V02 / CASE-07 | 发起人兼审批角色、审核/签批同人、其他班组长、其他公司厂长、撤权账号；分别走专用动作与普通API | 全部按三方分离、对象范围和当前角色拒绝；同班组/同公司合法正例不被误封。不得用Administrator作为业务正例。 |
| B19-V03 / CASE-07 | 未批准工单直接submit、PUT审批字段、手工Job Card、make_time_log、库存submit及只传job_card间接关联 | 不能绕过审批；没有有效报工、库存变化、派生任务副作用。原生配置、直接方法和批量入口分别覆盖，不只测隐藏按钮。 |
| B19-V04 / CASE-01/05 | 待审核/待签批修改依据；退回/撤回后修改、重提；终止后查询 | 待审依据冻结；重提从审核开始、旧签批不继承；终止原因与历史保留。审批人员不能代改业务依据。 |
| B19-V05 / CASE-04 | 旧页面停留；另一路退回修改重提到同名状态；旧页面再批准 | 因版本不同拒绝，要求重新查看；不能将重读最新内容直接等同本人已审核。 |
| B19-V06 / CASE-04 | 同次动作双击、同单同时批准/撤回、签批/执行竞争、写记录时故障 | 一次有效推进/记录；失败回滚、重试读原结果，不重复提交/建任务。与G3共享锁序；未执行不宣称并发安全。 |
| B19-V07 / CASE-05 | 已批准无事实取消修订；已有领料/报工要求改数量 | 无事实修订重新审批，旧单保留；有事实拒直接改，关联新单另审，原单合法退料/冲销/结束仍可进行。 |
| B19-V08 / CASE-07 | 改/删原单、Version、审批Comment、依据附件；跨班组查待办/历史/导出；核当前站点日志清理配置 | 普通业务角色不能破坏已留痕记录；查询和待办不泄露他组依据；允许的系统派生更新正常，日志清理不得清除必需审批证据。固定Frappe默认清理表未列Version/Comment，不代表实际站点配置已核。 |
| B19-V09 / CASE-01/07 | 激活前有draft/submitted旧测试单；重复导入流程配置 | 不自动批准旧单、不删旧数据；配置仅作用确认的新单边界，重复执行不制造第二套流程。 |
| B19-V10 / CASE-08/11 | 中文PC/实际手机操作；单一外部渠道成功、HTTP失败、HTTP200业务失败、超时 | 状态/原因中文，消息仅是待办提醒，链接登录后重鉴权；发送失败可见，不回滚已确认审批，不外泄业务明细/密钥。渠道和可达地址未提供时标未验证，不模拟成实发成功。 |

**真实入口与拟新增测试分开：**Frappe现有`frappe.workflow.doctype.workflow.test_workflow.TestWorkflow`及其`test_approve/test_wrong_action/test_workflow_condition/test_workflow_action_recreated_when_state_is_re_entered/test_if_workflow_set_on_action`已定位，未运行；它们用ToDo且setUp会删除Workflow Action，不直接拿来覆盖本项目或在有保留证据的站点裸跑。

拟新增`TestWorkOrderApproval`位于已有`erpnext/manufacturing/doctype/work_order/test_work_order.py`，覆盖V01–V09；Job Card/Stock Entry旁路断言放对应已有test文件并回链同一用例。类目前不存在，不可现在执行后把0收集当通过。命令模板沿已验证runner，具体用例写完、最小fixture可执行且本轮改动源码部署后才运行：

```sh
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --case TestWorkOrderApproval --skip-test-records --skip-before-tests
```

后续真实HTTP：`POST /api/method/erpnext.manufacturing.doctype.work_order.work_order.apply_production_approval`是**拟新增入口**；普通旁路已有`frappe.client.save/submit`、Resource API、`frappe.model.workflow.apply_workflow/bulk_workflow_approval`，不能假设只需测新API。数据只在本地隔离站点生成，脱敏结果/版本/命令回写`evidence/B19/`；新HTTP脚本未编写，不提供虚构运行结果。

## 7. 本轮停止点与后续

本轮停止于确认规则、固定源码、静态绑定和任务卡更新。B19尚未实施/测试；审批核心的用户决策已齐，企业实际通知渠道/账号和可达地址在部署前落实，废料库存细节按真实样例另绑原卡。下一次可先执行B19的最小样例与原生流程受控验证，优先验证V01/V02/V03/V05/V09，再依据失败反例实施已限定补强；这不要求G1/G2/G3提前通过，也不能替代它们。

若必须改Frappe共享框架、重造审批/事实账、导入旧业务数据或扩展多渠道服务，停止受影响子项，记录依据与最小替代再确认。未变化的B02/B10结果直接继承，达到本卡阶段条件就停止，不重新选型或反复全量测试。

### 2026-10-27 HTTP样例运行补充绑定

真实HTTP/内部commit批量审批采用原测试库的专用本地副本`xgd-b19-http.localhost`，复用原生BackupGenerator与_new_site(source_sql)，固定新库且拒绝已有目标，原库数据不覆盖；不是客户/开发站点启用。实际命令与限制统一记录于[HTTP证据](../B19/http/run-record.md)，准备脚本`.development/checks/b19_http_site.py`及HTTP客户端脚本只属于测试设施，不新增产品服务。没有合适最小样例时停止对应HTTP项，不mock事务。
