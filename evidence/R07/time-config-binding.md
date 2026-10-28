> 公开归档副本（2026-10-28）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R07｜B14最小时段配置、权限读取与B08确认衔接

**2026-10-27实施续接：**B14配置子项实际结果见[本批证据](../B14/run-record.md)，B08原生事实反例见[探针](../B08/native-fact/run-record.md)；下文保留实施前静态记录。运行核查纠正：本版本Frappe读取CSV，必要四词条实际在`erpnext/translations/zh.csv`，原拟PO未生效且已撤回。父子表写反例后在两控制器补归属和独立写保护，范围仍在原白名单内。G1/G2/G3未关闭。

2026-10-27。**本轮是源码静态绑定和计划更新，未改产品代码、未创建配置表、未迁移数据库、未运行业务测试。**本文件是原R07的专项证据，不新增平行任务表；状态仍以原B14/B08卡为准。

实施时沿原卡使用`superpowers:executing-plans`。本轮使用需求梳理、编写计划方法，用户已授权连续推进；不重问C05/C10/C13，不因技能默认路径另建一套计划。

## 1. 目标、基线与范围

目标：配置管理员能用原生中文表单维护休息/可加班时段；操作工只能从有权报工的任务取得所需上下文；确认后保留当时依据，规则变更不改写历史。沿用B04两个函数，不新建计算引擎、考勤、排班或工资结算系统。

