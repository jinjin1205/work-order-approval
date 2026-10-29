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
