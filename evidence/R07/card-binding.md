> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R07｜首批代码入口、改动范围与验收绑定

**2026-10-27 B19批准后变更（当前）：**按[审批绑定补充](approval-binding.md)实施V04/V07服务器限定子项，18项受控验证通过；见[本批证据](../B19/approved-changes/run-record.md)。新增岗位决策已确认：批准后取消/停止仅生产厂长且填原因。原生失败先留证再局部修补，不改Frappe、不重建事实。下一步新动作HTTP、附件/依据还原及中文网页；G1/G2/G3和活动计时收尾保留。

**2026-10-27 B19真实HTTP（上一批）：**已按审批绑定的专用合成副本完成真实HTTP与原生同步批量拒绝验证，见[HTTP证据](../B19/http/run-record.md)。源测试库11张业务表未变，产品补丁未变；38请求含1个已保留并修正的样例前置条件错误，不能写全量38通过。下一步按原绑定补批准后变更、终止/已有执行停止规则，再补附件、依据还原及中文网页；G1/G2/G3保留。

**2026-10-27 B19历史保护（上一批）：**已按第5节允许范围接入原hooks扩展点，14项受控子项及正常审批回归1项通过；见[证据](../B19/entry-history/run-record.md)。附件、完整依据还原、批准后完整变更及G1/G2/G3不据此通过。

2026-10-26。本轮按用户要求只绑定**数量、退料、报工原记录、权限与并发**，并加入简体中文交付约束。**R07部分完成；未改产品代码、未运行新的业务测试，未解锁全部B/A/Z卡。** 详细步骤已写回[原业务任务卡](../../docs/任务卡/02-生产与物料闭环.md)，本页是索引和共用边界，不另建一套TODO。