- 当前已发布源码：`7d2e9453c35e217eac38674f359b1fbfa196ee78`；ERPNext15.124.1上游`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，Frappe15.124.0固定快照`f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab`。累计补丁`fc68d4af7ab3c74ed84ca898bffebe36b24c5c66041b272ec851e241754214e3`本轮未变。
- 需求：原TRD4.3/4.6、CASE-03、C13；本轮用户明确**配置管理员维护，操作工从本人有权报工的任务查看，厂长签批不附带配置修改权**，已记C14。客户实际账号待部署时映射，不是本轮缺少决定。
- 五项目复用核查沿用[B04固定版本证据](../B04/time-metrics/run-record.md#五项目复用核查固定版本2026-10-27)，条件未变不重新安装/跑五套。其他四个项目本批未取得可直接用于Frappe权限、原生表单及本项目规则快照的已验证代码，不据此声称全仓不存在。
- 新增数据结构是本轮根据源码作出的工程选择，不冒充用户指定技术方案。首版业务仍仅生产工单、原公司/班组/任务范围和中文网页；时段作用范围仍为全部工序或指定工序，不加班次、节假日、人员特例、定时生效或多层规则继承。
- 文件身份与静态检查见`time-config-source-manifest.json`；不把文件存在/语法检查写成运行通过。

## 2. 原生能复用什么，为什么不能直接改名使用

下表ERPNext路径均从`erpnext/manufacturing/doctype/`开始，行号绑定本批源码；Frappe路径从应用包开始。

| 已读源码入口 | 实际行为与判定 |
|---|---|
| `manufacturing_settings/manufacturing_settings.json/.py` | Single配置已有原生表单、角色权限与track_changes；`allow_overtime`是排程开关，没有按工序、优先级、休息/可加班区间的数据。不能把其开关当报工加班额度 |
| `workstation/workstation.py:73/82/126/322`及`workstation_working_hour/*.json` | 工作时间用于工作站排程；开始>=结束拒绝，工作时段重叠拒绝。当前需求允许跨零点及休息并集，直接改此校验会影响排程，超出本卡 |
| `downtime_entry/downtime_entry.json/.py` | 是工作站停机事实及停机原因，不是重复日规则，不能用它存休息配置；不自动把设备停机全部扣给某个操作工 |
| `job_card/job_card.py:1434/1474` | B04的`calculate_report_time`与`calculate_report_metrics`已经实现；输入必须明确，默认无规则与缺上下文不同。直接复用，配置层不重写区间、效率或工资公式 |
| `job_card/job_card.json` | 原有起止时间、员工、数量与成本分钟；没有本项目停工/加班秒、规则快照和有效工时字段。`hour_rate`是作业成本，不能改作个人工资单价 |
| `frappe/client.py:get/get_list/save`及`model/document.py:_save/check_permission` | 普通单据读写及子表父权限入口可复用；不能用select代替read或仅靠隐藏菜单阻止请求 |
| `frappe/__init__.py:2020/2043` | `get_list`执行权限筛选；`get_all`明确跳过权限。直接按操作工权限筛规则可能漏掉高优先级规则，直接公开get_all则泄露配置；必须明确受限服务端读取边界 |
| `frappe/model/document.py:1315 save_version` | track_changes保存Version差异，受ignore_version等条件影响；不等于业务快照，也不保证报工能永久重建当时全部配置。复用作配置审计，不拿它代替报工事实 |
| `work_order/work_order.py:71/85 check_production_execution` | 已有公司/班组及批准/停止门槛；旧非审批工单存在返回None分支。新报工入口不得把None当已获授权；任务精确范围、员工身份、报工动作仍需原B02/B06判定 |

比较后的最小选择：**新增一个原生规则DocType＋一个时段子表，复用Frappe CRUD/表格/权限/Version**。不采用“把所有规则塞进Manufacturing Settings的JSON”，因为这会让现场维护依赖代码文本，并难以单独限定公司和配置权限；也不采用改工作站排程含义。没有重做账号、组织、表单或审计框架。

## 3. B14最小配置与文件边界（均为拟新增，尚不存在）

| 对象/文件 | 字段与职责 |
|---|---|
| `production_time_rule/production_time_rule.json/.py`、`__init__.py` | `Production Time Rule`，中文“报工时段规则”。原生name作为稳定ID；`rule_name`标题、`company`必填Company Link、`enabled`、非负整数`priority`、可空Operation Link `operation`、`periods`子表；track_changes=1。company仅沿用工单公司隔离数据，不创建新公司/租户模型 |
| `production_time_period/production_time_period.json/.py`、`__init__.py` | `Production Time Period`，中文“报工规则时段”，istable=1；`period_type`为Rest/Overtime（中文休息/可加班），`start_time/end_time`原生Time。只接收分钟精度，非零秒明确拒绝，不静默截断；转换为B04已有HH:mm输入 |
| `production_time_rule/test_production_time_rule.py` | 拟`TestProductionTimeRule`；只测配置持久化、权限、序列化和与已有计算入口衔接，不重跑B0412项全套 |
| 原`job_card/job_card.py` | 新规则控制器可调用现有B04函数；如需共享时段格式检查，只把现有检查提成一个确有配置/计算双消费者的小函数，不另复制算法。不改原生经过分钟/估价语义 |
| `erpnext/locale/zh.po`、最小本地配置脚本`.development/checks/b14_prepare.py`（拟） | 原生中文词条与Role/Custom DocPerm/User Permission最小样例；脚本先检查目标、可重入且不覆盖无关配置。只操作隔离站，记录部署所需步骤，不自动改现有网页或客户站 |

原生表单用标题、启停用、公司、适用工序、数字优先级和可增删时段行；沿C04不新增拖拽排序控件。跨零点、同起止为空、交叠取并集、按priority/name首条命中，均沿用B04。名称排序使用稳定单据ID，显示标题不冒充ID。

有效规则至少明确提供时段行及合法类型/时刻；空时段或没有交集按B04现有语义不匹配，不把无意义的00:00–00:00解释成全天。规则不承载个人工资或标准效率，来源另按B03/B08落实；无单价不能默认成工作站费率或30元。

## 4. 权限和完整规则读取

### 4.1 配置自身

- 用户确认的配置管理员映射拟窄角色`生产配置管理员`；使用原生Role/DocPerm/Custom DocPerm，不授予整套Manufacturing Manager或System Manager作为业务前提。
- 配置维护者只在明确Company User Permission范围内创建、读取、修改规则；业务范围缺失拒绝，不因最后一条限制被删而放开全公司。修改时核原/新公司，不通过移动规则绕过权限。
- 普通操作工、审核人、厂长、仓管默认没有规则全量GET/list/写/导入/分享/导出权；被单张分享不自动拥有全规则读取。运维Administrator是既有管理边界，不用于证明业务岗位权限。
- 用过的规则保留稳定ID；停用代替删除。B08持久化关联启用后，`on_trash`检查所有关联报工，含取消态，禁止删已使用规则；不能只查docstatus=1。无引用规则在明确delete授权下可删，不禁止合理草稿清理。
- 如默认DocPerm/User Permission组合不足，允许在新规则模块补`has_permission(doc, ptype, user=None, debug=False)`和`get_permission_query_conditions(user, doctype=None)`，由原`hooks.py`分别注册`has_permission`与`permission_query_conditions`。这是实际`frappe.permissions.has_controller_permissions:455`及`DatabaseQuery.get_permission_query_conditions:1504`的hook契约，不是只在类里写同名方法便会生效。缺角色/显式公司范围时只收窄拒绝，不借hook扩大DocPerm；查询SQL片段复用原生转义/构造，不把公司值直接拼接或二次字符串格式化。不改Frappe全局权限。

### 4.2 报工所需上下文（消费端条件绑定）

拟内部函数`load_report_time_rules(company, operation)`放新规则控制器，**非白名单**：只接B08从已授权、服务器重读的工单和任务得到的公司/工序；参数不是浏览器传来的过滤器。固定只读该公司启用、全工序或本道工序的规则及其子行，返回完整候选列表。禁止返回其他公司/其他工序配置，禁止任意doctype/fields/filter参数。

该内部读取可用原生get_all取得完整候选，前提是调用方先通过下面的业务授权。此处是明确的窄服务端取配置，**不是宣称get_all自动鉴权**。不切换Administrator、不设置全局ignore_permissions，不把全部候选发给浏览器。B14阶段只验证此内部契约与配置CRUD，不能把它当可调用的操作工HTTP接口。

B08预览/确认共用原R07权限候选`erpnext/manufacturing/permissions.py`中的拟`check_report_permission(work_order, operation_id, user=None)`，不另建第二份scope判断。返回服务器取出的工单、精确工序行、当前有效Employee。必须检查：登录报工动作、父单read、精确parent/operation_id、公司/班组范围、已批准可执行、ALL/DEPT/PERSON任务范围及当前Employee映射。公司/工序均从返回对象取。审批helper仅作已批准门槛，不能代替上述完整授权；旧单返回None则本项目新入口拒绝。

没有候选/没有交集才可形成B04的明确无匹配结果；配置加载失败、表未部署、授权失败、无效数据不得catch后返回`[]`。新确认请求重新检查权限和当前状态；同次调用已验证且未变的身份/数据不重复检查。

## 5. 历史快照与B08字段衔接

快照建立在**人确认、生效事务内**，不是每次预览、每次打开旧页面，也不是修改规则时批量回写。规则修改后新报工用新配置，旧报工读取自己保存的依据；本轮没有授权回填历史单。

| 原Job Card拟新增字段 | 最小含义 |
|---|---|
| `report_shutdown_seconds`、`report_overtime_seconds` | 人工输入的非负整数秒；保存时仍走B04限额校验 |
| `report_effective_seconds` | 确认时B04返回的有效整秒，用于预计工资/效率；服务器只写，不覆盖原作业成本分钟 |
| `report_time_rule` | 可空规则Link；无匹配时为空。关联用于追踪/防删，不能靠当前规则值重算旧报工 |
| `report_time_context` | Code/JSON，只读、不可复制；保存计算版本标识、Asia/Shanghai、匹配/无匹配状态、匹配规则ID/标题/modified/priority/工序范围/当时区间、当次reported/rest及停工/加班限额秒。起止与员工沿用原时间行，停工/加班及有效秒沿上列字段，不再复制一份业务输入或工资账 |

快照只保留当次实际采用的依据，不复制全厂规则库。不匹配记录包含服务器判定时刻、公司/工序范围及“休息0、加班上限=经过时长”的明确上下文；它证明当次实际采用的计算依据，**不承诺重建当时全部未命中规则目录**。计算版本绑定维护源码，不按页面语言/标题改变公式。

字段metadata的read_only/no_copy/allow_on_submit=0只是辅助：B08/B09控制器仍须拒绝外部伪造、覆盖、复制快照；已生效和已取消事实均保留原快照。更正原卡不回写新规则；新更正卡如何选用规则/单价属于B09更正样例，不在本轮静默决定或解锁。原生Version记录配置改动；报工事实来源为当时快照，二者用途不同。

## 6. B08预览与确认契约（拟接口，尚未实现）

所有新方法仍在原`job_card.py`，不建独立服务：

1. 拟`preview_production_report_time(work_order, operation_id, from_time, to_time, shutdown_seconds=0, overtime_seconds=0)`：先调用共用任务授权，再内部读取规则，调用`calculate_report_time`。只返回中文说明、当次采用规则摘要/计算值和`context_fingerprint`，不写报工/库存。此接口须在任务授权最小样例成立后才能白名单化，B14规则配置可独立先完成。
2. 拟`confirm_production_report(request_id, work_order, operation_id, good_quantity, bad_quantity, from_time, to_time, shutdown_seconds, overtime_seconds, context_fingerprint, reason=None)`：参数均有明确含义；无`employee/company/rules/effective_seconds/wage/docstatus`等客户端权威输入，登录Employee与任务来源由服务器取得。仅绑定本阶段的数量/工时确认；工资来源字段未绑定前，不冒称完整B08工资页面已完成。
3. 先按原R07请求键找回/授权，再按既定同工单事务锁重读状态、任务及事实余量；服务端重取规则并计算，对比预览依据指纹。若所用规则/结果变化，明确提示“时段规则已变化，请重新核对后确认”，不按旧预览静默写新结果。指纹只用于识别陈旧预览，不是授权凭证或服务端签名；重试已提交请求按原结果返回，不被后来规则变化改写。
4. 确认事务使用同一份已读取候选计算和写快照，保证快照与本次结果相符；不额外锁全厂规则或建立配置发布平台。规则编辑与报工同时发生的完整先后/重试证据仍归G3，未实测不称完全并发安全。
5. 沿原`Document.insert/submit`即时生效、调用原工单派生链；在受限服务器上下文写快照。不新增中途commit、不调用库存过账、不自动签批。原通用save/submit/Resource/子行/复制入口不得绕过身份、批准、数量及快照保护。

**前置门槛不隐藏：**原`JobCard.validate_job_card_qty:156`统计含草稿的卡批量；`WorkOrder.create_job_card:963/create_job_card:2102`已会生成全量计划卡。逐笔1+1+(6良2不良)再建卡可能冲突；本轮静态发现不是新运行失败。原`update_work_order_data:831`还会保存父工单，窄角色回写及成本字段边界未验。继续按[原F-RPT-01](report-concurrency.md#3-只推进一条最小候选先验证事实粒度)处理计划卡、显式不良、受限派生回写与原记录保留；未通过前不得开放上述确认接口。B14配置不等待这些B08整卡条件，二者不形成循环。

## 7. 最小样例、验收和顺序

沿B01隔离测试站`xgd-test.localhost`，复用已有合成公司/工单fixture；准备两个公司、同公司两个班组、三个工序、配置维护者/操作工/无权者/撤权对照。不复制客户数据、不启用开发/客户审批，不在真实网页偷偷导入样例。

| 顺序/归属 | 必须实际证明的样例 | 通过条件与证据边界 |
|---|---|---|
| P0 B14准备 | 仅加载两个原生新DocType、必要角色与一个规则，保存重读 | 元数据及实际运行源码哈希一致；先让fixture可运行，再写失败断言；不能把新表尚不存在当业务缺陷 |
| P1 B14配置 | 本公司午休12–13、允许加班16–17；工序专用/全工序、停用、非法时刻/类型/非零秒 | 原生CRUD重读后转B04列表；09–17得25200有效秒，停工3600/加班1800得23400；覆盖跨零点保存转换，只测受适配影响的案例 |
| P2 B14权限 | 维护者正例；操作工/厂长/无角色的直接GET/list/子表及写；跨公司、单张分享、撤权 | 只能执行获授权动作，撤掉最后范围不能放开；配置修改有原生Version记录；不把管理员成功作业务通过 |
| P3 B14读取 | 无规则明确[]；两条优先规则完整读取；配置读取异常/非法行 | 不能因get_list隐藏高优先级而改变计算，不能把错误当无匹配；内部完整候选不经公开API返回 |
| P4 B02/B06/B08 | 原F-RPT-01计划10三工序，连续良1、良1、良6/不良2；操作工无工单write/库存write | 独立事实3条、本道良8/不良2、其他任务未完成、入库0、原计划不变；受限父派生回写成立。实际失败保留后才能局部修补 |
| P5 B08预览/确认 | 同一普通操作者通过精确任务读取；换任务/班组/员工状态/撤权；客户端规则/有效秒伪造 | 有权预览0业务写；确认服务端计算；无权/未批准/停止/旧非审批单拒绝，无部分成功；不因客户端声称“已校验”放行 |
| P6 B08快照 | 先以午休12–13确认09–17，再改为12–14或停用；再打开/导出原记录 | 原有效25200及规则快照不变；新报工按新规则得到21600或无匹配28800；原记录查询不调用当前规则覆盖；旧预览确认需重新核对 |
| P7 B08/B09 | 直接PUT/submit/子行改快照、复制、取消后删除原记录、删除已用规则、失败回滚、同键重试 | 原始依据保留，复制不带事实；无残留、同键回到原结果。沿原G2/I01/I06，实际HTTP并发/I03～I05仍独立留G3，不用顺序单测替代 |
| P8 B14/B08中文PC | 配置管理员用原生表单保存时段；普通操作工在原Job Card报工页查看规则、有效工时并确认 | 中文提示、无规则说明、超限数字及旧预览提示可操作；本阶段未完成前不称网页可用。手机/弱网仍归B13 |

下一批先做P0～P3及B14配置中文PC子项，范围达到即结束；P4可按原任务独立推进，不要求B19整卡完成。P5～P8中B08部分在P4及相应防重/历史保护最小门槛成立后接入。完整B14编号/默认值、B08报工整卡、B09/G2/G3、B04其余数量/G1均不提前关闭。

## 8. 命令、允许改动与结束条件

以下是**未来文件/测试实现后的执行命令**，本轮未运行、不承诺当前可通过。不要用缺表/未收集到测试当通过，也不把已有B04类改名重跑：

```sh
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json run --rm --no-deps -T bench bench --site xgd-test.localhost reload-doc manufacturing doctype production_time_period
docker compose -f .development/compose.json run --rm --no-deps -T bench bench --site xgd-test.localhost reload-doc manufacturing doctype production_time_rule
# 先生成并核对本批真实源码清单；准备脚本拟只补必要配置，不做全量初始化。
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/b14_prepare.py
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.production_time_rule.test_production_time_rule --case TestProductionTimeRule --skip-test-records --skip-before-tests
```

B08拟新增有限类放原`job_card/test_job_card.py`，名称`TestProductionReportTimeContext`，沿同一run-tests命令换module/case。先实现P4对应原F-RPT-01测试，再验证预览/快照/确认；不能直接使用大权限管理员成功代替。普通HTTP在最小fixture和只连隔离站的脚本准备后再绑定实际CLI；本轮不虚构不存在的可运行HTTP脚本。

允许产品范围：第3节两个新原生DocType及其测试；原`job_card.py/.json/.js/test_job_card.py`；确需权限共用时原R07已拟的`erpnext/manufacturing/permissions.py`及`hooks.py`必要注册；历史/派生联动只沿原`report-concurrency.md`文件与字段白名单。新增字段跟随原生元数据/可复现迁移，不手改客户库。Frappe所有源码、库存估价、制造排程/工作站时段含义均禁止修改。

本轮R07结束条件：实际源码入口/哈希可核、C14落定、结构/读取/快照/接口/失败样例及条件边界写回原卡、产品差异未变、白名单发布回读。不是B14/B08运行验收；本轮不新增配置、不开放接口、不重跑B04/Q05/B19，G1/G2/G3继续保留。需要改全局框架、第二套任务/库存账、放宽整单权限或出现白名单外派生修改时，记录实际证据并止于对应子项，不无限扩卡。

## 2026-10-27 B08 本批实现回链

实际证据见[实施记录](../B08/implementation/run-record.md)。原Job Card每笔事实/唯一`report_request_id`/`report_payload_hash`、服务端`report_time_context`与秒数字段；原Work Order Operation增加`report_scope/report_department/report_employee`。JobCardTimeLog只补已确认父卡保护；WorkOrder只放行服务器上下文中的本工序派生字段。没有新增permissions模块、事实表或Frappe改动。

实际入口均在`job_card.py`：`get_production_report_tasks`、`preview_production_report_time`、`confirm_production_report`、`get_production_report_result`、`correct_production_report`；内部`_report_task/_report_context`复用原公司/班组/状态检查，`_report_time_context`复用B04计算和B14读取。中文原WorkOrder弹窗及JobCard依据查看，不另建页面系统。`work_order.py:validate_production_execution_state`由原判定拆出复用，旧请求找回先查历史权限，新事实仍查执行状态。

实际最小更正为原生cancel/amend，起止不变沿用原时段依据；有提交库存单或后工序事实即拒绝。原生子工序配置明确拒绝，不新增子工序业务。三笔、窄回写、同键真实HTTP、快照旧新、原卡/子行保护及受控回滚已有证据；全部权限组合、完整逆向/跨对象并发、现场10秒及G1/G2/G3未通过。旧节中的“拟新增/当前不存在”为实施前历史，不代表本批状态。

<a id="2026-10-28-b08-单价与效率续接来源待确认"></a>

## 2026-10-28 B08 单价与效率续接：来源与实施绑定

**用户确认：**选择“按工单工序填写并随审批冻结”，见[C16](../../docs/决策与范围.md#c16--报工单价与标准效率来源2026-10-28)。此前来源待定和未绑定的描述是历史缺口；本包已实施，并按下述原卡/记录回填受控和真实PC证据，本次单价/效率包已按限定范围收口。C13公式不变，`hour_rate`仍为作业成本，`production_capacity`仍为并行卡数，排程分钟不替代标准效率。维护沿现有工单发起人草稿/退回权限，不自动赋予时段配置管理员或普通报工人员工单write。

以下字段、存储和舍入是本轮技术选择；用户确认的是来源，不表述为用户另外指定了实现类型或舍入规则。只在原生文档增加必要字段，不建主数据计价平台、工资账或配置发布框架。

| 原生对象/字段 | 类型与语义 | 写入和冻结边界 |
|---|---|---|
| Work Order Operation `report_wage_mode` | Select：空、`hourly`、`piece`；中文显示未配置/计时/计件 | 沿工单发起人草稿/退回编辑；送审后冻结 |
| Work Order Operation `report_wage_rate` | Data：有限非负、小于1,000,000,000、最多六位小数；空与明确0不同。计时为币种/小时，计件为币种/工单库存单位；模式和单价须成对 | 与模式一起冻结；不修改原`hour_rate`成本 |
| Work Order Operation `report_standard_efficiency` | Data：可空或0，有限非负；单位为本工单库存单位/小时。缺失或0不产生达标率 | 沿原草稿/退回权限填写，随送审冻结；不从成本/排程字段推算 |
| Work Order Operation `report_wage_currency` | 只读币种字段，来源`Company.default_currency` | 工单草稿由服务器带入，送审冻结；客户端不得指定另一币种，当前公司币种改变不改已冻结工序 |
| Job Card `report_metrics_context` | 只读JSON：保存当笔来源对象/工序行、版本`B08-metrics-v1`、模式、单价、标准、库存单位、币种及实际采用的金额精度 | 确认服务器写入；按既有快照/原记录保护拒绝通用改写，不回填旧笔 |
| Job Card `report_estimated_wage` | 只读Data：按该笔币种精度保存的预计金额；缺配置为缺失，明确零价为0 | 与依据同一确认事务写入；不形成工资结算账，不接受客户端金额 |

**计算和精度：**继续只用`job_card.py:calculate_report_metrics`的C13公式。实际效率/达标率不存百分比字段，从当笔良/不良、有效秒及保存的标准依据计算。`plan_quantity`可为None，无计划上下文时未清数量/比例为None；无关的`completed_tasks/total_tasks`、`issued_quantity/required_quantity`可缺省，每对须同时提供或同时缺省。未清/任务/物料缺上下文均不计算，不塞虚构0，不复制公式。预计金额精度按Frappe `model/meta.py:get_field_precision`的Currency口径取得：字段显式precision优先，其次系统currency_precision，再由币种/系统数字格式取得；确认时捕获币种及实际采用精度，历史沿保存精度。只复用该精度入口，不改Frappe；预计金额采用Decimal `ROUND_HALF_UP`显示和落快照，单价保持六位输入能力，不先按金额精度截断单价。

**原API和页面：**`preview_production_report_time`保留现有时间参数，增加可选成对良/不良数量并返回metrics；旧的纯工时调用仍可使用。`confirm_production_report`继续从服务器授权任务及工序取得来源；`context_fingerprint`覆盖时段、价格、标准、库存单位、币种和金额精度依据。良/不良变化触发重新预览；旧依据确认被拒绝且不部分保存，不接受客户端工资/标准/币种/精度作为权威输入。`get_production_report_result`及原Job Card依据弹窗按保存依据重读，旧记录无指标依据显示“未记录”，不使用当前配置填补历史。仍保留原公司/班组/Employee/对象read/审批状态边界，不通过本包放宽权限。

**更正：**沿`correct_production_report`和现有cancel/amend门槛，仅同工单同工序，沿原报工单价/标准/币种/精度及C15时段依据，按更正后数量重算新预计金额；原记录与原金额保留，不复制旧金额，不因当前配置变化改旧笔。完整库存/后工序逆向和G3并发不在本包增加。

**允许文件：**只沿`.development/repos/erpnext/erpnext/manufacturing/doctype/`下原`job_card/job_card.py`、`job_card.json`、`job_card.js`、`test_job_card.py`，原`work_order/work_order.py`、`work_order.js`、`work_order_operation/work_order_operation.json`；确需中文显示时沿原`erpnext/translations/zh.csv`。上述文件沿累计交付白名单；因下述子行冻结真实失败，本次补入原`work_order_operation/work_order_operation.py`，仅保护本轮新增计价来源。最终交付源码清单须纳入该原控制器，不沿用旧24文件数冒称完整。本包不改Frappe、Operation/BOM Operation主数据、库存成本或排程。保留已有维护checkout及累计补丁；每次运行前核对实际源码清单，不能把旧交付SHA当新实现证据。

**子行保存绕过的实际失败及最小范围：**`TestProductionReportMetrics.test_direct_child_save_cannot_bypass_pricing_freeze_or_validation`调用真实`frappe.client.save`保存Work Order Operation，草稿`report_wage_rate=-1`及送审待审核`report_wage_rate=99`均未拒绝；待审核样例父修改版本不变、子行变化。先1项16.647秒FAIL，扩展后1项18.458秒FAIL3（2个拒绝断言和保存前后差异），最终事务回滚，日志见child-first.log（仅本地保留；见 publication/evidence-index.json）、child-both-first.log（仅本地保留；见 publication/evidence-index.json）。这是本次新增字段校验/审批冻结的实证缺口，不是旧任意子行/完整G2验收。

原`work_order_operation.py`已补最小入口保护：直接子行save/insert改变`report_wage_mode/report_wage_rate/report_wage_currency/report_standard_efficiency`，或带这些来源的子行改变parent/operation关联时拒绝，中文提示通过父工单工序表编辑。父单原生保存路径继续执行现有`validate_report_pricing`和审批规则，不复制公式/校验框架，不修改Frappe。修后子行拒绝、父单来源校验/审批冻结、正常计时确认共3项28.415秒通过；扩展insert/改工序/清空来源的同一方法1项11.041秒通过，父单前后及四张规则/员工/权限表回滚一致，见child-fixed.log（仅本地保留；见 publication/evidence-index.json）、child-entry-boundaries.log（仅本地保留；见 publication/evidence-index.json）。另以配置浏览器同cookie及合法CSRF执行独立真实HTTP，将子行单价改为-1返回403/PermissionError并命中计价保护，原值及父子修改时间不变，见[config-http.json](../B08/metrics-20261028/config-http.json)；此项独立于内部client.save测试和页面操作。

**验证入口与实际批次：**原`test_job_card.py`的`TestProductionReportMetrics`由本地`.development/checks/b08_metrics_tests.py`（容器`/b01/b08_metrics_tests.py`）仅连接隔离测试站`xgd-test.localhost`运行，可指定方法或默认运行该类。当前10个真实方法名：`test_hourly_preview_confirm_and_reopen_use_frozen_source`、`test_piece_correction_recalculates_with_original_price`、`test_unconfigured_is_unknown_and_legacy_snapshot_not_backfilled`、`test_zero_rate_and_zero_seconds_remain_explicit`、`test_source_validation_and_approval_freeze`、`test_stale_source_forgery_and_revoked_access_reject_without_facts`、`test_amount_precision_and_unrelated_metrics_are_not_invented`、`test_piece_rounding_captures_native_currency_precision`、`test_direct_child_save_cannot_bypass_pricing_freeze_or_validation`、`test_saved_currency_precision_survive_current_settings_changes`。10方法已分批覆盖通过，未声称最终10方法一次全类通过；具体参数、源码清单及原始输出以[本轮记录](../B08/metrics-20261028/run-record.md)为准。

```sh
# 默认全类是runner用法；本轮实际分批方法与日志沿运行记录，不累加重复批次。
docker exec xgd-b08-check env/bin/python /b01/b08_metrics_tests.py
# 已运行的子行定向入口；后续扩展仍为同一方法，不计新增方法。
docker exec xgd-b08-check env/bin/python /b01/b08_metrics_tests.py test_direct_child_save_cannot_bypass_pricing_freeze_or_validation
docker exec xgd-b08-check env/bin/python /b01/b08_metrics_tests.py test_saved_currency_precision_survive_current_settings_changes
```

必要元数据加载沿原`reload-doc manufacturing doctype work_order_operation`及`reload-doc manufacturing doctype job_card`，不重做全量依赖初始化；加载命令、前后状态和真实结果必须记录。普通账号HTTP及Playwright CLI中文PC使用本包新合成样例，脚本/动作名实际存在后记录，不虚构已运行命令。

**已核结果与剩余：**首次接口缺参、首批复制草稿fixture错误及子行真实失败均保留。修后接入/舍入、子行/父保存、实际当前公司币种/原生金额精度变化的历史保持分批通过；设置变化时旧笔币种/精度2/20.00保持、新预览20.000、旧指纹拒绝且设置回滚一致。受影响原指标/规则快照/跨用户结果5项18.687秒通过。前端6红→6绿和刷新回归通过，重复最终check不计新覆盖；Chrome计时20.00、计件80.00的确认/重开、数量刷新及旧记录历史未记录已有页面证据。新增窄角色发起人从中文原生配置页保存/重开独立草稿，计时10/标准10/CNY与公司一致，清缓存后计时/计件选项中文生效，见[config-ui.json](../B08/metrics-20261028/config-ui.json)；同账号独立HTTP拒绝已验。构建/测试/网页三处最终源码清单均33份一致，累计25份修改源码及镜像build已核，见[built-source.json](../B08/metrics-20261028/built-source.json)、[runtime-final-source.json](../B08/metrics-20261028/runtime-final-source.json)、[web-final-source.json](../B08/metrics-20261028/web-final-source.json)。源测试站11表哈希保持；UI站11表全部原有行/捕获列保持，库存3表无新增，新增合成样例及报工保留，见[ui-retention-summary.json](../B08/metrics-20261028/ui-retention-summary.json)。公开产品提交`d90f568b6894f44c4adee5310a1d4fe4f5115ec4`已fresh clone核对311文件/310内容哈希及25份源码，差异0，见[回执](../发布/2026-10-28-d90f568-remote.json)，本包限定范围收口；不据11表核对宣称全库审计。

**本包做/不做/通过条件和8组必要验收只维护在[原B08当前子节](../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-单价与效率来源核对)**；本节不复制第二份清单。历史缺口与执行证据沿[本轮记录](../B08/metrics-20261028/run-record.md)。仅关闭本包对应实现/验证/保存过程；34卡统计、整卡、人工现场、手机、G1/G2/G3、Z01及后台周期边界不变。下一入口沿原卡真正未完成绑定余项，未变化旧项及本包不重跑，OpenSpec不归档。
