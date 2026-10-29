> 公开归档副本（2026-10-29）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

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