**任务卡一致性更新（历史，2026-10-26）：**用户再次限定本轮只改计划与证据，B01仍为下一步。分项前置、验收归属和失败停止规则以[总TODO](../../docs/开发TODO.md#分项交接与停止规则)为准；下文“门槛”区分开工绑定与实现后验收，不能以最终验收尚未通过为由禁止必要的限定实现。

**B01后续执行更新（2026-10-26）：**用户已授权并实际执行独立中文环境。环境子项已完成，原生仓库测试基线在依赖装载缺`Payment Gateway`，未通过；B01整卡保持部分完成。具体以[B01记录](../B01/run-record.md)为准。下文“本轮未执行”描述R07绑定阶段；G1/G2/G3没有因环境建立而通过。

**B02/B10后续执行更新（2026-10-26）：**最小真实fixture已可执行，三个辅助读取权限与库存单位子项已局部修补；结果以[B02](../B02/run-record.md)、[B10](../B10/run-record.md)为准。下文静态绑定和R05失败保留为历史，不改写为未修或全部通过。G1/G2/G3仍未满足，R07仍部分完成。

**2026-10-27 B19续接（上一批）：**审批核心及执行准入已有隔离受控子项，见[B19记录](../B19/run-record.md)与[执行门槛](../B19/execution-gate/run-record.md)。整卡与G1/G2/G3未通过，下一步仍在B19补HTTP/已绑定变更及记录保护，不重新选型。

**2026-10-27审批续接（此前）：**本轮已完成C10业务确认、五项目审批代码有限核查与B19核心静态绑定，详见[审批绑定](approval-binding.md)及[源码核对](approval-source-check.json)。原生Workflow配置/记录/权限构件可复用，直接提交、自批、旧页面版本及历史保留须限定补强；尚未启用流程、实现产品或运行测试。下一步建议B19最小样例与原生边界验证，G1/G2/G3继续保留。以下2026-10-26顺序为历史，不覆盖当前入口。

## 1. 结论与执行顺序

| 顺序／所属原卡 | 本轮绑定结果 | 开始实施前条件／停止点 |
|---|---|---|
| 1．B01隔离开发环境子项 | 复用固定镜像、R05已运行的Compose结构、原生Bench和测试设施；新增开发工作区与中文站点，不改评估库 | B01已取得固定完整源码并验证Web/Bench关键文件、分库、中文登录及启停；原生测试基线未通过。C06未定不阻塞合成环境，但客户适配/团队CI仍未绑定 |
| 2．B02辅助接口权限、B10实耗单位子项 | 真实入口和失败样例明确，可在环境与最小样例就绪后局部修补 | 只关闭对应子项；不能据此关闭整个权限卡或领料卡。源代码版本、角色正例和反例都要留证 |
| 3．B04数量、B06/B08/B09事实承载前置验证 | 已绑定计算链及一个原生事实方案，以下G1/G2尚未通过 | 先做限定验证，再冻结实际字段/完整接口；不先铺全部页面、AI或另造事实表 |
| 4．B11退料、B09/B10～B12同工单并发 | 原单关联、额度规则、请求防重及锁顺序方案已限定 | G3真实入口/合法链/锁序/范围先绑定，再实施提交保护；并发验收通过才关闭。退料生成可先独立修，不称闭环完成 |
| 5．B13中文必要操作 | 进行中工单退料入口、库存设置读取、请求结果恢复已定位；中文配置机制已核 | 依赖已正确的业务入口；桌面小屏不替代真机，扫码/弱网另验 |

先从B01开始，是为了保证后续测试运行的是**改动后源码、正确中文配置和独立样例**；随后用已复现的单位/权限反例验证小范围修补，再验证两项决定底座是否仍合适的关键适配。不是重新安装比较所有候选。

## 2. 固定版本与复用方式

- ERPNext `v15.124.1 / 4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；Frappe `v15.124.0 / f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab`；Bench `5.31.1`。
- R05 ARM64镜像：`frappe/erpnext@sha256:4160d3c77aafb41c7770aad3daa67254a13f8750765ee83d632434ed564a4834`。本轮从已停止的R05容器复制只读源码至快照（仅本地保留；见 publication/evidence-index.json），核心文件blob与R05记录一致，身份与范围见[清单](source-manifest.json)。不是可编辑开发仓库，也不证明整个镜像与Git逐文件相同。
- **实现方案：维护一个ERPNext分支，局部改原控制器、原DocType元数据、原生hooks及对应测试。Frappe保持原版。** 不为包装这些差异先建扩展App、通用中间层或第二套MES；后续确有打包需求再依证据绑定。源码许可、上游变更合并与交付归Z01/R01，不凭可复制认定全部许可审查完成。
- 只配置不足：R05已证明单位汇总、可超退、原记录删除和辅助权限缺口。重写整套制造/库存成本更高且没有必要性证据；所以先限定ERPNext业务层补丁。t3rik/OpenMES本轮只作已有设计参考，没有复制其代码。
- 直接复用：账户、角色、单据、库存账、事务、取消修订、列表、表单、翻译和测试runner。局部新增：只有已证明缺失的业务身份字段、动作保护及必要小函数；新增名称在分项文档均标“拟新增”，不是现成API。

## 3. 四类问题的唯一归属

路径相对ERPNext仓库；现有文件在快照的`erpnext/`下可核查，详细签名/行号见对应绑定。Frappe源码仅为只读依据。

| 问题 | 现有权威入口／最少改动 | 验收证据与未解锁项 |
|---|---|---|
| 数量／单位 | `manufacturing/doctype/work_order/work_order.py`的`set_required_items`负责最终需求；`update_consumed_qty_for_required_items`改为库存单位汇总。`stock/doctype/stock_entry/stock_entry.py`保留`set_transfer_qty`及库存账；超额领料也统一比较库存单位 | Q05需求/保存/库存同为0.0002；U01消耗0.5g后工单为0.0005kg，取消后恢复。**全程Decimal及材料损耗来源未闭合**。见[数量与退料](quantity-return.md)第2/3/5节 |
| 退料 | `work_order.make_stock_return_entry`、`stock_entry.get_available_materials/get_stock_entry_data`及StockEntry提交校验；复用`against_stock_entry/ste_detail`追原领料行。余额按本工单、实际物料、在制仓、库存单位计算 | 领10退2，再生成8；耗7后只可退1；本单余8、仓内他单另有10，退9仍拒绝；错原单、重复行、并发、取消回滚均验。共享拆解/批序号调用保留回归。G3前不宣称提交安全 |
| 报工原记录 | `job_card.py`及Time Log/Work Order生命周期；候选为工序任务承载在Work Order Operation、每笔确认生成原生Job Card、原生cancel＋amend全冲重报；保存原卡和时间行 | 计划10连续1＋1＋(6良2不良)，任务计划不变、良8不良2，无自动补不良；更正10→8原卡仍10，新卡8关联原卡；普通/批量/子行/父删除都保护。见[事实与并发](report-concurrency.md)，G2尚未通过 |
| 权限／并发 | B02用原生Role/DocPerm/User Permission，修`get_operation_details/get_operations/get_job_details`等直接读取；B09请求身份放Job Card。所有改变同工单余额/事实的入口共享“工单先锁→重读→校验→原生事务” | 普通最小角色正例、越权/撤权/冒领身份反例；余2并发各2只能一笔，各1必须两笔；丢响应找原结果，故障零残留。权限、事实和库存互相调用一个规则，不各写一套。见[权限](permissions.md)与[事实与并发](report-concurrency.md) |

中文词条和必要错误提示随所属卡修改；统一配置见[中文绑定](chinese-interface.md)。无需英文产品版本，保留上游英文代码/字段标识。

## 4. 三个明确门槛：先验证，失败就停受影响项

**统一先后：**先把该次试验的真实输入、接口/字段、允许修改和预期绑定，随后在B01隔离环境作限定实现与验证，最后按结果决定固化或停止。G1/G2/G3的运行通过是相应实现的验收结果，不是必须预先存在的开工证据；未绑定部分仍不得猜测实现。本轮没有执行这些步骤，也不新增试验卡。

### G1：十进制及材料损耗（B04/B07）

1. 复用R02 Q01～Q05、U01；核原始六位输入、BOM单层/展开、父项基数、中间类型、最终四位、保存重读和下游库存取值。先定位每次`flt`转换，不能在已经算过的float外套Decimal就宣称全链正确。
2. Q03材料损耗字段当前未绑定；BOM `process_loss_percentage`是成品损耗，不能替用。先确定原数据可否无歧义承载；确无字段时，只给BOM原料行最小字段方案及消费位置补绑，不能新建BOM模型。
3. 合格条件是当前规则可在制造/用料局部实现并证明保存不破坏口径；若必须改Frappe全局数字处理、全库存估价或新建并行计算账，停止此项并在R06记录这一差异。Q05单例通过不能解除G1；没有新的有限方案/输入/决策，不重复试验或重装候选。

### G2：逐笔事实、任务计划和最小角色（B02/B06/B08/B09）

1. 按[事实绑定第3节](report-concurrency.md)的F-RPT-01验证一个方案；先处理原生自动全量Job Card与逐笔卡不能叠加的问题。不同任务计划、显式不良传向库存、工单首报开工及取消后的汇总/日期必须明确，不能只改标签。
2. 使用无父工单结构编辑权的普通操作工。现有`JobCard.update_work_order_data → wo.save()`仍检查Work Order write；R05宽角色成功不证明窄角色可用。先限定系统派生回写方式，验证正常报工与禁止直接改工单同时成立；不通过全局绕权或放开工单编辑来消除错误。
3. 通过后才能冻结Job Card请求字段、首次确认时点、逐笔完整参数和Work Order Operation任务scope；未绑定的计价/工时字段仍回B04/B08。不能拿带省略号的候选签名当成可直接开发的最终接口。
4. 失败若需要第二套事实/任务账或修改共享框架，停止受影响项，保存反例、必要变化与代价；R06仅更新该项差异，待新的有限方案/用户决策再推进，不重跑同一失败或直接转成大范围自研。未证明前保留原用户需求，不降低精度、历史保留或权限要求。

### G3：一个锁顺序覆盖所有必要入口（B09/B10～B12）

1. 统一覆盖报工确认/更正、计划/结构改变、领/退/耗/成品的提交与取消。先锁同工单，再读取最新事实，最后沿原生事务完成；不能在Job Card已锁之后再用它等待工单写锁。
2. 对通用PUT/submit/cancel，优先在ERPNext制造控制器早期拒绝非法旁路，不另建全站拦截层。真实业务仍需有合法原生入口，不能为了防并发封死所有草稿操作。库存提交/取消已有不同写入顺序，必须一起核实后才能放行退料提交修补。
3. 重读须证明看到前一事务已提交的余额；只加`for_update`文字不是证明。新请求键唯一、原记录及派生在同事务；没有中间commit，不吞异常，不无限重试。
4. **开工前**补齐真实入口表、合法调用链、锁序、允许修改、测试输入和判据；已有测试runner可复用，待编写的HTTP测试脚本明确归属，不以它尚未写完阻止限定实现。**实现后**执行同工单并发、不同工单共享工作站、退与耗/取消竞争、I05响应丢失、I06故障回滚，分别保留原始结果；运行结果不全则不得关闭或宣称并发安全。尚无锁图，不断言R05死锁根因已完全定位。本轮G3开工绑定与运行验收均未完成。

## 5. B01环境子项的具体落点

**现有可复用文件：**`.evaluation/r05-erpnext/compose.json`、`compose.web.json`及[R05运行记录](../R05/run-record.md)；已存在服务db/redis-cache/redis-queue/bench/web、原镜像与Bench工作目录`/home/frappe/frappe-bench`。这些是模板和历史证据，不能直接在旧站点跑改造回归。

**B01已创建并验证（后续更新）：**`.development/repos/erpnext/`为上述commit的完整维护checkout；`.development/compose.json`沿用已验证结构并使用项目名`xgd-dev`、独立卷；必要构建/源码挂载配置在同目录，凭证单独受限保存且排除版本管理。新站点为`xgd-dev.localhost`（中文操作）和`xgd-test.localhost`（上游测试隔离，测试会产生自身测试公司）。不新建第三套账号/业务服务。本机开发端口为`127.0.0.1:18086`，B01新卷/新网络与R05隔离；详见[B01配置说明](../../.development/README.md)。

实施步骤：取得固定源码→核HEAD和依赖与镜像相容→写最小隔离配置→原生建站/安装ERPNext→向导设置中国/zh/上海/CNY及普通测试账号→记录运行模块实际路径与文件哈希→登录、重启、回读验证→停机方法。挂载或构建必须覆盖实际Python导入和前端资源；仅checkout改了而容器仍跑旧包不算绑定。B01先证明运行本checkout，不为环境验证另写业务补丁；B02/B10真正改动后必须重新核变化文件并测相应反例。具体建站参数复用R05成功记录与已读`frappe/commands/site.py`，实施时凭证不得写入证据或命令回显。

以下环境命令已在B01执行；其原始记录与结果见B01，不能用本段命令文本替代运行证据：

```sh
git -C .development/repos/erpnext rev-parse HEAD
docker compose -p xgd-dev -f .development/compose.json config --quiet
docker compose -p xgd-dev -f .development/compose.json ps -a
```

容器Bench目录内执行（配置完成并确认改动后源码生效后）：

```sh
bench version
bench --site xgd-test.localhost set-config allow_tests true
CI=1 bench --site xgd-test.localhost run-tests --app erpnext --doctype "Stock Entry" --test test_warehouse_user --failfast
```

B01实际显示：新站点用`--module`未准备所需fixture，改原生`--doctype`装载后仍缺`Payment Gateway`，因此该测试基线未通过；CI=1保留失败退出码。测试只在隔离测试站点启用。分项反例、受影响原生回归与命令分别见四份绑定；**拟新增测试尚不存在**，不能用“未收集到测试”当通过。源码检查/文档检查与应用测试分别登记。团队CI仓库/权限仍未定，不承诺已接CI或先建空CI框架。

## 6. 公共允许范围、证据与结束条件

- 所有产品修改限于分项列出的ERPNext制造/库存函数、必要元数据/中文提示、原生hooks配置及对应测试；生产写权限、数量和事务规则各保留一个实现。不同卡碰同文件按函数归属串行合并，不并行改同一函数。
- 本轮计划文件和只读快照可写；原R05环境/数据/证据、Downloads原稿、Frappe框架、库存账/估价核心、客户系统均不改。不执行采购、迁移、删除、额外候选部署、AI实调或全面UI重做。
- 后续每项记录源码提交与diff、运行文件身份、环境配置、合成输入、普通角色、真实命令/返回、前后持久化状态、预期、失败与限制。新前缀/新证据目录，不覆盖R05结果；已通过未变化子项不无理由重跑。
- 原卡共33张不增加。R07绑定收口时R00～R06共7张完成、R07部分完成、其余25张未完成；B01执行后的当前状态为7张完成、R07/B01部分完成、另24张未完成。子项已绑定不等整卡解锁，以上G1/G2/G3及未涉及字段/交付项仍为条件。没有人天、费用或节省比例估算，C06未定及这些技术门槛是明确依据。
- 本轮停止于入口、范围、验收和门槛落文档；不以撰写计划宣称数量/权限已修复。下一步可执行B01环境子项；业务修补按环境、最小样例和上述条件逐项进入。

## 7. 首次绑定核对记录（历史）

首次绑定时用本地脚本解析原卡/总表、依赖、Markdown本地链接和源码测试函数，并计算快照哈希；结果见[历史文档与身份核对](document-check.json)。当时33张卡/33个唯一ID，7完成、R07部分完成、25未完成；**显式依赖表未发现图环，此结论不覆盖卡内语义依赖**。当时115个本地链接/锚点可定位，991个快照源码/资源文件身份一致；哈希数量不表示逐文件业务审查，测试名存在不表示已执行。本次仅改文档，不重复源码哈希或业务测试。

独立只读复核已纳入两项实质修正：最小操作工无父工单write与原`wo.save()`的冲突；直接Work Order Operation子行改删的保护入口。它们仍在G2/G3及对应测试门槛内，不称已经解决。`docker ps -a`按R05项目过滤回读，web/db/两项Redis均为exited；本轮未启动这些业务服务、未连接数据库。

**本次语义审查补充：**修正B02整卡等待下游的反向依赖，以及G3要求先有实现后测试结果才允许实现的自锁；并明确选型回退只记录受影响差异，无新依据不重启比较。结果见[本次任务卡审查](scope-review.json)。当时仍是7完成、R07部分完成、25未完成；未新增产品完成结论。


## 2026-10-29 B05/B06/B07空明细与人工确认生成绑定

用户已明确授权本绑定完成后连续实施及验收。固定ERPNext/Frappe基线沿第2节，开工公开main为4925f5bf14d94338ef4b305a41c63c1dd54a915d，维护累计25份/e15fba；保留维护分支及全部旧数据，不另建worktree或安装依赖。

**做什么：**仅对本流程新审批工单，建单保存为空工序/用料；草稿/退回发起人预览原BOM展开，确认后生成计划行。**不做什么：**不接活动计时收尾、结束差额、完整任务编辑/复制、全局BOM回写、库存链、AI、手机、客户配置或后台周期。**通过：**原CASE-01的0/0→3任务/1用料行/需求5，重复不追加；权限、陈旧预览/来源、冻结及失败零副作用；普通岗位中文PC保存/预览/确认/重开。

| 归属 | 真实入口与限定改动 | 验收 |
|---|---|---|
| B05空明细 | `erpnext/manufacturing/doctype/work_order/work_order.py:WorkOrder.validate`不为审批工单空表自动补用料；`work_order.js:bom_no/qty/use_multi_level_bom`在本Workflow不自动生成；原非审批调用保持 | 新建保存重开0/0；必填/数量及审批校验保留，空明细不能送审 |
| B06/B07计划生成 | 拟新增同模块`preview_production_order_details(work_order, expected_modified)`、`confirm_production_order_details(work_order, expected_modified, fingerprint)`；复用`get_items_and_operations_from_bom/set_work_order_operations/set_required_items`，不复制数量算法或加元数据/事实表 | 两入口必须read/write及原公司/班组授权，当前草稿/退回且本人发起；BOM需read。预览不保存；确认工单先锁并重读，按原save事务保存 |
| 陈旧/防重复 | 预览指纹为已保存输入、BOM版本及原算法生成的相关计划字段；确认重新展开核指纹。当前明细与该预览相同时返回同单/同明细且不再次save；已有不同明细拒绝自动覆盖；空表时核modified后首次生成 | 拒绝量/BOM/路线/状态/权限变化；重复不追加；原生Job Card/Stock Entry不生成，不把该有限幂等当完整G3 |
| 页面 | 原`work_order.js`增加中文预览及确认操作，要求先保存；展示工序/用料及数量、单位。只给本人草稿/退回显示，但后端也检查；已有不同明细须先人工核对，不隐式替换 | 普通发起人中文PC新建/保存/预览/确认/重开；取消预览无变化；送审后入口拒绝 |

**允许产品文件仅3份：**原`work_order.py`、`work_order.js`、`test_work_order.py`；不改Frappe、BOM算法、Job Card或库存。检查脚本仅`.development/checks/b05_details_tests.py`与`b05_details_ui_fixture.py`及本包页面脚本；本地凭据另放private排除公开。无元数据变更，不reload-doc/全量迁移。测试容器`xgd-b08-check`和网页`xgd-b08-ui`复用；只启动本项目既有DB/Redis/保留容器。真实运行源文件逐份核哈希，不以镜像tag当证据。

**测试与命令（拟新增测试先红后绿）：**原`test_work_order.py`新增`TestWorkOrderExplicitDetails`，复用`TestWorkOrderApproval`的真实合成fixture/rollback。覆盖`test_empty_draft_stays_empty`、`test_preview_confirm_replay`、`test_stale_basis_and_order_rejected`、`test_scope_and_frozen_rejected`及确认写入失败回滚。命令为`docker exec xgd-b08-check env/bin/python /b01/b05_details_tests.py`；脚本直接加载该类，不递归装Payment Gateway，确认实际测试数且失败退出非0，最终rollback核旧11表。只补受影响原审批正常流程/数量保存回归，不重跑B08/I03～I06等不变子包。页面使用Playwright CLI独立会话和既有合成站，新样例不重放旧写入。

**来源复用：**原R03～R06五项目固定来源及审批复用核查继续有效，不重装/重选。实际使用ERPNext原Work Order、BOM、权限、事务、表单和测试；t3rik/OpenMES仅原设计参考，快格云/qcadoo原许可/可取得性边界保留，未拷其他项目代码。纯配置不能阻止`WorkOrder.validate`空表补行与客户端事件，故只局部改造这3文件。

**结束：**本绑定只关闭静态子项；实际红绿、受影响回归、页面、旧数据/源码保持、独立审查与公开回读分别留`evidence/B05/explicit-details-20261029/`。仅关闭本包B05/B06/B07子项；整卡/G1/G2/G3、现场/手机/Z01继续开放。


**本包审查补绑（2026-10-29）：**现有`reset_use_multi_level_bom`仍会在保存切换时展开，属于同一确认边界；限定在原WorkOrder内禁用审批工单该自动路径。已有明细变更qty/BOM/展开开关/来源仓等计划依据时，拒绝携带旧计划保存，要求人工核对后清空草稿明细再改依据、重新确认；不实现自动替换/复杂调整。预览按`set_work_order_operations→validate_operations/validate_operations_sequence→set_required_items`建立稳定计划，不复制规则。原测试类新增`test_switch_explosion_does_not_generate`、`test_confirmed_basis_requires_clearing`、`test_unsequenced_route_replay`、`test_single_operation_replay`先核反例；仍只改原3文件，命令仍原b05 runner。


## 2026-10-29 B05活动计时收尾与人工结束绑定

用户明确授权本绑定后连续开发和验收，仅B05这三个余项。开工公开main为65b0a8a30baff197985b811a2ba7188815e83651，固定ERPNext/Frappe及现有维护checkout沿第2节，原25份累计源码/5823ca57保留；原空明细/确认生成子包不重开。

**做什么／通过标准：**识别原审批工单下所有非取消卡的真实开放计时；人工结束前必须收尾。计时按人明确填写的实际结束时刻保存、既有时段/数量/原记录不变；停止单仍允许结束既有计时但不允许新增执行。厂长用原结束接口，最新授权/版本/状态及原因必填，保存结束当时差额与操作者/时间。正常、无权/跨单/撤权、陈旧、失败零残留、中文PC重开可核。**不做：**不改生产/库存数量、报工/工资/效率公式，不新增结束状态机、计时平台、元数据或事实账；不接库存闭环、完整G3、手机、现场、AI、Z01或后台周期。

### 真实入口和最小方案

| 归属 | 实际位置/拟新增签名 | 允许范围与判据 |
|---|---|---|
| 结束入口 | 原`work_order.py:close_work_order(work_order,status)`拟补可选`expected_modified=None,reason=None`；拟新增`preview_production_close(work_order,expected_modified)` | 仅新审批工单强制厂长/对象write/read/本公司授权、已批准docstatus1及Not Started/In Process/Stopped/Completed状态；工单先锁重读。Closed拒绝重复结束，不追加原因记录；非审批原调用保持 |
| 计时发现 | 同模块拟新增内部`_production_open_timers(order)` | 在已授权父工单内按真实Job Card/Time Log查询，docstatus0/1且未取消；from有值/to为空及started_time异常均不能忽略，不用用户可见列表或status标签筛掉活动；预览只读 |
| 计时收尾 | 同模块拟新增`finish_production_timers(work_order,expected_modified,timer_fingerprint,end_time)` | 本包由有权厂长处理，每张卡仍需read/write；工单先锁再按卡名锁，核预览指纹/各卡版本、合法时间、draft且非正式report卡；已提交开放卡/时间异常明确拒绝，不修旧事实。只给原开放行填to_time，清原计时器状态，使用原JobCard校验/分钟计算并save，不submit/不记数量 |
| 停止单收尾边界 | `job_card.py:JobCard.validate_work_order`及`make_time_log(args)` | 仅上述服务器创建的request-local context，绑定同一父对象/同一卡对象/当前厂长，允许Stopped收尾既有草稿计时；Closed/新增行/改量/改关联仍拒绝。原make_time_log审批路径在父工单先锁后重读，收尾与标准开始/完成计时使用同一父锁；不宣称所有通用资源/库存路径已覆盖G3 |
| 差额/原因 | 原close入口复用`update_status/on_close_or_cancel`及原Comment | 差额消费B04`calculate_report_metrics(...plan_quantity,good,bad...)`，逐工序存计划/良/不良/未清，成品入库量及其计划差额另列，不把工序相加当成品。只在同事务记录原Comment：原因、当前人/时间、依据版本、单位及快照；不改历史报工、库存、作业实际日期或补造完工事实 |
| 页面 | 原`work_order.js`状态按钮/`change_work_order_status` | 审批单以中文“人工结束”对话框展示当前计时、差额和原因；先明确实际时间结束计时，再刷新预览后确认结束。接口复验全部边界，按钮隐藏不代替鉴权；原非审批按钮不重写 |

**依据／岗位：**原C05/C10及B19已验的厂长结束限制，不新增审核层级。工单停止表示不再新增执行，收尾原计时不等恢复。原生暂停方法会带入completed_qty并受Stopped校验，故只复用原时间校验/计时状态与save，不自动用该方法写产量。原五项目固定来源沿R03～R06/审批绑定；实际只复用ERPNext/Frappe，配置不能修漏检和结束原因缺失，需局部改造。

**允许产品文件仅4份：**原`work_order.py/.js/test_work_order.py`与`job_card.py`。源路径均在`erpnext/manufacturing/doctype/`；不改Frappe/BOM算法/Job Card元数据/库存。检查脚本仅`.development/checks/b05_closeout_tests.py`、`b05_closeout_ui_fixture.py`、`b05_closeout_ui_preserve.py`及本包浏览器步骤。无元数据新增，无reload-doc/建站/全量依赖初始化。原xgd-test.localhost和18090合成站/容器复用；开工及最终指定源文件核哈希，原数据/凭据保留。

**拟新增测试：**原`test_work_order.py:TestWorkOrderCloseout`复用原审批/报工fixture，覆盖开放草稿拒结束、明确收尾后结束、Stopped仍能收尾、原因与差额历史、角色/跨公司/撤权/陈旧、非法时间/正式卡不改、失败回滚及重复结束；仅补直接受影响的原停止/恢复和计时状态回归。具体每个方法名字在创建前写原卡，不运行未创建方法或用未收集冒充通过。命令`docker exec xgd-b08-check env/bin/python /b01/b05_closeout_tests.py`，真实DB/原业务对象，fixture事务回滚核原11表。页面使用Playwright CLI和新合成数据，不重放旧B05/B08/I03～I06写入。

**结束条件：**绑定、实际红绿/受影响回归、明确中文PC操作/重开、旧数据/源码核对、一次独立审阅及公开回读齐备才收口本包。证据为`evidence/B05/closeout-20261029/`；B05整卡、G1/G2/G3及正式交付不因此关闭。


本包页面夹具复用18090及旧BOM，只新增自己角色/厂长/窄报工员/Employee/隔离工位和3张新样例；旧岗位/权限/配置不变，按原审批产生计划卡，再给差额样例一笔8良2不良作为人工结束的既存前提。23表捕获旧行。计时/结束共享父锁改动另以`.development/checks/b05_closeout_race.py`在第三张新单做一次两独立HTTP标准开始与close重叠，结果只能开始成功/close活动冲突，或close成功/开始闭单拒绝；新样例后续仅正常接口收尾，实际结果不外推全部G3。脚本在执行前补绑。


真实持久化核对发现结束快照的中文被原生`as_json`默认转义；只将同调用补`ensure_ascii=False`，原记录不改写。新增脚本`.development/checks/b05_closeout_ui_unicode.py`仅给原本包追加第四张无计时/无报工的中文记录展示样例，不重放前三张；受影响单方法补中文原文断言，先红后绿，不重跑已验12项全批。原23表捕获基线及原3样例保留，预期新单4/计划卡12＋正式报工1。


## 2026-10-29 B05字段编号与缺资料提示绑定

**授权与版本：**用户明确继续原B05这三个余项，先核对补绑再连续开发验收。公开main已实际pull为Already up to date，HEAD=e18aba7548d7d3805ddfd2729388ff94257a1b04；25份维护源码哈希与公开锁一致，原累计patch 3e9b706c。ERPNext15.124.1/Frappe15.124.0及维护checkout/隔离站点沿原绑定，不新建工作树覆盖25份已有改动。

**做什么：**映射并复用工单字段和编号，补交期完整性及具体缺项提示。**不做：**不另加字段/表/编号器、路线平台、主数据维护界面或日历产能算法；不改B04数量/展开、B08事实、已验计时/结束或库存链，不扩手机/现场/G/Z01及后台周期。**通过：**正常原生编号/字段保存重开；草稿交期可空有提醒，送审必须补交期；交期不得早于计划开始日期；缺BOM/工序路线/用料分别可理解，权限与原审批冻结不弱化；失败不生半张有效单。真实中文PC及旧行保留、一次审查及公开回读后只关闭本包子项。

### 现有字段与处理，不重复造轮子

| 业务字段 | 原真实字段/代码 | 本包处理 |
|---|---|---|
| 工单编号 | Work Order.name / naming_series；work_order.json autoname=naming_series:，单项MFG-WO-.YYYY.-；Frappe model.naming.set_new_name/set_name_from_naming_options/getseries及主键唯一约束 | 直接复用；不自定新前缀，不承诺连续无断号；实测两个新号唯一、重开不变与重复主键拒绝。测试使用原insert(set_name=...)指定重复号，不能用重新分号伪装重复测试 |
| 产品/公司/计划量 | production_item/company/qty/stock_uom；原before_validate/validate_production_item及JSON必填 | 直接复用现有有效物料/单位/B04校验，不重跑已验精度批次 |
| 执行班组/申请人 | 原production_team、approval_requested_by；validate_production_approval及scope | 直接复用，不增加岗位，原对象/公司/班组和归属校验在交期提示前 |
| 交期与计划 | expected_delivery_date是既有Date、原未必填；planned_start_date既有必填Datetime默认now；planned_end_date原validate_dates检查先后 | 不把计划完工当交期、不推算交期。草稿可暂空；仅新建/发起人草稿编辑及送审检查新交期规则；其他流转/已批准报工/停止与结束不倒追补填旧单 |
| BOM/路线 | bom_no既有必填Link；已提交有效BOM名为现有版本标识，工单operations为准备的计划行；_production_order_detail_plan先read权限、validate_bom_no再原展开 | 不造独立路线版本字段；仅把原合并的缺工序/用料错误拆清。原确认指纹已含BOM.modified及计划明细，沿用不重写；全局BOM结构锁/主路线历史仍B07责任，不因字段映射通过 |
| 仓库/可选来源 | source_warehouse/wip_warehouse/fg_warehouse；sales_order/project/production_plan等原字段 | 保留必填和默认行为；不强制销售单或新加仓库校验，原生缺必填保存拦截继续生效 |
| 实际日期与数量 | actual_start_date/end_date、produced_qty及原报工/库存来源 | 只映射、不改来源，不用交期或草稿字段伪造实际生产/入库 |

### 最小改动与唯一任务步骤

1. **仅允许3份产品文件：**`erpnext/manufacturing/doctype/work_order/work_order.py/.js/test_work_order.py`。不改JSON元数据、Frappe、JobCard、BOM算法。现有25份累计成果保留。拟新增控制器方法`WorkOrder.validate_production_header(self, *, for_review=False)`，只消费原生getdate做必填/日期先后；在validate_production_approval的新建/本人草稿保存及可信送审处调用一份规则，其他审批流转/派生回写跳过，不给旧批准单追补交期。原`validate_dates`的计划结束检查不重写。
2. 原`_production_order_detail_plan(order)`保留计算/权限，只拆“缺工序路线”和“缺用料”消息，原缺BOM分支仍在同处。JS原refresh/bom_no/production_item回调和既有字段事件调用拟新增`erpnext.work_order.show_production_header_guidance(frm)`；只用本表已有值提示产品/BOM/交期及准备下一步，不新开读取API，不对未知BOM断言无路线；具体缺项仍由原有预览返回。复用原set_intro和字段description，不重建页面。
3. 测试拟新增`TestWorkOrderHeader`：原生编号唯一/重复拒绝，交期草稿空值/送审拦截，交期保存/重开/冻结，非法及倒序日期，缺BOM/无路线具体错误零明细，缺用料明确拒绝，权限/撤权。复用TestWorkOrderApproval fixture；因新增送审前置，在该fixture.order_args补可见交期并让原helper透传，原显式生成fixture亦补该字段，不代表旧批次已重跑。具体方法在原B05创建前列名。仅直接受影响原回归`TestWorkOrderApproval.test_normal_two_stage_workflow`及`TestWorkOrderExplicitDetails.test_preview_confirm_replay`各一次；不重跑计时/结束/B08等全批。
4. 复用runner模式新增`.development/checks/b05_header_tests.py`，命令`docker exec xgd-b08-check env/bin/python /b01/b05_header_tests.py`；实际红绿、原11表回滚保持。新UI脚本仅`b05_header_ui_fixture.py/b05_header_ui_preserve.py`及私有Playwright步骤，复用18090，不导入会初始化fixture的test_*模块。新普通发起人、无BOM物料、已准备但无交期草稿作为最小前提；页面实际验字段/编号、缺BOM、无路线提示、交期拦截/补填/送审/重开，不重放旧确认生成或旧报工。
5. 无元数据/依赖变化；只同步3文件到保留测试/网页容器、必要noreload重启。指定运行清单和原数据回读，独立审查一次，原34卡只关本包子项，OpenSpec引用本卡不复制第二清单。可公开证据在`evidence/B05/header-20261029/`；原始日志/样例/凭据/截图本地保留。依据继续沿R03～R06五候选及原CASE-01/07，实际复用ERPNext/Frappe，未重选/安装其他底座。

**本包实操补充：**缺用料测试仅在本方法新造的BOM中受控清空用料/展开行，模拟上游不完整来源，最后事务回滚；为此原11表外另核4张BOM表，共15表，不操作旧客户资料。网页新会话实际出现磁盘源码已新但提示函数仍undefined的旧脚本；只清专用合成站`frappe.clear_cache(doctype="Work Order")`并完整重载后，新交期提示已出现。该目标缓存刷新属于本包必要运行同步，不改元数据或业务数据；不能只凭源码哈希声称浏览器已更新。

**收口规则校正（以本段为准）：**原生`validate_dates`只阻断计划结束早于计划开始，`expected_delivery_date`为期望交付日期；原卡未要求它必须晚于计划开始。初版把该关系硬拦截依据不足，会阻断逾期安排。仅把该一分支改为“可能逾期”的风险提示并保留原交期，非法日期/缺交期送审及原权限/冻结仍阻断。新增`TestWorkOrderHeader.test_overdue_delivery_is_preserved_with_warning`先红后绿，连同受影响日期方法定向2项复验，不重跑其他主批次；原10项清单另存中间版本。页面只在本包自己的无路线草稿填早于计划开始的交期，保存/重开核警示及原值，不新增样例或执行事实。

## 2026-10-29 B05状态动作与未覆盖入口绑定

**授权/基线：**用户要求从原B05状态动作及未覆盖入口续接，并核清为什么仍在B05。公开main实际pull无更新，基线`b26633cb871b2cd4667b943493cf787234b8d93e`；维护checkout沿`codex/xgd-maintenance`，累计25份修改保留，原源码清单/补丁`382c6d2f`。复用原测试容器`xgd-b08-check`、专用合成网页`xgd-b08-ui:18090`，不另建工作树、站点或初始化依赖。原R03～R06五候选核验继续适用，本包直接复用ERPNext15.124.1/Frappe15.124.0。

**目标：**把剩余入口逐项对账，只修真实缺口，状态页面与已验服务器规则一致；复制的新单不能继承生产事实，父单删除不能抹除历史。**边界：**不重新开发审批、计时/结束、报工/库存算法；不扩销售404、全局BOM锁、手机/现场、完整G1/G2/G3、Z01或后台周期。本包新增隔离样例才允许在用例内删除/回滚，旧记录、用户与授权保持。

### 唯一实施计划（原卡引用，不另建任务清单）

1. 按原B05及CASE-01/07建立入口矩阵。已验直接建单/确认生成、交期/编号、两级审批及直接取消/停止拒绝、首报联动、计时/结束与历史保护只回链旧记录；未改变不重跑。不把B04网页精度或其他卡的整体验收挪成B05新增功能。
2. 先以真实fixture核原生`frappe.copy_doc(..., ignore_no_copy=False)`，检查新单任务/用料、实际日期、原事实及审批是否继承。仅当真实反例确认时，复用原生`no_copy`修既有字段（`operations/actual_start_date/actual_end_date`），不新建复制器。普通新建/Resource保存输入在`WorkOrder.validate_production_approval`现有新建边界检查不能伪造实际生产字段，不改旧单派生回写。
3. 原`work_order.js:set_custom_buttons`只对审批工单去掉原生`Stop/Re-open`入口，保留原`show_production_approval_actions`的厂长/版本/原因动作；原生非审批路径保留。库存`Start/Finish`若在审批表单出现，只澄清领料/入库语义，不新增手动开工或生产完成入口。直接服务器保护沿原`stop_unstop/close_work_order/apply_production_approval`，不复制状态机。
4. 仅允许原`work_order.py/.js/.json/test_work_order.py`四文件，JSON仅既有字段`no_copy`；未发现真实缺口的文件不改。新增`TestWorkOrderEntrances`：最小fixture、新单伪造实际字段拒绝、原生复制空明细且不带事实、父单删除权限/历史正反例。复制元数据如影响旧取消修订/关联新单，仅相应两原方法改用原预览/确认准备新计划并定向回归，不重跑旧18项。先红后绿，期望为失败零副作用及测试结束旧表回滚相同。
5. 检查脚本复用原runner，新增`.development/checks/b05_entries_tests.py`，命令`docker exec xgd-b08-check env/bin/python /b01/b05_entries_tests.py`。必要时仅目标`reload_doc(manufacturing,doctype,work_order)`同步既有no_copy并刷新DocType缓存；不全量迁移/构建。中文PC普通岗位新样例核状态菜单、带原因停止/取消及复制保存重开/删除；服务器绕过反例由定向测试承担，不将API冒充页面验收。
6. 本包证据`evidence/B05/entries-20261029/`。源码/实际命令/分批红绿、中文PC、旧行保留、独立一次审查及公开回读齐备后，逐项回填原B05；整卡是否关闭仅依矩阵支持范围与原结束条件，不预填通过、不因其他卡未验无限滞留B05。未支持管理入口明确范围，不承诺抵抗管理员SQL。

**执行记录：**尚未运行本包测试或验收，结果在上述路径按实际续记。

**同一新建边界补充：**新单的工序行也属于外部新建输入，`completed_qty/process_loss_qty/actual_operation_time/actual_start_time/actual_end_time/status`不能伪造执行事实。原WorkOrderOperation历史保护针对已存在的报工引用，不负责新父单输入；本包仍只在原WorkOrder新建检查内处理，新增一个定向方法`test_new_plan_rows_cannot_fabricate_execution`先红后绿，不修改子行控制器或重开B08。

**状态冲突实证及补绑：**普通厂长在本包新样例停止后，页面仍提供取消修订，真实HTTP417；一次仅回滚的同对象诊断定位原`WorkOrder.validate_cancel`要求Stopped先恢复，与项目原规则禁止恢复冲突。原C10/B19已允许无执行历史取消修订。本包补绑此原方法，仅审批工单可跳过原Stopped阻挡；`before_cancel`既有动作授权和`_has_production_execution`历史保护保持，不允许有计时/报工/库存历史取消。新增`test_stopped_approval_without_execution_can_cancel_without_resume`单方法红绿；原`stop_unstop`仅将审批停止消息明确中文化，非审批原逻辑保留。此前417和脚本超时留档，不写成取消成功。

**页面修订授权前提：**实际读取本包新发起人权限为read/create/delete真、amend/import假，Data Import create假；不能把create当作amend。本包只在新增隔离角色追加原生amend以验修订入口，旧角色/用户/授权不动；客户角色部署仍归B02/Z01，不把测试授权当默认生产配置。此项在fixture脚本中可复现。

**普通新建0/0的直接输入：**本包工序零实绩正例实际通过时带入一行计划，证明普通insert仍允许跳过“先保存空草稿”。原CASE-01不只约束自动BOM展开。本包追加`test_new_order_requires_empty_saved_draft_before_plan_input`红绿，在同一新建边界拒绝预填任务/用料。既有`TestWorkOrderApproval.setUp`只把计划准备移到空insert之后，仍沿原草稿编辑与权威set_required_items；不新造fixture或确认入口。当前UI fixture同样调整，仅本轮受影响方法及正常两级审批定向复验，历史全批不重跑。

**受影响验收范围冻结：**新建0/0规则使本轮fixture创建步骤变化，最终只重验本轮`TestWorkOrderEntrances`，含`test_stopped_order_with_report_history_still_cannot_cancel`保护反例；另加原正常两级审批及本包直接影响的取消修订/剩余需求两方法。B04/计时结束/B08旧整批不跑。这个有限集合是最终服务器验收，不再扩成全量ERPNext测试。

**修订按钮补绑：**实际已取消新单在有amend权限时仍无修订按钮；Frappe`Form.set_read_only`裁掉amend/create，Toolbar.can_amend因此不显示，但原`Form.validate_form_action`已支持Workflow只读单据按基础权限执行复制/修订。仅原`work_order.js:show_production_approval_actions`在已取消审批单、生产发起角色且原基础create/amend权限均真时显示“修订”，复用`frm.amend_doc()`及其原生校验；不改Frappe、Workflow配置或任何权限掩码。新草稿不应继承审批/事实/计划，若原生from_amend复制的实际结果不满足，再仅在原onload新修订单初始化处理。

**修订实测反例与初始化：**原生按钮实测可进入新未存修订单，但from_amend忽略no_copy，仍带3计划/1用料、原申请/审核人、Cancelled生产状态。仅原`onload`在新建且有amended_from及本审批Workflow时清审批、计划和实绩并设Draft/草稿；await原set_value完成再继续，不改源单、默认Workflow或权限。普通复制已经通过不重跑。服务器最终10方法中9通过，唯一历史反例因报工后fixture未reload导致TimestampMismatch；只补该方法reload并单独复验，不重跑9个未变方法；此准备失败不算产品缺陷或整批通过。

**旧行差异的已证实归属：**最终完整哈希检查发现复制源单一行不同，modified仍为本轮前时间。只读副本去掉本轮新读者的`_seen`新增项、按原生json.dumps重建后与开工原哈希完全一致，证明其余全部字段未改；实际Frappe`Document.add_seen`正是update_modified=False追加阅读者。保留该原生阅读审计，不恢复/删除或称原23表逐字节零差异。最终回执明确“1阅读标记差异、0业务字段差异”。这不放宽任何其他旧行/字段核对。

**本轮实际结束：**[执行记录](../B05/entries-20261029/run-record.md)及原B05入口矩阵已回填，11不同方法按P0/9过1准备错/修后单项分批覆盖，中文PC及最终23表业务字段核对完成，一次独立四文件审查无阻断。只归档本状态入口change；B05整卡保留B04网页原始数量精度回链，后续开发移到原B06，不因卡片仍部分反复开本包。公开保存以最终远端回执为准。

## 2026-10-29 B06任务调整与授权绑定

**授权及依据：**用户“继续下一步”，按最新TODO转B06；公开基线`1f2fc31b945f05bb826bbfba44d072558005f45d`。维护源码34份与B05最终清单一致，累计26个产品文件保留。原PRD 5.3.2已实际读取：任务允许增加/删除/中插/复制，报工权限挂任务，工序计划可以小于工单计划。C05规定良品＋不良达任务计划完成。原删除报工文案已被“事实保留、关联冲销”决策取代，不能恢复连带删除。

**做什么：**草稿/退回的任务插入、复制、重排、删行、独立计划量及任务授权；审批冻结与直接子行入口同守边界。**不做什么：**重写生成/审批/报工/身份模型、另建任务账、委外、客户迁移部署、手机/现场或全局验收。旧生成、B05父删及B08/B09历史保护消费原证据；只有本次改动经过的路径才定向回归。

### 唯一实施与验收计划（B06引用）

1. 产品只改ERPNext制造的七文件：`work_order.py/.js/test_work_order.py`、`work_order_operation.py/.json`、`job_card.py/test_job_card.py`。不改Frappe/角色矩阵/依赖。复用原生工序表和grid，`idx`是实际行链、`sequence_id`沿原生首项1/递进校验；复制产生新行身份，插删重排后可清空序号由原生重新编号，不造第二套pre/post字段。
2. 元数据仅新增`Work Order Operation.report_plan_qty`（Data，中文“任务计划数量”，库存单位，保留原始十进制输入）。权威读取为拟新增`WorkOrder.get_operation_plan_quantity(row)`，校验复用B04 `validate_quantity_input`；草稿准备缺值取工单计划并保存。旧已批准空字段沿原父计划语义读取，不回填旧数据，不吞非法非空值。默认生成仍各10；明确任务调整可小于父计划，不新增无依据的父子数量关系限制。
3. 只将相关原取数接到该入口：`validate_operations`、`create_job_card`、`create_job_card`函数的默认批量、`update_operation_status`、`_production_close_snapshot`，Job Card `validate_job_card_qty/get_production_report_tasks/validate_sequence_id`。任务自身计划控制数量限额及完成，保留现有超产配置；前道已完成的小计划不被旧“前道良品必须不少于后道”比较错误阻断。工单计划、成品入库及用料计算不改。
4. 任务编辑复用`_production_order_for_details`的read/write、发起人、草稿/退回和公司/班组校验，先锁父单再检查。直接子行插入/改挂、改序/计划/授权/事实需回父表完整保存，已存草稿的普通时间编辑及末行删除正例保留；冻结父单下即使没有报工也不得从子行旁路改删。`validate_report_history`对生效/取消引用继续先行且不重写；父表删除仍走已有保护。未变化的报工scope鉴权继续唯一实现。
5. 原测试新增`TestWorkOrderTaskAdjustments`和`TestProductionTaskPlans`；只复用已有fixture，不继承整类重复执行。首个最小fixture单独执行，再跑本包新测试及直接受影响原“生成预览重试”“窄报工确认”“未报工草稿子行编辑/末删”方法；不重跑B05计时/结束或B08全批。命令`docker exec xgd-b08-check env/bin/python /b01/b06_tasks_tests.py [完整方法名...]`，15张原业务表回滚哈希不变；报告实际失败/修后分批结果。
6. 新隔离普通中文PC样例在18090原站：已有准备明细作为前提，实际grid新增/复制/中插/删行、改计划和scope、保存重开、送审冻结及旁路拒绝；权限用新合成用户，旧角色/旧记录不动。报工真实数量与scope由新计划样例服务器/HTTP证据验，不把API当页面。只同步七文件，按需reload新增工序元数据、清目标DocType缓存并完整重载；源码清单、旧行/库存保持、一次独立审查后收口，证据`evidence/B06/tasks-20261029/`。

**怎样算通过：**真实输入产生不同计划且不改父计划，原生任务行顺序/身份稳定，合法草稿编辑成功，冻结/无权/陈旧保存/越任务及有历史破坏拒绝，良品＋不良按本道计划完成，重复请求不追加事实，库存无新增；相同业务事实未重验。满足本包才归档，整卡及G1/G2/G3/Z01只按原完整判据记状态。

**首次执行后的有限补绑：**两个直接子行冻结红测已真实失败，修后通过。原生grid列表会维护idx；首个Python中插测试只调列表未同步idx，修测试以模拟真实输入，不改原生顺序算法。数量反例在函数测试中须模拟HTTP失败回滚边界，另用真实HTTP核417后零事实；撤权前User因员工绑定被系统更新，须先reload。父表行身份另两条红测实际证明“挪用别单任务name/重复同一name”可保存，故仅在`validate_operations`草稿/退回分支校验已有行归属及唯一身份，不改变B08原历史拦截。新增原卡范围内两方法后，只复验5个新/失败方法和直接受影响的生成重试；不重跑首批12个未变通过方法。页面样例新增只读Employee/Department选择角色用于配置scope，旧角色不动，客户角色交付仍属B02/Z01。

**页面/HTTP适用范围：**原Select支持value/label对象，`work_order.js:setup`仅用原grid选项接口显示未授权/所有人/指定部门/指定人员，服务器标识仍为空/ALL/DEPT/PERSON，不改鉴权。新任务计划影响限额，真实HTTP在新样例核超量417后零事实，并以两个不同请求并发争同一部分任务余量，要求一成功一拒绝、只持久化一事实；这是本次受影响边界，不重跑原I03～I06全批。页面送审后由控制脚本在同一新样例完成原两级批准作为HTTP前提，不能计为本轮审批页面验收。

**独立审查有限修正：**两项Important均新反例证实：撤掉发起角色但保留其他对象write仍可父表调量；直接删首行留下2/3。仅将原草稿发起人/角色/scope抽为`_check_production_draft_editor`供父表和明细入口共用，合法审批/系统派生原分支保留；直接子行只保留末删，其他删行回父表保存。不增加新授权模型。Minor为原工序进度按父计划×任务数计算，与部分任务不符；原`show_progress_for_operations`项目分支按C05既有完成状态计已完成数/总数，工单产出进度不改。中文选项最终放`refresh`刷新当前grid。只复验两新反例、末删正例和合法父表调整，页面核真实完成比例。

### 2026-10-29 B06工位差异纠正绑定

用户明确授权“处理这条差异，再进B07”。公开基线`69aa1b97f2f67223549af5a6cfd1e66f02ac4ce4`。**做：**保留原FAILED/原哈希，核原生工位状态写入；修测试样例的资源隔离及原值捕获，补一笔报工的保持验证。**不做：**不恢复/改挂原报工与旧工位，不回填猜测的历史值，不改B06产品代码或重跑20方法/PC/并发。

1. 新只读回滚探针`.development/checks/b06_retention_probe.py`：在原合成站对原单唯一有效Job Card调用既有`update_status_in_workstation`，捕获调用前/后原行，核差异仅原生状态/审计字段；finally回滚并核原23表完全恢复。只证明当前源码行为，不能反推上轮历史原值。
2. 修原`b06_tasks_ui_fixture.py`：接受明确样例键`b06-tasks`/`b06-retention`，仍拒绝覆盖；新样例复制独立Workstation给三任务使用，旧角色/数据不动，私有基线增加工位原行。原`b06_tasks_control.py/preserve.py`仅接受同一可选样例键，复用既有状态/审批/保持核对。历史原文件和FAILED摘要不改写。
3. 新`.development/checks/b06_retention_verify.py`仅对纠正样例准备1/2/3计划并沿正常审批，窄报工员只发一笔良1/不良0，检查独立工位关联、原23表完全保持、原B06旧失败哈希/记录未覆盖、零库存。命令沿`docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/<脚本>`，私有原值与响应不公开。产品源码/输入中不受工位变化影响的项全部复用。
4. **通过条件：**当前写入范围及回滚有证据；纠正样例仅自有工位派生变化，旧23表和历史证据不变；历史具体字段差异仍明确未验证。修复后通过只关闭本包的隔离/保持缺陷，不把旧FAILED翻成OK，不关闭整卡G2。满足后沿原OpenSpec归档当前限定包，再补原B07真实入口绑定开发。

## 2026-10-29 B07本单用料保存与结构锁绑定

**授权/基线：**用户授权处理工位差异后进B07。差异纠正已用独立工位一笔报工复验23旧表保持，产品仍为`69aa1b9`的累计补丁`5400304d`。复用ERPNext15.124.1/Frappe15.124.0及原测试/网页容器、原R03～R06候选结论，不新建底座或环境。

**做什么：**原本单用料合法编辑、保存范围/权限、领退历史结构保护和生效数量来源展示。**不做什么：**重算B04、重跑生成/Q05、修改Stock Entry/库存账、反算本单数量覆盖多层BOM、发明库存审批状态、客户迁移/部署或手机验收。产品通用BOM沿原生独立维护/复制新版本，不从本单隐式回写。

### 唯一执行计划（原B07引用）

1. 只改七份原产品文件：`work_order.py/.js/test_work_order.py`、`work_order_item.py`、`bom.py/.js`、`bom_item.py`。原未修改的两个子行控制器因此首次纳入源码清单；不改Frappe、Stock Entry、角色矩阵或数量字段类型。新脚本仅`b07_materials_tests.py`及本包新合成网页fixture/保持检查；证据`evidence/B07/materials-20261029/`。
2. `WorkOrder.validate_operations`现有行身份检查抽为`validate_production_plan_rows`并同验工序/用料身份，防挪用别单行/重复行；本单编辑仍经原`validate_production_approval/_check_production_draft_editor`。用料需求输入复用B04 `validate_quantity_input`（允许既有公式舍入到0）；库存单位取Item权威，拒绝伪造已领/退/消耗。草稿/退回合法数量/来源仓库调整不回写BOM；审批状态不解冻。
3. `WorkOrderItem`原生父表保存不逐行触发自定义save钩子，故直接子行入口拒绝并提示回本工单保存；按存储行旧parent检查Stock Entry docstatus>0历史（含取消），累计发生过领退不因净额0解锁。父表结构保护复用审批冻结及行归属，不复制库存校验或建关联账。非法引用和跨单移挂必须拒绝。
4. BOM结构冻结扩展原`validate_material_loss_write`，同时覆盖既有`before_update_after_submit/update_cost(save=True)`，存储状态为已提交时，父产品/基数/单位/公司及材料行身份/物料/单位/数量/损耗依据不得从成本旁路改写；金额/费率等原成本派生仍允许。BOM Item直接改删统一要求回父BOM，已提交版复制新版本；不改版本命名。`bom.js:before_save`用原生确认弹窗区分保存产品通用BOM，取消不得落库。
5. 新只读`get_production_material_summary(work_order)`只在原对象read后返回本单行，消费原`transferred_qty`（已提交非退料累计）、`returned_qty`及`consumed_qty`，净领=累计领－退，统一库存单位。原库存未有接入的待审批状态，`pending_issue/pending_return`返回null并说明未接入，不能把docstatus0草稿称待审批或把未知写0；此依赖明确保留B19/B10/B11，完整B07不提前关闭。
6. `work_order.js`复用原grid及`frm.save`，草稿/退回发起人的本单材料编辑沿现有权限；原dirty事件只改主保存文案为“保存到本工单”。用料区说明及来源表显示不同数量，产品通用BOM维护置二级菜单，确认后进原生BOM；按实际BOM对象read/write能力显示，真正保存仍由原权限/状态/版本控制。无需新编辑器或从工单反推BOM。
7. 新原测试`TestWorkOrderMaterials/TestWorkOrderMaterialHistory`，先最小fixture，再新安全反例红绿。覆盖本单改量不改BOM、非法数量/单位/实绩、父表行身份、送审子行改删、通用BOM权限/新版本/成本旁路、真实领10退10净0及取消历史不解锁、只读数量/无权。只复验直接影响的原BOM成本损耗保护和B06合法任务编辑；原生成/并发整批不跑。命令`docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b07_materials_tests.py [完整方法名]`，原15表回滚保持。
8. 新普通中文PC在原18090专用站：独立工位/新BOM样例，实际本单改量保存重开、二级BOM维护确认/取消及有权新版本保存、送审冻结；真实领/退链用原库存入口作为来源，不算新增库存审批验收。私有保存原值及哈希、核旧表保持；只同步绑定七文件，目标缓存/完整重载，独立审查后据实际结果收口当前包，整卡G1/G2/G3、待审批来源和交付条件保留。

**首次执行补充（范围不扩卡）：**P0通过，四安全反例全红后修补；首批13方法中11方法通过，另两方法分别为错误单位输入恰等于当前库存单位、移挂目标不存在先在原生权限层失败（两个历史分支各一错误）。只修这两测试输入。通用BOM草稿父表挪用已提交材料name的新反例另实际失败，因此将相同归属/唯一身份检查抽到原`bom.py:validate_child_table_identity`，供BOM材料及工单两表共用，不建新框架；只补相关失败/新反例和正常保存回归。网页用独立产品、原料和工位，库存只触及新物料Bin，捕获旧Bin及原表，不能重犯共享可变资源问题。

**同入口后续核对：**单位反例进一步改为核保存后确实等于Item库存单位，不把一次未拒绝推断成错误单位可持久化。BOM草稿成本持久化另一次同方法红测确认可越过before_validate；仅将共用归属检查放入原`validate_quantity_inputs`，使普通保存及`update_cost(save=True)`都到达，无第二套检查。只复验这两个直接变化的方法。

### B07当前包实际结果（2026-10-29）

七文件范围未扩大，16个不同方法分批通过、15旧表逐批回滚保持；普通中文PC本单需求6不隐写原BOM0.5，原生新版本草稿0.6，取消不新增版本，送审冻结。原生受控领6退6后页面显示6/6/6/0/0，待审批null/未接入；24旧表含Bin捕获行保持，36运行文件匹配。

独立审查发现的提交BOM成本入口stock_qty遗漏已先红后修，仅重验反例与原正常成本更新；行身份保护同步覆盖草稿BOM成本路径。单位测试按真实原生归一结果断言持久化物料主数据单位，未增加第二套换算。失败/中间源码哈希未捕获、UI工具误选与输入未同步过程均保留，不改写历史通过。见[B07实际记录](../B07/materials-20261029/run-record.md)。当前限定包可归档，整卡、待审批实际来源与全局门槛仍未关闭；不自动启动下一责任卡。

# 2026-10-31 B13手机网页、扫码与弱网恢复绑定

沿原B13/CASE-08；本段只补本轮开工必要绑定，TODO/交接/提交后期统一做。ERPNext15.124.1 `4e0dce9`维护分支，B12本地累计补丁`9b8906c6`、41文件运行核实；原B08导航、B09请求幂等、B10/B11库存事实与B12入库已验项不重做。

- 复用：Frappe15.124.0原响应式Form/List/Dialog、`frappe.ui.Scanner`（`frappe/public/js/frappe/scanner/index.js`）及内置html5-qrcode；原扫码组件只输出解码文本，无工单定位鉴权，错误关闭相机窗口。只补受控定位及中文人工输入回退，不改Frappe/扫码库、不新建App/打印二维码标准。
- 扫码契约：接受本站原`/app/work-order/<name>`、`/app/job-card/<name>`链接或明确单号；拒绝站外/脚本/带额外查询参数/未知类型/不存在或无权对象；取消单据提示历史人工查看。复用各文档read及父工单当前范围，返回doctype/name仅导航，不自动报工、审批或过账。原二维码不含到期令牌，不能声称实现签名过期认证。
- 允许文件：`work_order.py`新增最小`resolve_production_code(code)`只读白名单；`work_order_list.js`和`work_order.js`只添加入口；`erpnext/public/js/production_navigation.js`共享原Scanner/Dialog调用（两入口复用）。原扫码库不改。普通跨对象/撤权、坏格式及取消对象须有反例。
- B11入口：`work_order.js:add_custom_button_to_return_components`仅放开已签批、可创建Stock Entry且有已领减退减耗余额的进行中/停止/结束原工单；动作仍原`make_stock_return_entry`与原库存保存/提交，不改B11计算。原有非项目流程保留。
- 设置最小读取沿`permissions.md`第5节：只在`stock_entry.py`新增`get_stock_entry_form_settings(company,stock_entry=None)`并在`stock_entry.js`替换两次Stock Settings整份读取，保存单read/company匹配、新单create+当前Company范围；留样仓仅在当前可读/可选择范围内返回。仅返回两字段，不接受任意设置键，不授Stock Settings权限。
- 报工弱网：仅改`work_order.js:open_production_report`的原localStorage请求恢复/输入回显；保留原键和原请求，刷新后先查询结果、无结果才原键重试；未确认响应不当失败或新建另一笔。必要捕获只补真实状态/保留输入，禁止假成功。不改`job_card.py`确认/幂等/计算或历史事实。
- 验证文件：原`stock_entry/test_stock_entry.py`追加独立B13类并复用B11最小fixture；`.development/checks/b13_*`只增定向检查、合成独立样例及31旧表审计。用原`b06_tasks_tests.py <B13方法>`回滚测试；`node --check`改动JS；Playwright CLI本地18090，桌面Chromium156.0.8078.79触屏模拟，设备描述390×844；实际库存视口390×844、报工视口390×664（按最终浏览器实测记录）。刷新加载源码、普通岗位扫码/输入定位/审批状态/报工/领退料；断请求/后端提交后丢响应、刷新原键恢复、命名库存草稿提交丢响应后重开原单，核0重复库存/报工。新草稿保存不是库存生效，不新造库存离线提交引擎。
- 真机型号/真实镜头成功扫码/现场网络/非开发人员均尚无条件，保持未验证；桌面触屏模拟和注入解码文本分别明示。只关闭本轮实际验过子项，不标B13整卡完成、G3或客户交付。

# 2026-10-31 B14编号与默认值剩余配置绑定

依据原B14及CASE-01/07配置子项；用户明确不新增字段，提交及TODO后期统一。当前维护ERPNext15.124.1 `4e0dce9`，Frappe15.124.0；承接B13累计补丁`c51578ad`及43文件清单，不重跑原B05基础唯一编号、B14时段、B08图片/计算、B13已验或缺条件项。

**做什么：**原生条件编号配置、停用/优先级与冲突反馈；原生Company User Permission默认值的保存/读取、默认冲突、当前权限及旧文档保持。**不做什么：**新增字段/DocType、客户正式编号方案、重编号旧单、重置现有业务计数、改全局权限/新配置引擎、Frappe修改、客户部署或提交推送。**通过：**隔离配置管理员正常维护、普通发起人消费；无权/撤权与非法配置拒绝，旧事实不变，真实PC配置/消费及定向运行证据齐备；只认本包范围，不将旧卡未验项改成已验。

1. 编号直接配置后使用：Frappe `core/doctype/document_naming_rule/document_naming_rule.py/.json`原生Form、`DocumentNamingRule.validate_fields_in_conditions/apply`、`model/naming.py:set_new_name/set_document_name_via_naming_rules`。规则仅匹配新隔离物料/公司条件，前缀明确为测试标识；原锁counter及主键唯一约束保留。编号为空/错误条件及配置计数导致冲突应真实拒绝，不承诺连续无断号。不重跑B05手工重复主键用例。
2. 权限沿原生System Manager全站配置角色，只给本轮独立配置账号；不是公司级生产配置管理员的自动授权。普通发起人不能读取/改规则；撤掉该测试账号System Manager后原角色正常业务权限与配置拒绝分开验证。新增规则有原Version；不改已有规则、全局命名系列或元数据。
3. 默认值直接配置后使用：`core/doctype/user_permission/user_permission.py:validate_default_permission/get_user_permissions`及`model/create_new.py:get_new_doc/set_user_and_static_default_values`。同一测试用户Company范围的`is_default`是真实配置入口，普通原Work Order新建消费；多个默认冲突按原生拒绝。既有数量默认1、计划开始now及报工默认未完成量只映射来源，不伪造可配置数量表、不重跑其已验计算。默认值不授予权限；构造好草稿后撤当前Company授权，保存仍须原工单强制范围检查；缺必要物料/BOM/交期不被默认掩盖。
4. 默认/编号配置均仅新样例，原站全局参数不变。基于同一已批准BOM/原角色契约新建空草稿；不确认展开、不提交工单/报工/库存，不增加业务联动验收。用原样例保持函数额外捕获Document Naming Rule/Condition、User Permission、DefaultValue、Property Setter及生产/库存旧事实。
5. 文件白名单：本轮先仅`.development/checks/b14_config_*`测试/fixture/浏览器步骤、私有`.development/private/b14-config-20261031/`及本绑定；不预先改产品源文件。若出现实际产品缺口，先留失败再补具体最小文件绑定，不直接扩改底座。
6. 验证命令：`docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b14_config_tests.py [方法]`回滚独立样例；`... /b01/b14_config_fixture.py prepare|audit`用于18090持久合成样例及旧表保持；`playwright-cli -s=b14-config ...`与普通发起人会话原生配置Form/新建/保存/重开。先最小fixture，不全量初始化依赖；已有工具/容器复用。原apply引用模式0任务不是B14完成证据；遵从用户不更新TODO/任务勾选。

# 2026-10-31 B15生产计划与软分组绑定

用户本轮明确激活原B15；依赖原B05/B14、C03/C04、CASE-01/07。仅新增执行绑定，TODO/提交/交接后期统一；B13/B14未验证项原样保留。ERPNext15.124.1维护分支`4e0dce9`，承接B14累计补丁`c51578ad`；GPL-3.0原生Production Plan、Work Order来源字段、Project及Version复用，不新建字段/DocType。

- 做：原生已提交计划的单个成品行预览→人工确认→空明细审批草稿；现有Project多工单软分组及草稿解绑留痕；来源变更不改旧工单。通过须定向受控测试、真实PC、旧行保持、运行源码核实。完整并发门槛未实际运行前仍未验证。
- 不做：销售/MRP/自动排产/委外或子装配批量生成；全新组织单据、客户数据、业务字段、已审批依据改写、来源解绑后自动重生、计划级联删除；不改B05展开/审批与B09/B10/B11/B12数量实现。
- 文件白名单：`erpnext/manufacturing/doctype/production_plan/production_plan.py/.js`新增`preview_approval_work_order`、`confirm_approval_work_order`及原生Dialog入口；`work_order.py:validate_production_approval`仅补来源不可伪造/移除和Project当前read/同公司检查。测试`.development/checks/b15_plan_*`，本地私有证据`.development/private/b15-plan-20261031/`。若有新实际缺口先补绑定，不扩至Frappe或权限全局配置。
- 契约：原生plan.read/write+工单create+发起角色+当前公司班组；只接受真实父计划下成品行，排除销售/物料申请/子装配来源；BOM/Project读取权限及有效公司。预览显示品号/BOM/库存数量单位/公司/仓库/日期/班组/分组，确认重新读取并锁父计划，指纹不一致拒绝；原生来源plan+item查已存在工单（含草稿/取消），有权重试返回原单，无权不泄漏。新单仍原`insert`全部权限与必填校验，不ignore权限/验证，不预展开明细。
- 原`ProductionPlan.make_work_order`在项目Workflow启用时阻止旧直接生成，避免绕过预览；未启用旧路径保留。来源字段只由受控确认写入，后续不可改；Project沿原草稿编辑限制，存在明细/审批冻结不得绕过，原Version保留解绑轨迹。计划原生向上数量汇总保留，无计划向下改写或删除的新逻辑。
- 验证命令：`docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b15_plan_tests.py [方法]`隔离回滚；`node --check .../production_plan.js`；实际18090用`playwright-cli -s=b15-plan ...`，目标缓存/重载后确认新行为。先最小fixture，依据源码/输入变化只运行本轮新增项。最终只认实跑结果，不用锁代码代替并发验收。

B15审查补充（同文件边界）：既有原生取消修订会复制no_copy来源字段；新来源保护需兼容真实已取消原单的同源修订。只复用`validate_production_approval`已有amended_from原单read/公司班组检查，另校验docstatus=2及三个来源字段完全一致；禁止改源、借用未取消原单或无权原单。不新增修订入口、不清空来源逃避防重。定向“计划→审批→取消→同源空草稿修订”先红后修。

# 2026-10-31 B16对账与查询导出绑定

沿原B16及CASE-01/05/06/07，复用B04/B08快照、B09原单/更正、B10～B12库存来源和B19Comment/Version。ERPNext15.124.1 `4e0dce9`维护分支承接B15累计补丁`df2308e7`，Frappe15.124.0。用户要求不新增字段、不重跑未变已验、提交/TODO后期统一；B13～B15未验保留。OpenSpec继续引用原卡，无第二清单。

1. 原`Work Order Consumed Materials`（ref Work Order）：绑定`manufacturing/report/work_order_consumed_materials/*.py/.js`原execute/get_data/get_columns/filter。原get_all无对象范围、退料使用Stock Entry Detail.qty已见静态缺口；改为原get_list授权父工单，精确ID读权、状态/工单创建日期过滤，消费既有`work_order.py:get_production_material_summary`累计领/退/净领/本单需求，不另写库存汇总。库存单位按原Work Order Item.stock_uom，不跨物料相加；未有有效消耗来源时实耗留空并标“未记录”，待审批未接入不写0。成品入库读Work Order.produced_qty，工序产量不冒充成品。保留原超耗筛选；源工单链接追原库存与审批。
2. 原`Job Card Summary`（ref Job Card）：绑定`manufacturing/report/job_card_summary/*.py/.js`原Script Report，增“逐笔生产报工”视图，不另建Report。普通列表模式保留；逐笔仅report_request_id真实确认记录，默认docstatus1，取消记录独立视图并标明不计生效。日期为原posting_date；明确工单/工序/库存单位、良/不良、有效秒、原单/amended_from。数量良品率调用`calculate_report_metrics`，效率/预计工资读取`_saved_report_metrics`历史快照，缺快照/零分母“—”，不另存汇总。get_list当前JobCard read且检查父WorkOrder read；混选无权父ID拒绝。逐笔视图关闭跨单位合计和把取消记录计完成的图表。
3. 原列表绑定：Work Order的name/qty/produced_qty/status/workflow_state及审批字段；Job Card的docstatus/amended_from/correction_reason/原确认时间；Stock Entry的work_order/purpose/is_return/source_stock_entry/docstatus及明细against_stock_entry/transfer_qty/stock_uom。均经`frappe.desk.reportview.get/export_query/_export_query`和当前read/export。审批完整处理轨迹只消费原Work Order Comment/Version，不新造审批历史表。
4. 导出绑定：两份Script Report统一`frappe.desk.query_report.run/export_query/_export_query`，导出重新执行原report且can_export检查相应ref DocType；不返回预缓存管理员结果、不改Frappe。列表混选ID/无过滤/!、like、%、引号与撤权定向测试，导出核实际ID和中文表头，不只计行数；read与export分别验证。后台/PreparedReport/邮件及历史下载未验保留，不新增能力。
5. 白名单仅上述4原生报表源码；不改B04/B08计算、B09确认/冲销、库存/审批实现及全局角色。测试`.development/checks/b16_query_*`、私有`.development/private/b16-query-20261031/`和本绑定；持久只新增隔离读/导出测试账号/角色与自身权限，不改旧业务行。实际缺口扩文件先补绑定。
6. 验证：`docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b16_query_tests.py [方法]`原最小fixture回滚；真实原生run/export Query/ReportView；`playwright-cli -s=b16-query ...`本地18090普通中文页面/CSV下载及源记录核对；JS node --check、运行清单。旧业务数据按基线哈希保留，不重建已验领退/报工样例。不得把两报表子包、API或只读核对冒充CASE全链/客户验收。

B16 CASE-06补充：同一已绑定材料报表增加显示列`material_issue_percent`（仅报表列，非数据库字段），调用原`calculate_report_metrics`的issued_quantity/required_quantity支路；累计领料作分子，不用净领替代，零需求返回“—”。真实旧工单00041领10退2净8的HTTP检查缺列先红；只复验变化的材料页面/CSV及此分支，不重跑领退业务或已验报工报表。

B16实际导出汉化缺口补绑定：原ReportView导出实际出现`docstatus`、`owner`、带上下文的`ID`英文表头。仅扩白名单至已有`erpnext/translations/zh.csv`，补3条原生翻译（单据状态、创建人、编号），第三列沿Frappe上下文格式；不改Frappe导出器、字段名、筛选或权限。清理原翻译缓存后只核受影响表头。实际取消/更正追溯复用既有[本地样例编号已移除]→00101-1/工单00029，新只读账号仅该来源；不再纠错。

# 2026-10-31 B17受控核心闭环验收绑定

原B17/CASE-01～08及R02；固定B16候选ERPNext15.124.1 `4e0dce9`，累计补丁SHA256 `a81070eba07db1eece06a5b823e2663fd775adfc4abf6b80ad93f74587f25f95`，49文件清单沿b16-query-source-manifest.json。遵从最新8条规则、不新增字段、不重跑未变化独立子项、提交和TODO延后；此前未验不关闭。

- 做：证据差集；一张新隔离CASE-01工单，从普通发起人空明细保存→原preview/confirm_production_order_details→原apply_production_approval送审/审核/签批（三人分离）→仓管领料→操作工三道逐笔报工→部分及剩余成品入库→原B16查询/CSV和来源追溯。领5→退1→核净4→原生取消退料恢复净5后继续主链，保留退料及取消事实；逆向验证先取消成品入库、再取消领料、最后更正报工，遇真实依赖拒绝先保留证据，不绕过。
- 样例：复用原fixture主数据创建及旧表保持工具；R02计划10、3工序、BOM基数1/用量0.5/损耗0、原料20/成品0、独立仓库和工作站。合成日期按当前隔离环境2026-10-31记录，不冒称R02原日期已跑；单位复用原Nos并记录本地映射。真实HTTP业务角色均无System Manager/Administrator；管理员仅配置新样例、读取核验。
- 真实入口：`frappe.client.insert/get/submit/cancel`；WorkOrder原preview/confirm_production_order_details、apply_production_approval、make_stock_entry、make_stock_return_entry；JobCard原preview_production_report_time/confirm_production_report/correct_production_report；原Query Report run/export_query及原WorkOrder/JobCard/StockEntry中文页面。库存审批未配置，不把草稿算待批。
- 通过判据：空明细0/0，确认3任务/1用料需求5；审批记录三人、时间和状态可追；领5后source15/WIP5，退1后source16/WIP4，取消退料恢复；三工序各良10不计成30成品；部分4和剩余6入库后fg10/source15/WIP0、实耗5，查询CSV同源。逆向后原单不删除、库存与派生回退，已有下游先拒绝更正。当前缺条件项及完整G1/G2/G3按证据差集保留，不能把此链当全门槛通过。
- 白名单：本次先仅`.development/checks/b17_core_*`、私有`.development/private/b17-core-20261031/`和本绑定；复用b08_distinct_concurrency_fixture的capture_tables/compare_tables、b10的TABLES、原初始化和HTTP调用方式。没有产品改动授权扩张；出现实际失败后定位原责任卡和具体文件，再补最小修补绑定。不会为假想竞态加锁/重试/兜底。
- 命令：`docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b17_core_fixture.py prepare|audit`；`python3 .development/checks/b17_core_http.py <已记录阶段>`；`playwright-cli -s=b17-core ...`复用已装CLI做实际中文页面/来源核对。每次请求及返回阶段保存，失败不自动重放整个链；检查真实当前状态后仅续接未完成动作。无旧库清理、无新增服务、无新API或第二公式。

B17实际样例补充：原Nos为整单位，BOM0.5改复用已有B05小数单位（成品仍Nos），不改已有单位或字段。人工确认明细后必须由发起人通过原frappe.client.save设置WorkOrder Operation.report_scope=DEPT/report_department=本样例班组，再送审。初始00048漏配授权而报工403，保留为反例；已有领退历史禁止取消修订，按原停止执行→previous_work_order关联00049恢复，不移除历史保护。新测试发起人只公司/班组范围，单单UserPermission仅其他已建单操作角色；仅移除本轮新planner那条阻碍创建的限制。fixture增加bind/allow-continuation模式只服务本样例；无产品改动。

B17证据收口位置补充：沿原卡写`evidence/B17/run-record.md`和脱敏结果摘要，原始请求/合成数据/凭据留本地受限目录，不写入公开证据；不更新TODO/交接/原卡勾选或提交。

# 2026-10-31 B18前置核对与现场准备绑定

依据原B18、CASE-12、C07，严格沿最新8条规则。已实际核对B17记录和A01～A03原卡：B17整卡未完成，A01～A03未见本项目完成证据；C07车间/验收人/岗位/数据范围/设备网络/观察期/接受条件仍待提供。本轮只完成可独立的现场准备，不把缺条件当已具备，不启动客户业务或代填使用日志。

- **做什么：**核对前置与候选版本，复用现有普通岗位操作和失败处理说明，整理现场输入及实际记录格式。**不做什么：**产品代码/字段/权限配置更改、客户数据写入/迁移、现场部署、采购/模型调用/外部发送、重复B17或以前测试、TODO/交接/任务勾选/提交推送。**通过标准：**每个前置有现有来源及明确状态；操作说明指向既有入口，不虚构AI页面；现场记录为空且标未执行；缺项和恢复入口明确。
- 候选沿B17：ERPNext15.124.1维护分支`codex/xgd-maintenance`、基线`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，49文件和累计补丁`a81070eba07db1eece06a5b823e2663fd775adfc4abf6b80ad93f74587f25f95`已只读核实。本候选不是客户试点版或发布版，不因文档准备关闭G1/G2/G3。
- 复用入口及实现映射（只读绑定，未授权本轮修改）：WorkOrder `work_order.js`的“预览任务和用料/确认生成任务和用料”、任务报工范围、原审批菜单、“逐笔报工/扫码或输入定位/成品入库”；后端`work_order.py`的preview/confirm_production_order_details、apply_production_approval、make_stock_entry/make_stock_return_entry、close_work_order。JobCard原确认/更正与原键恢复，StockEntry原生保存/提交/取消；B16两原生报告`Work Order Consumed Materials`和`Job Card Summary`及原导出。B18只消费原职责，不另造现场报工页、统计公式或验收系统。
- A01～A03只引用原卡要求，未绑定新AI文件/API或模型服务；确定性明细预览不能替代AI-2字段候选或AI-3语音/文本识别验收。待其实际完成证据后，再补现场真实入口和服务条件。
- 白名单仅本文件、`evidence/B18/run-record.md`（前置/岗位操作/现场记录，单一入口）、`.development/private/b18-pilot-20261031/`只读核对回执。本次没有合适既有现场操作手册，沿原卡要求在B18证据目录首次形成该记录，不复制TODO/34卡。
- 当前命令只读：`sed/rg`原卡、决策、验收及既有B17证据；`git -C .development/repos/erpnext rev-parse HEAD`、`branch --show-current`、`diff --binary`取候选；Python标准库hash核49文件、保护TODO/AGENTS/任务卡/OpenSpec原文及Markdown相对链接。无业务/浏览器/数据库测试，因为没有产品或页面变化，且无现场人员设备条件。
- 现场启动另需C07与A01～A03/B17前置实际满足，并绑定获准站点地址、版本、人员角色、单据/产品范围、数据留存范围、设备/网络、时间及验收人。当前没有真实站点/操作者/排期，不编造可执行生产命令；收到信息先核对再执行。原资料一周观察不由脚本压缩，人工10秒目标按真实操作计时，不由自动化用时替代。

## B18模拟资料续接（2026-10-31）

用户答复明确标注“B18现场试点信息表（模拟）”；本补充只绑定该演练输入的记录和差异核对，不将其转成真实C07确认或客户数据/删除/发送授权。仍只允许修改本R07、`evidence/B18/run-record.md`及本地受限B18证据；源文件、字段、角色配置、原TODO/任务勾选和提交推送均保持本轮边界。

- 原输入受限保存在`.development/private/b18-pilot-20261031/simulation-input-original.json`；准备稿以“验收人-A”代称模拟负责人。设备系列、岗位称谓、90天、阈值及日期均按模拟来源记录，真实身份/站点/账号/产品BOM/库存/服务授权尚未取得。
- 模拟计划2026-11-16至2026-12-11，四个工作周；Python `datetime`核起止为周一/周五，周记录日期为11-20、11-27、12-04、12-11。仅日历推导，没有创建定时任务或生成未来/连续使用记录。
- 原C09/C10核对：独立异常返修审批无既有首版定义；模拟“工艺工程师审核→生产主管签批”与原班组长→厂长称谓/授权不同。只登记差异，未改原审批配置；原不良报工/更正不能自动当独立返修审批。
- 审批离线暂存/重试未有证据。复用B13原报工恢复/库存重开及真机未验台账，不重跑、不将其推为离线审批通过，也不新造离线队列。
- 原`job_card_summary.py:get_production_report_columns/get_production_reports`及B17保存CSV可核“预计工资”“确认人”等原输出；BOM原页面仍需按实际权限检查。当前没有证据满足模拟“禁止字段在界面/日志不可见”；需在真实范围和薪资字段口径明确后回原责任卡绑定实际缺口。90天起算/证据与业务账/日志导出备份等范围未定义，不配置删除或削弱历史保留。
- 成功率98%、工作日平均审批30分钟、一致99%、加载5秒、抽20单全过、P1/P2无遗留等只记录为模拟目标。已列待明确分母/起止/工作日历/容差/抽样/分级等口径，不编造统计、测量或业务验收人签收。
- 核验命令限Python标准库日期/文件hash/相对链接、`rg/sed`原范围/台账及报表源码、读取既有CSV表头；没有产品行为变化或新业务测试。输出回执`simulation-input-verification.json`，此前B17/A01～A03与B13～B15等未验状态不变。

## B18脱敏演练证据包绑定（2026-10-31）

本轮用户要求继续完成B18；原卡仍要求真实人员/周期/接受记录，现有输入明确为模拟。本次推进未完成的资料准备，复用B17正向/逆向保存回执，生成可供人工演练的脱敏副本及20单空抽检表。没有真实试点条件时不重放已有业务链，不生成未来周报或20张业务单。

- 文件白名单新增`.development/checks/b18_pilot_package.py`（仅本地证据生成，不是产品API/导出器）、`evidence/B18/rehearsal-package/`生成文件及本地受限B18回执；继续维护本R07和原B18记录。无新增DocType/业务字段、角色/权限、离线审批、返修功能或90天删除任务。
- 输入固定为`.development/private/b17-core-20261031/`中的forward-audit/reverse-audit、3份continuation审批回执、领/退/两笔制造submit回执和两份报工更正回执；不读access/login/凭据文件、不连数据库、不重新请求接口。演练身份仅角色代号，工单/工序/物料/报工/库存记录使用稳定可区分的合成别名，原始映射只留受限本地。
- 原数据的计划/工序良不良/库存单位数量、状态和时间直接取保存结果；阶段分正向/逆向，不能把重复快照行当新增业务或多周使用。数量列仅用于本合成演练，不构成真实客户数据授权。
- 仅输出列白名单；不输出姓名、邮箱/工号、工资/金额、价格、BOM原文、客户信息或原始内部标识。此脱敏只覆盖生成副本，不改变或证明原系统界面、日志、导出均符合模拟隐私要求。90天保留为待确认期限，不删除正式或旧测试记录。
- 命令`python3 .development/checks/b18_pilot_package.py`，输出审批/工单/报工/库存CSV、20行未填抽检CSV和说明；源脚本为唯一生成入口，生成物不手改。检查实际输入hash、CSV白名单/行数、稳定关联、关键数量与状态、人工栏为空；结果留本地verification，不把资料验证计业务接受。
- 通过：生成包能追溯B17来源且无禁用字段/原始身份，20行仅序号和未执行状态；原TODO/AGENTS/C09/C10/OpenSpec、产品源码不变。全部原现场/前置未验保留，B18不能关闭；此轮不提交推送。

# 2026-10-31 A01取数、结构化草稿与人工确认边界绑定

原总TODO顺序第6步及原A01/CASE-09为本轮入口；B12～B19已验子包沿各自证据承接，不因TODO延后而重跑。C06用户明确答复“待定”，不实调模型/语音、不发外部请求或采购；B19实发/B18现场/真机等原未验证保持。OpenSpec沿原卡引用模式，CLI 0任务/blocked不当进度依据；不复制任务清单、改勾选或归档。使用Superpowers执行原计划的必要红绿测试及一次最终审查；提交和TODO仍延后。

## 复用与最小设计

已查`evidence/R06/reuse-matrix.md`首版AI行：五项目核验没有证据可直接使用所需真实模型/语音实现，此结论不扩成整个生态没有AI。复用固定ERPNext15.124.1/4e0dce9、Frappe15.124.0的原权限/表单/JSON快照/事务及本项目B02/B04/B05/B08/B09/B16；当前51文件候选与B19最终manifest相符。既有WorkOrder预览/确认已覆盖AI-1确定性部分，不另写生成器；既有原生字段/来源作为AI-2候选来源，真实候选选择归A02；本轮不写文本解析或录音，归A03。

只补缺失的结构化建议连接，不建Agent平台。允许新增`erpnext/manufacturing/production_ai.py`，改原`doctype/job_card/job_card.py`和`doctype/work_order/work_order.js`，测试新增`manufacturing/test_production_ai.py`及本地`.development/checks/a01_*`。不改Frappe/元数据/锁，不新增字段/DocType、角色框架或独立草稿库；测试角色只在隔离fixture。

| 实际入口／拟补签名 | 权限、输入输出及边界 |
|---|---|
| 新`get_production_ai_context(work_order)` | 原WorkOrder.read，输出对象/modified/状态、单位及已存工序计划/良不良的最小事实和来源；不返回全单/员工/工资/BOM原文，不接受SQL或任意字段。只读身份无报工、审批、库存写权 |
| 新`prepare_production_report_draft(work_order, operation_id, suggestion)` | 人工导入结构化建议时复用原`_report_task`校验执行/本人任务权限；suggestion只允许原6个报工输入字段。原数量/工时类型校验直接复用；缺项保持空，不猜时间/数量。返回values、missing及当前父单/工序/版本basis，不保存生产事实或服务器草稿。模式明确为结构化建议，不能称真实模型识别 |
| 原`preview_production_report_time` | 人工补齐后按原B04实时预览，指标及fingerprint完全复用；模型金额/工时派生值一律不接受 |
| 原`confirm_production_report(..., draft_basis=None)` | 只新增可选建议来源元数据，沿原锁/当前角色/任务/状态/余量/防重。来源只作待本人确认的客户端声明，不充当授权票据；当前版本改变时新请求须重新导入，同键已成功请求仍沿原hash回原结果。元数据纳入原请求hash及既有`report_time_context.suggestion_draft`，原JobCard.owner/时间记录确认人；不复制写入校验或建第二条确认入口 |
| 原`open_production_report(frm, selected_task, suggestion_draft)` | 仅可选导入连接，复用同一弹窗；明确“建议草稿待本人核对”，任务绑定本对象，数量可改，缺工时不填now；取消无写入。人工按钮仍调用原确认接口，已有待核对请求优先、不被新草稿覆盖。结构化合成输入通过实际浏览器验收，不冒充真实文本/语音页面 |

验证以新增A01真实fixture为主：只读AI取数/无写权、无权/跨对象/撤权、8良2不良缺工时与取消无事实、非法/注入字段拒绝、本人编辑后原API确认及同键重复/改内容拒绝、来源版本变化与撤权后确认拒绝；原JSON快照可追到来源/建议/确认人和正式单。先留功能缺失失败，再最小实现；只复验直接改变的普通确认路径，不重跑旧G1/G2/G3/并发。真实模型与语音、C06费用、A02字段候选及A03识别均未验。

命令绑定：原隔离`xgd-b08-check`上`PYTHONPATH=/b01 env/bin/python /b01/a01_boundary_tests.py [方法]`回滚新合成数据并核旧表保持；Node语法检查改动JS。实际页面优先当前ego-browser技能，工具不适用时按已安装Playwright CLI与项目要求说明替代，不重装。运行来源/哈希、失败与最终结果存`evidence/A01/`及受限`.development/private/a01-boundary-20261031/`。达到原A01本轮不依赖C06的结束条件即交接A02，不在同点重复检查，不称整卡或模型实调完成。

# 2026-10-31 A02明细建议与原生字段补全绑定

原A02/CASE-09及用户本轮明确授权。已核A01本包7项/真实页面与53文件候选，B05/B06/B07/B14前置按现有证据消费；不重跑未变算法、防重、审批/报工/库存及原缺条件项。C06待定，不实调模型/语音；确定性预览/候选不能写成真实AI识别。原OpenSpec引用模式继续，TODO/任务卡/交接/提交延后，不复制计划或新建任务卡。

已读原`preview_production_order_details`/`confirm_production_order_details`、`_production_order_detail_plan`、原弹窗及`WorkOrder.set_default_warehouse/get_default_fg_warehouse`、`Item.default_bom/get_item_defaults`。原R06五项目AI行没有可直接调用所需模型的证据，沿一个ERPNext底座复用，不重新安装/选型。

**做什么：**原明细预览补可见工单/BOM版本来源；原生字段仅给BOM/原料仓/在制仓/成品仓的有据候选，交期无本单确认依据则提示本人填写。新增只读候选连接与中文选择弹窗，接受只填当前空字段，不自动保存/展开/送审。可改、可忽略，普通手工入口保留。

**不做：**新字段/元数据/推荐平台/历史预测、复制计算或确认入口、任意字段/SQL、猜交期/人员/数量、模型语音调用。未查询历史样本就明确未使用，不编数量或声称历史为0。A01报工草稿及其已验项不改，已记录Minor不顺带清理。

| 真实入口／允许位置 | 输入输出、权限和复用 |
|---|---|
| `production_ai.py:get_production_field_suggestions(production_item, company, missing_fields, bom_no=None)`拟新增 | 只接受原5字段白名单`bom_no/source_warehouse/wip_warehouse/fg_warehouse/expected_delivery_date`；原发起角色及WorkOrder.create，当前Item/Company原生read。返回候选值/标签/来源对象版本/理由、无候选说明，不改库。BOM来自Item.default_bom或已选BOM，需实际BOM.read、产品/公司及已提交启用符合；仓库候选需当前Warehouse.read、同公司/非组/启用。可选默认BOM无read时不暴露，手工流程不受影响 |
| 原`WorkOrder.set_default_warehouse/get_default_fg_warehouse` | 在未保存的原生WorkOrder对象上获取在制/成品默认，复用原Manufacturing Settings→Item/ItemGroup规则，不复写默认算法；返回仓库版本与原方法来源。原料仓只在已授权BOM用料的非空来源仓唯一时建议，多来源或缺值保持无候选，不造领料算法 |
| 原`_production_order_detail_plan` | 只在既有fingerprint计算后追加只读`source`（工单/modified、BOM/modified）；不改展开/哈希/确认比较。原弹窗显示来源，原确认仅消费原参数，仍生成计划而非事实 |
| 原`work_order.js`表单 | 新“字段补全建议”按钮只给发起人的新单/可编辑草稿；先选产品/公司，收集当前空字段。弹窗默认不勾选，来源可核，忽略无改动；接受只`frm.set_value`选中空字段，来源产品/公司/BOM已改则提示重取，原保存再校验当前权限/取值。无新增服务器保存或确认API |

白名单仍4个原文件：`production_ai.py`、`test_production_ai.py`、原`work_order.py/.js`；本地`.development/checks/a02_*`仅检查/隔离样例。复用原A01回滚runner，指定新增`TestProductionOrderSuggestions`类，不执行未变化A01测试；核新候选/来源、无配置/多来源、无权/撤权/select-only、错误字段输入及无写入。BOM变更与重复确认的原保护引用B05已验及未变代码，页面经本包新入口只验新增组合。实际ego-browser中文选择/忽略/修改/保存与原明细预览/确认，留各次请求耗时，单样例不外推2秒SLA。旧表保持、源清单、一次最终只读审查及失败记录齐后收口本包，整卡真实模型仍未验。

A02执行补充：新接口真实接受字典参考的反例已保留，明确字符串对象ID在入口一次拒绝，不让原get_doc将其解释为筛选。审查只补本包多/空来源、真实异产品BOM及Warehouse不可读/停用/组/跨公司新失败分支证据；没有新增产品防护。页面理由和DocType来源采用中文业务表述/原生翻译，不向用户显示内部函数名。

A02保持审计出现旧User1行hash变化，原基线仅hash且没有字段原值。原audit断言失败保留，不修旧User、不重写基线、不猜字段原因；本轮只新增只读observe工具，显式输出False及变化对象/其余表结果，供继续核新样例事实。该工具不改变原保持判据，不把失败当完成，功能结果与保持门槛分开报告。
