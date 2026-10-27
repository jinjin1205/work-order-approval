> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R07｜权限、对象范围与直接入口绑定

日期：2026-10-26。对应 B02；关联 B06、B08/B09、B10～B13、B16、A01～A03。**本页是静态绑定与后续验收设计，没有修改产品代码、启动服务、连接数据库或新增运行通过结论。** 既有 R05 结果直接继承；本轮新发现均标静态发现。原卡状态由总绑定更新，本页不另建实施任务清单。

## 1. 固定依据与当前结论

- ERPNext v15.124.1，`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；Frappe v15.124.0，`f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab`。本轮只读源文件位于 `.evaluation/r07-sources/`；下文源码路径均相对此快照，实际开发在 B01 核实的同版本维护分支进行，**不编辑评估快照**。
- 已读 [B02](../../docs/任务卡/02-生产与物料闭环.md)、[R02角色/fixture](../R02/fixture-spec.md#3-最小角色与可见范围)、[CASE-07预期](../R02/expected-results.md#case-07-权限状态与历史)、[R05权限](../R05/followup-access.md)、[R05手机](../R05/followup-mobile.md)、[R06选择](../R06/selection.md)。原 PRD 第5.3.2及7节区分“这一单这一道工序的报工权限”和“工单可见范围”；两者不合并成一个手工工单白名单。
- R05普通 Resource API 对显式 Work Order User Permission 的读、列表、写拒绝子集有效；ALL/DEPT/PERSON当时只是标签，未实现部门或人员变更后的自动判定。`get_operation_details` 已实测向无业务角色返回受限子行 `name/idx`。制造角色写库存草稿已实测成功，不能直接用作只报工岗位。
- R05 Stock User 在桌面390×844小屏提交既有领料草稿后实际过账成功；同时读取 Stock Settings 的页面请求报权限错。两件事实同时保留，不能据此给予整份设置或管理员权限。
- **可独立先行绑定：**最小角色配置、原有显式对象范围、已证实的辅助接口读权限修补、原生撤权机制验收。**条件绑定：**任务范围及逐笔报工身份接入，须先通过 B08/B09 的“Work Order Operation＝任务、Job Card＝逐笔事实”映射试验。完整 B02/CASE-07 不能凭前一子集关闭；B16具体报表与AI入口分别按原卡落实。

**分项依赖修正：**上述基础权限子项通过后即可交给B03及后续，不等待B08/B16/A01整卡。任务scope规则本身归B02；真实报工接入归B06/B08/B09，库存接入归B10～B12，实际导出归B16，AI归A01～A03，使用同一规则并回链证据。B02不要求下游先完成才允许下游开工，也不以AI实调作为自身关闭前置；完整CASE-07仍分别在核心闭环和AI验收汇总，不减少检查。

以下 blob 由本轮 `git hash-object` 对实际读取快照计算，便于复核文件身份；不是整个镜像逐文件证明：

| 文件 | blob |
|---|---|
| `erpnext/manufacturing/doctype/job_card/job_card.py` | `cd8c77dc9ea49d27a991eb47c1555af2e01a6518` |
| `erpnext/manufacturing/doctype/work_order/work_order.py` | `808777b02a1833279c5073fce26902d83eca60c6` |
| `frappe/permissions.py` | `ebcbf8dca697a4d0071a3a9ef8272e40b0cc10b9` |
| `frappe/desk/reportview.py` | `0a7bf3f464e1ac7eba287d6ab8b18fbd45df74f8` |
| `erpnext/setup/doctype/employee/employee.py` | `b4eb03fcbc609853b0562dd3aad91e8013402706` |

## 2. 最小岗位配置：复用原生权限，不直接分配默认大角色

复用 User、Role、DocPerm/Custom DocPerm、User Permission 和 Employee；不另建账号、租户、组织或权限引擎。`job_card.json` 默认 Manufacturing User 同时有 create/write/submit/cancel/delete/amend/export/share；`stock_entry.json` 该角色也有库存 write/submit/cancel/delete。Frappe多角色权限会组合，新增一个窄角色而保留原宽角色并不能收窄。

下表是本项目合成岗位的**待实施配置基线**，不是已存在角色或客户人员授权。原生 Role/Custom DocPerm 配置优先；只调整明确使用的 DocType，保留无关ERP角色定义。

| 岗位 | 默认允许 | 默认不给；确有授权时单独赋予 |
|---|---|---|
| 配置管理员 | 初始化、账号、岗位/对象权限、必要参数 | 不用于证明普通业务通过；管理员旁路不能替代业务鉴权 |
| 计划员/班组长 | 授权工单/任务的建单、生成、派工与查看；经单独动作授权的开始/人工结束 | 系统设置、库存提交/过账、无范围数据；人工结束仍需差额及原因 |
| 操作工 | 授权任务的普通报工、草稿检查、本人确认；读取该动作必要的已授权上下文 | Work Order结构/授权字段修改；库存 create/write/submit/cancel；任意报工cancel/delete/amend；share、import、export默认关闭 |
| 仓管制单 | 授权公司/工单/仓库的领料、退料、成品入库草稿 create/write/read | submit/cancel等过账或反向动作，除非其岗位另有审批/过账授权 |
| 库存审批/过账 | 上述范围的 submit；需要时与仓管由同一人兼任 | 自动获得所有仓库、Stock Settings写权限；反向/撤销另授，历史仍保留 |
| 管理查看者 | 授权范围read；必要基础查询report | 生产/库存写；需要导出的对象明确授export并验其范围 |
| 无业务角色/外部门对照 | 仅明确授予的对照数据及动作 | 任何未授予对象、辅助入口、AI取数 |

说明：

1. “确认报工”需要正常 Job Card提交链，不能因为给了原生write/submit便允许操作工任意编辑全部计划、人员、关系或取消旧事实；B08/B09的入口与字段保护必须同步。首版无额外主管报工审批。冲销权限单列，生效事实不可删的限制不因持有cancel/delete而解除。
2. 原生Work Order write同时支撑多个状态动作。`stop_unstop(work_order,status)`/`close_work_order(work_order,status)`已有DocType及对象write检查，但没有本项目独立动作区分。仅配置write不能算已完成“开始/结束/取消分别授权”；B05状态动作复用原入口，加限定动作角色检查，不另建通用动作框架。
3. 仓库范围用原生 Warehouse User Permission；检查 Stock Entry头部 `from_warehouse/to_warehouse` 和每条 Stock Entry Detail 的 `s_warehouse/t_warehouse`，不能仅检查表头。公司与工单范围同时生效，不能以同一个WIP仓允许跨工单错引用。上游已有 `test_warehouse_user`，本项目岗位组合仍需普通账号实测。
4. 默认不授share；已有分享也要盘点。`frappe/permissions.py`及`db_query.py`存在分享兜底/OR路径，仅新增一个scope hook不能假定阻止所有既有共享。B02使用隔离数据，不删除客户分享；是否需硬拒绝分享跨scope由同一验收反例决定，不能修改全局Frappe规则。
5. Employee自动追加的Employee角色及已有自助权限要记录在实际矩阵中，不能把实际组合写成“只有操作工角色”。
6. **最小操作工正常链仍有实施门槛：**`JobCard.update_work_order_data:859`和`update_corrective_in_work_order:806`直接调用`wo.save()`，而`Document._save:406`会检查Work Order write。上表不给操作工父单任意写权限，B09又要求不使用通用ignore_permissions，因此不能假定新窄角色仍能完成原生汇总。必须在F-RPT-01前绑定受控系统派生写的权限衔接：只容许已授权报工命令更新确定性工序/工单派生字段，并保留原save链；直接工单结构/状态/授权字段修改仍拒绝。不得给操作工整单全写来掩盖问题。Frappe has_permission hook只收窄，不能凭返回True产生缺失DocPerm；具体衔接未闭合时该正常确认子项保持条件门槛。

## 3. 对象与人员：任务scope和数据可见范围分别落实

授权判定至少包含：当前登录人及有效角色 → 工单/公司/仓库的数据范围 → 本次动作 → 本道任务报工scope → 员工身份与当前状态。每次新请求/正式确认重新判定；不信任生成AI草稿时的结果、客户端employee或页面按钮状态。

### 3.1 原生可复用部分

| 已有入口/字段 | 已核依据及复用限度 |
|---|---|
| `frappe.permissions.has_permission(doctype,ptype="read",doc=None,user=None,...)`；`Document.check_permission(permtype="read",permlevel=None)` | 传doc才进入对象检查；仅DocType权限不足。`get_doc`本身不表示已授权。`ignore_permissions`只可保留底座内受控系统调用，不能由业务请求传入以绕过检查。 |
| `frappe.permissions.add_user_permission(doctype,name,user,ignore_permissions=False,applicable_for=None,is_default=0,hide_descendants=0)` | 已有工单/公司/仓库显式范围配置入口；`applicable_for`和Link字段影响传播，须记录配置，不默认所有关联表自动受限。 |
| `frappe/permissions.py:333` `has_user_permission`，`frappe/model/db_query.py:1444` `add_user_permissions` | 检查父/子Link及列表条件；无User Permission通常不是“拒绝全部”，删除最后一条限制可能回到角色授权范围。不能靠删光白名单实现撤权。 |
| `Employee.user_id/company/department/status`；`employee.py:66–106,184–214` | 登录关联、有效员工重复关联校验、员工角色及状态同步已有实现。R05特意 `create_user_permission=0`，不能从该例推出默认员工自限配置可满足部门任务。无需引入完整HR/薪酬。 |
| `User.on_update`、`UserPermission.on_update/on_trash` | 前者 `frappe.clear_cache(user=...)`；后者删除user_permissions缓存并在提交后发刷新事件。通过原生保存/删除配置生效，不直写表；实际现有会话/API token撤权效果待普通请求复测。 |

### 3.2 任务映射条件与最小新增

**以下为拟新增绑定，不是上游现成功能，也未创建文件。** 与B08/B09统一：用 `Work Order Operation.name + parent` 标识这一单这一道任务；Job Card的 `operation_id` 指向任务，`work_order`须等于该任务parent。`JobCard.validate_operation_id`现有检查带多个字段同时满足的条件，不能视为所有伪造ID组合均已验证。

映射试验通过后允许：

- 在实际已有 `erpnext/manufacturing/doctype/work_order_operation/work_order_operation.json` 承载拟新增 `report_scope`（ALL/DEPT/PERSON）、`report_department`（Department Link）、`report_employee`（Employee Link）。DEPT须有明确部门，PERSON须有有效个人；缺字段/非法组合不默认为ALL。ALL仅限明确授予报工动作的有效登录操作工；不是匿名或所有系统账号。部门层级是否包含下级不在当前确认范围，合成样例按精确部门匹配，不自作扩展。
- 拟新增 `erpnext/manufacturing/permissions.py`，只承载本项目制造任务范围与登录Employee的统一判定；由现有 `erpnext/hooks.py` 注册原生权限hook。Frappe实际hook契约：`has_controller_permissions`调用 `doc,ptype,user,debug`；`DatabaseQuery.get_permission_query_conditions`调用 `user,doctype`。具体新函数不是原生接口：任务report_scope只约束报工写动作；read/list/export/result查询使用单独的数据可见规则，不能因为当前不能报工便默认不能查历史，也不能因为有报工scope便授整单read。相同数据可见规则同时供单条判定和查询条件使用；任务写scope在确认与controller共用一份判断。二者可在同一小模块内复用身份解析，不互相代替。
- `job_card.py`的报工入口、`validate`/`on_submit`覆盖身份及任务归属；只改公开helper会漏掉Resource PUT、`frappe.client.save/submit`和Desk savedocs。普通工人只确认自己的Employee；代报不是已确认首版默认能力。`owner`是文档创建者，不能替代任务被指派人/报工人；多员工时间表不能被当作一次多人分摊。
- 任务scope由计划授权者修改；普通工人不能用PUT把PERSON改ALL、换`operation_id/work_order`、换Employee后报工。已有事实保留原操作者与员工，不随Employee改部门或离职改写历史。当前权限决定新操作；历史可见范围仍走当前数据授权。

**数据边界必须另验：**PRD把工单可见范围与任务报工范围分列。原生Work Order GET会返回operations子表；有权读取某张Job Card不能被推断为能看整张工单或其他任务事实。B02合成矩阵要明确哪些父单字段/子行本就可见，哪些受限，随后检查父单GET、Job Card列表/单条、工序helper、日历和导出返回。同一工单的三道任务给ALL/DEPT/PERSON不同报工scope，必须分别拒绝不具备scope的报工；跨工单数据可见仍以原生User Permission验。若要求在同一可见工单内再隐藏部分工序/事实，应在同一制造权限模块/受控上下文取数中限定返回，不通过授予父单全读来消除报错。该字段/返回契约与任务映射一起闭合前，不把动态范围部分标可交付。

## 4. 实际入口、调用方与限定修改

| 实际原入口 | 已核调用链/问题 | 最小处理及状态 |
|---|---|---|
| `job_card.py:1129 get_operation_details(work_order,operation)` | `job_card.js:248 operation`事件调用；直接get_all工序name/idx；R05已复现越权返回 | 必改：在读取前用真实父Work Order检查read；任务级可见策略接入后再按目标操作行限制返回。无权抛PermissionError，不返回受限ID或假空成功。保留签名及授权正例。 |
| `job_card.py:1139 get_operations(doctype,txt,searchfield,start,page_len,filters)` | `job_card.js:5`工序Link查询；直接get_all父单工序 | 同对象读取边界的局部改造，与上一入口共用规则。静态发现，越权HTTP未实测；检验filters缺失/伪造父单及分页搜索。 |
| `job_card.py:1255 get_job_details(start,end,filters=None)` | `job_card_calendar.js:30`日历调用；get_filters_cond默认with_match_conditions=False后直接SQL；返回卡名/工单/备注 | 静态确认此调用未追加对象匹配；运行泄露未验证。需使查询复用有权限的Job Card集合及数据可见规则，保留原时间输出；不把报工写scope直接当管理查看权限。只隐藏日历按钮不能关闭直接RPC。 |
| `job_card.py:1118 make_time_log(args)` → `JobCard.add_time_log(args):515` | `job_card.js:373–400`传job_card_id、employees、时间、状态/数量；get_doc后先validate_sequence_id，再add_time_log，最终save检查write | 在读出敏感上下文及动作前检查目标文档/任务权限；Employee不得由客户端任意冒领。save/submit仍走原生保护；任务/逐笔事实接入服从3.2门槛。 |
| `work_order.py:1632 make_stock_entry(work_order_id,purpose,qty=None,target_warehouse=None,source_stock_entry=None)` | work_order.js:406/968/1014；stock_entry.js:380；读取工单并返回库存草稿，本函数未显式检查源单read/目标create | 静态相邻边界，未实测越权。B10/B12生成草稿前检查源工单、关联来源单及目标Stock Entry create，限制目的/仓库；实际save/submit重新检查当前对象。不得只依赖后续保存会拒绝。 |
| `work_order.py:2017 make_stock_return_entry(work_order)` | `work_order.js:259` Return Components；先get_available_materials再读工单 | 同上；B11在计算可退材料前检查源工单read及库存动作。状态/净额修复由数量卡负责，权限规则不重复实现。 |
| `work_order.py:1764 make_job_card(work_order,operations)`；`:1625 set_work_order_ops(name)` | 前者由work_order.js:345调用，create_job_card最终insert；后者原保存链；不能把子单insert许可等同于父任务改动许可 | B06检查父单write、任务生成动作、操作行属于该父单；不接受伪造operation_id。set_work_order_ops当前网页调用者未定位，保留直接入口验证，不虚构调用者。 |
| `work_order.py:1724 stop_unstop(work_order,status)`、`:1780 close_work_order(work_order,status)` | `work_order.js:1028`状态动作；已存在DocType及对象write检查 | 直接复用对象检查，B05补本项目动作授权/状态允许值及人工结束原因；无证据不重写原状态框架。 |
| `job_card.py:1190 make_stock_entry(source_name,target_doc=None)` | job_card.js:523–525表单映射到Stock Entry；用 `frappe/model/mapper.py:get_mapped_doc(...)`，该函数已有源read/目标create逻辑 | 复用而非重新做映射器；在本项目strict user permission配置下验授权/拒绝，不假定其所有分支均通过。 |
| `stock_entry.py:3951 get_work_order_details(work_order,company)` | 已有work_order.check_permission("read") | 直接复用，作为新辅助入口的既有模式；不删这层保护。 |

`frappe/handler.py:execute_cmd`只检查白名单和HTTP方法，不自动完成业务对象鉴权。`frappe.__init__.get_all`明确设置ignore_permissions=True；不能在面向普通用户的取数里把get_all当受控get_list。

## 5. 页面设置读取、导出和AI边界

### Stock Settings最小读取

实际调用已定位 `stock_entry.js:67`读取 `sample_retention_warehouse`、`:174`读取 `disable_serial_no_and_batch_selector`。`frappe.client.get_value`/`get_single_value`先检查Stock Settings整份read；原始 `stock_settings.json` 给Stock Manager读写、Sales User读，未给Stock User读。

最小方案固定为在已有 `erpnext/stock/doctype/stock_entry/stock_entry.py` **拟新增** `get_stock_entry_form_settings(company, stock_entry=None)`，`stock_entry.js`只将上述两次通用设置读取改用该限定入口；此函数目前不存在，不冒称原生API。已有单据先检查该Stock Entry read、真实company与传入company相符；新单据检查Stock Entry create及Company当前范围。只返回这两个字段，不能接受任意设置字段名。`sample_retention_warehouse`若不在当前用户可选择的仓库范围，不返回其名称，仓库候选仍通过原生权限查询；不能为加载页面泄露其他仓库。`StockEntry.onload`现有方法仅调用update_items_from_bin_details，本方案不依赖它覆盖新建单据生命周期。该方案局部新增的理由是现有通用RPC只能按整份Stock Settings授read，而本页面只需要两项信息；不授Stock User整份设置read/write，不改Frappe通用接口。本轮未创建新函数、未验证页面修复；正常过账及直接任意读取设置仍被拒需分别验收。

### 导出/查询

- `frappe/api/v1.py:document_list/read_doc/update_doc/delete_doc`、`frappe.client.get/save/submit/cancel`和`frappe/desk/form/save.py:savedocs(doc,action)`均是本项目需覆盖的实际入口；网页成功不足以替代直接API失败验证。
- Report Builder实际导出为 `frappe.desk.reportview.export_query()` → `_export_query(form_params,csv_params,populate_response=True)`；后者调用DatabaseQuery、`can_export`。`selected_items`会替换filters，但仍须受对象权限限制。B16复用此入口；检验普通角色、伪造选择受限ID、无过滤导出、字段/子表、可见与不可见混选。不能把read自动当export，也不能只检总行数而不核返回ID。
- Query/Script Report有另一入口 `frappe.desk.query_report.run(report_name,filters=None,user=None,...)`及`export_query()`，其report/export门禁和Link过滤检查已读；具体报表SQL能否遵守本项目任务scope未验证。B16只开放逐一绑定并验过的数据源/报表；不能给report角色后声称所有ERP报表都安全。后台导出、Prepared Report和历史文件下载的执行身份/撤权后访问尚未闭合，本页不把它们算已通过；基础同步导出先行，不新增后台邮件能力。
- AI-1/2/3必须复用相同对象/字段可见规则；AI草稿的生成、回看、确认分别按当前登录人检查。模型不持有管理员或Stock User通用凭证，不直接get_all/SQL读范围外数据。确认调用普通业务入口，不能把AI草稿保存成功当已报工。实际AI取数/草稿入口尚未存在，本页不给虚构API；由A01～A03绑定并验收。

## 6. 必要验证、可复用命令与结束门槛

P01～P06是权限覆盖矩阵，**不是要求B02先把全部下游功能做完**。B02验配置/规则/已存在且本卡修补的入口；涉及尚未形成的报工、库存页、具体报表或AI入口时，由对应消费卡实施并验证本表相应反例。B17汇总核心权限，A01～A03补AI权限，不反向阻塞B02基础交接。

运行位置固定为B01新隔离测试环境的bench目录，测试站点为 `xgd-test.localhost`；当前站点尚未创建。B01须先确认该bench实际加载改动后ERPNext源码并记录提交/diff，不得在旧R05镜像上测试后宣称新改动通过。使用合成账户及R02 v1；未改变的R05证据直接引用。新配置/修补/任务映射改变后只复测受影响路径。每例记录版本、角色组合、User Permission、Employee映射、请求/返回、事实前后计数和限制；不保存凭证。

| 测试组 | 正常路径 | 关键失败路径/通过判据 |
|---|---|---|
| P01岗位 | 计划员建单；操作工自身确认；仓库草稿及授权过账；查看者授权读取 | 操作工直接创建/写/提交库存、无提交权仓管过账、查看者写、无角色辅助读取均拒绝；未新增事实/库存账 |
| P02任务与数据 | 同工单不同操作行ALL/DEPT-A/PERSON-A；a/b有权任务成功；跨工单列表与导出集合正确 | outsider调用DEPT，b调用PERSON，伪造父单/操作行，普通人改scope/owner/employee，父单子表/日历/辅助接口受限数据均不得越权；数据可见矩阵逐字段列清 |
| P03身份/撤权 | 当前有效Employee与session.user匹配；批准的原生配置更新后新请求正确 | 员工停用/换部门/解除个人指派、角色撤销、撤销最后一条对象限制、旧会话/API token及旧AI草稿确认；不依赖刷新页面才拒绝；不把删空白名单变成放开全部 |
| P04直接入口 | Resource、client.save/submit、Desk savedocs与正常业务入口结果一致 | 无权真实ID、POST/PUT传伪造关系、run_doc_method及GET辅助读取；拒绝时不泄露原单内容，无新卡/时间行/工序量/库存变化 |
| P05库存页 | Stock User/最小仓库角色开既有单和新建单，无设置权限弹窗，授权领退/入库链成功 | 任意Stock Settings字段读取/写入仍拒绝；跨仓子行、跨公司/工单及无过账权提交拒绝；不靠给Stock Manager消除提示 |
| P06导出/AI | 已授权同步导出只含矩阵允许行/字段；有依据AI草稿可预览且取消零事实 | mixed selected_items、无过滤、受限报表/日历/AI引用、生成后撤权均拒绝或过滤为明确授权集合；错误不能被解释为数量0 |

已核可复用测试入口（本轮**未执行**）：

```sh
bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.stock.doctype.stock_entry.test_stock_entry --test test_warehouse_user --test test_warehouse_company_validation
```

命令选项来自固定 `frappe/commands/utils.py:757–778`；两测试实际存在于 `stock_entry/test_stock_entry.py:1468–1520`。只证明原生仓库/公司权限相关路径，不覆盖新岗位、任务scope、辅助接口、导出或AI。新增反例放到现有 `job_card/test_job_card.py`、`work_order/test_work_order.py`、`stock_entry/test_stock_entry.py`对应测试文件，不另建通用测试框架；实施后以实际新增测试名运行，R07不捏造尚不存在的测试名。

历史普通HTTP探针 `python3 .evaluation/r05-erpnext/probes/access_http.py --setup evidence/R05/followup/access-setup.json --secrets <本地受限凭证文件> --section access --output <新独占证据路径>` 已逐行检查：此命令会写remarks和开始计时，**不是只读复核命令，不在旧R05夹具盲目重跑**；它硬绑定R05站点和prefix，也未覆盖部门变更/冒领Employee/导出。B02复用其HTTP身份、原始返回及不覆盖输出方式，改为B02独立新夹具并扩展上表受影响反例后再执行，不把旧命令冒称完整CASE-07命令。

本轮静态校核动作：`rg`定位实际定义/调用者，`sed`读正文，JSON解析DocType角色与字段，`git hash-object`记录上述blob；均未运行业务测试。用户使用简体中文、服务中国公司；权限失败及必要操作提示用简体中文，并经页面核对，语言/术语配置由本轮公共配置绑定负责，不扩展中国财税。

## 7. 允许修改范围及停止条件

- 先行权限补丁：ERPNext `job_card.py`所列helper/相邻日历读取及其现有测试；`work_order.py`所列制造/退料草稿与任务生成的对象检查及其现有测试；原生角色/DocPerm/Custom DocPerm/User Permission配置。按反例局部补，不为命名风格清理其他模块。
- 条件范围：映射试验通过后，`work_order_operation.json`任务scope字段，`job_card.py`正式写入边界，拟新增 `erpnext/manufacturing/permissions.py`及已有 `erpnext/hooks.py`对应hook注册，所需界面最少字段；只服务制造任务，不新建跨ERP权限框架。B08/B09负责事实数据与冲销，B02只提供同一权限规则。
- 页面设置：`stock_entry.py`必要设置投影/边界、`stock_entry.js`两个读取调用及必要测试；不修改Stock Settings整份权限来掩盖页面问题。
- Frappe的permissions、Document、DatabaseQuery、Resource API、client、handler、导出及User/UserPermission本轮作为复用依据，**不授权修改框架**。若满足范围必须大改框架/新建平行身份体系，记录反例并返回R06重评。
- B02可关闭需本卡负责的角色/对象/任务scope规则、撤权及已绑定直接入口正常/失败证据完整；规则或自身入口缺项继续保留。具体业务接入/导出/AI检查归消费卡并回链，不把下游功能完成作为基础权限交接前置；B02关闭不等完整CASE-07或首版通过。未启用报表/后台邮件、企业身份集成、客户授权数据和真实现场不在本轮。

## 2026-10-27 B08 本批实现回链

实际证据见[实施记录](../B08/implementation/run-record.md)。原Job Card每笔事实/唯一`report_request_id`/`report_payload_hash`、服务端`report_time_context`与秒数字段；原Work Order Operation增加`report_scope/report_department/report_employee`。JobCardTimeLog只补已确认父卡保护；WorkOrder只放行服务器上下文中的本工序派生字段。没有新增permissions模块、事实表或Frappe改动。

实际入口均在`job_card.py`：`get_production_report_tasks`、`preview_production_report_time`、`confirm_production_report`、`get_production_report_result`、`correct_production_report`；内部`_report_task/_report_context`复用原公司/班组/状态检查，`_report_time_context`复用B04计算和B14读取。中文原WorkOrder弹窗及JobCard依据查看，不另建页面系统。`work_order.py:validate_production_execution_state`由原判定拆出复用，旧请求找回先查历史权限，新事实仍查执行状态。

实际最小更正为原生cancel/amend，起止不变沿用原时段依据；有提交库存单或后工序事实即拒绝。原生子工序配置明确拒绝，不新增子工序业务。三笔、窄回写、同键真实HTTP、快照旧新、原卡/子行保护及受控回滚已有证据；全部权限组合、完整逆向/跨对象并发、现场10秒及G1/G2/G3未通过。旧节中的“拟新增/当前不存在”为实施前历史，不代表本批状态。
