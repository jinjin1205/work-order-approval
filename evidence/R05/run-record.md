> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R05｜ERPNext 核查与运行记录

当前结论（2026-10-26补证后）：R05按选型核验结束条件收口；已复现的问题尚未修复，完整CASE未通过。第1～5节保留各历史阶段结论，最新补证见第6节；底座选择见[R06](../R06/selection.md)。

## 1. 本次静态阶段实际做了什么

- 时间：2026-10-26，证据截止09:34 UTC（17:34北京时间）。
- 输入：项目AGENTS、R05卡、C05、CASE-01～07、R01固定版本、R02 fixture/expected-results v1。
- 采集环境：Codex工作区 `.`；通过GitHub连接器定向读取固定commit文件并查看行号。没有本地ERPNext/Frappe应用环境参与本阶段核查。
- 动作：读取 Work Order、Job Card、Stock Entry、BOM、库存账及必要的Frappe精度/文档状态/删除/权限实现；定向读取已有测试与CLI定义。
- 实际输出：下表列出的文件取得成功；建立[适配矩阵](fit-matrix.md)，确认原生库存链入口与业务口径差异。
- 期望：为R05筛选提供可复核的复用、配置、局改、未知边界；没有以任何测试通过为期望输出。
- 限制：没有安装、启动Docker/数据库、建站、初始化业务数据、执行Python业务方法、运行上游测试或R02样例；没有性能、手机、并发、AI或客户部署结果。根代理后续运行须单独追加真实记录，不覆盖本阶段。

## 2. 读取方式与文件身份

实际工具调用形式：`github.fetch_file(repository_full_name, ref, path)`；ERPNext统一使用 `frappe/erpnext` + `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；Frappe统一使用 `frappe/frappe` + `f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab`。均返回 `isError=false`。以下是**文件blob SHA**，不是仓库commit；源码结论与具体行号链接在fit-matrix中。

| 仓库 | 文件 | blob SHA |
|---|---|---|
| ERPNext | `erpnext/manufacturing/doctype/work_order/work_order.py` | `808777b02a1833279c5073fce26902d83eca60c6` |
| ERPNext | `erpnext/manufacturing/doctype/job_card/job_card.py` | `cd8c77dc9ea49d27a991eb47c1555af2e01a6518` |
| ERPNext | `erpnext/manufacturing/doctype/job_card/job_card.json` | `45ddb9cf609b5395222955e8bfdcc7e28a311cb2` |
| ERPNext | `erpnext/manufacturing/doctype/job_card_time_log/job_card_time_log.json` | `0565d677e9b509abb4d9b4da1c573c5ef7e1b271` |
| ERPNext | `erpnext/manufacturing/doctype/manufacturing_settings/manufacturing_settings.json` | `64a1c870ce489c6bc3057b7606dfdee7309d34cc` |
| ERPNext | `erpnext/manufacturing/doctype/bom/bom.py` | `cbd9d38d1bd3b0cf37debb0ea4dca8b929d7536c` |
| ERPNext | `erpnext/stock/doctype/stock_entry/stock_entry.py` | `fed639c03b7889d5c3897edcf5c9aaa59d3295de` |
| ERPNext | `erpnext/stock/stock_ledger.py` | `4dd1452f5f72406ec7e84ed52c0c6d7e2c8be336` |
| ERPNext | `erpnext/manufacturing/doctype/job_card/test_job_card.py` | `a4324187aff08505860508b1812cce2264ffbc48` |
| ERPNext | `erpnext/manufacturing/doctype/work_order/test_work_order.py` | `ffe9378511f7dbed7667b5b40a1f08ca71de4180` |
| ERPNext | `erpnext/stock/doctype/stock_entry/test_stock_entry.py` | `31ca720a88b55d5adafe2dd16c5ab7445a2b25e2` |
| Frappe | `frappe/model/document.py` | `971abd386544893872b36c905893539d471940e6` |
| Frappe | `frappe/model/base_document.py` | `ae015e0503a48c61193d2e677d55f877f9810b77` |
| Frappe | `frappe/model/delete_doc.py` | `bf515ccf265baf9d2da3f7fc06e977ec1d7e20be` |
| Frappe | `frappe/model/meta.py` | `8cb3cb92eab7a949639b5aaa1967801a1006595f` |
| Frappe | `frappe/utils/data.py` | `1f2eb5f02159f0e0ee811277675bb2e92905685b` |
| Frappe | `frappe/database/mariadb/database.py` | `91e4eb225271b25a36c1614879d7016a01382c83` |
| Frappe | `frappe/core/doctype/system_settings/system_settings.json` | `ac88db243fd8d664aa4e8e1a74082e7f27e8820e` |
| Frappe | `frappe/permissions.py` | `ebcbf8dca697a4d0071a3a9ef8272e40b0cc10b9` |
| Frappe | `frappe/commands/utils.py` | `a1d1c8e592c3b05d552328ec3de2dbd5f568e0cf` |

## 3. 已核对的有限原生测试入口（未执行）

[固定Frappe utils.py 757～828](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/commands/utils.py#L757)定义 `run-tests`，支持`--app`、`--module`、可重复`--test`、`--junit-xml-output`和`--failfast`。802～808检查站点`allow_tests`或CI，并在未启用时给出 `bench --site <site> set-config allow_tests true` 的原生命令。只允许用于独立测试站点。测试入口会建立上游测试数据，不能拿现有用户站点代替。

这里的命令是**基于已读选项与真实测试名的待执行模板**；`<隔离站点>`、日志路径、容器执行前缀由环境负责人核实后填入。此处没有实际执行记录或通过状态；实际镜像内若Frappe与固定基线不同，先记录差异，不能冒称完全相同组合。

| 优先次序 | 已读原生测试／位置 | 真实范围；不能替代的R02部分 |
|---|---|---|
| 1 | [test_work_order.py `test_job_card` 551～599](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/test_work_order.py#L551) | 建原生工单、转WIP、提交作业卡、Manufacture、断言下游制造阻止取消JobCard。使用上游BOM和数量1，不是R02三工序/数量10，不验无下游10→8冲销。 |
| 2 | [test_job_card.py `test_job_card_proccess_qty_and_completed_qty` 621～762](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/test_job_card.py#L621) | 原函数名确为`proccess`。两工序计划10，填完成8，断言自动损耗2、前工序不足时拒后工序10、最终WO产量8+损耗2且Completed。验证原生语义，不能等同明确不良报工满足R02。 |
| 3 | [test_stock_entry.py `test_material_transfer_for_manufacture_qty_precision` 1581～1609](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/test_stock_entry.py#L1581) | 内存文档需求33.876、已转33.875，允许0.001、拒0.002；未提交库存，未验六位输入、Q05或换算存储。 |
| 4 | [test_work_order.py `test_non_consumed_material_return_against_work_order` 2115～2180](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/test_work_order.py#L2115) | 原生转7、耗5、生成余料退回2；**只save退料草稿，未submit退料**，不能证明来源仓回补或R02领10/退2/净8通过。用批次/序列料，非R02简单原料。 |

```sh
bench --site <隔离站点> run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --test test_job_card --test test_non_consumed_material_return_against_work_order
bench --site <隔离站点> run-tests --app erpnext --module erpnext.manufacturing.doctype.job_card.test_job_card --test test_job_card_proccess_qty_and_completed_qty
bench --site <隔离站点> run-tests --app erpnext --module erpnext.stock.doctype.stock_entry.test_stock_entry --test test_material_transfer_for_manufacture_qty_precision
```

已读但不默认全跑：`test_job_card.test_completed_qty_sums_without_float_noise`（1161～1166）只核0.7+0.1状态；`test_work_order.test_partial_material_consumption`（971～1006）验证先制造2后剩余消耗草稿、未提交这笔消耗；`test_stock_entry.test_work_order_manufacture_with_material_consumption`（1611～1668）测制造成本分支。这些不能代替CASE-02全链或CASE-06明确实耗7。

## 4. R02 定向运行需补取的证据

| 分支 | 必须保存的原始事实／比较 | 本静态阶段状态 |
|---|---|---|
| CASE-01 主链 | 真实ID；计划10/料5；每道工序报工；source/WIP/FG位置的Stock Ledger；转料、消耗/制造、成品入库单据关联 | 未验证 |
| CASE-02 Q02/Q04/Q05/U01 | 原始输入、字段/全局精度、舍入配置、服务端结果、保存回读、换算后库存量；尤其SUM(qty)耗量与transfer_qty库存单位是否一致 | 未验证 |
| CASE-02 V01/V02 | 估价方法及入10@2、入10@4、出5前后的库存量、值、价；不得只看界面单价 | 未验证 |
| CASE-05 无下游10→8 | 原卡与时间行内容、cancel/amended_from、原因/人员/时间、有效量和剩余量；是否自动填loss2导致仍Completed；原单保留和普通删除拒绝 | 未验证 |
| CASE-06 领10退2待审3 | 生效单、草稿单、来源仓12/WIP8、累计领10/退2/净8；提交退单后的账；无消耗记录应区别于明确实耗0；另有实际耗7时单独记来源 | 未验证 |
| CASE-04/07 权限并发 | 普通业务角色、对象范围、请求标识、两个重叠请求时段、成功后丢响应重试、明细/汇总/账计数 | 未验证 |

运行遇到环境或依赖阻塞时，记录命令、输出和阻塞对象；不改产品以制造通过，不把上游单测等同本项目业务验收，不扩成全ERP回归。

## 5. 本轮实际运行追加（与前述静态阶段分开）

环境和启动中断/恢复事实见[本机记录](../R03-R05/environment.md)。仅本机ARM64隔离站点`r05.localhost`，没有客户数据；Compose项目`xgd-r05-20261026`。配置见[compose.json](../../.evaluation/r05-erpnext/compose.json)。实际ERPNext15.124.1、Frappe15.124.0、Bench5.31.1；官方镜像没有.git，已核8个关键业务/测试文件blob与第2节固定来源一致。不是全镜像源码审计。

### 5.1 环境与已有测试的实际结果

| 动作/测试 | 真实执行与结果 | 能证明的范围 |
|---|---|---|
| 固定ARM64镜像拉取 | 按`sha256:4160d3c77aafb41c7770aad3daa67254a13f8750765ee83d632434ed564a4834`拉取成功 | 镜像已取得；版本与关键文件随后单独核查 |
| 独立db/redis启动 | `docker compose -f .evaluation/r05-erpnext/compose.json up -d --wait db redis-cache redis-queue`退出0 | 新项目3个服务可运行；不证明应用业务正确 |
| 建测试站点 | 原生`bench new-site r05.localhost`安装erpnext，并仅在本隔离站点启用allow_tests；退出0，日志site-init.log（仅本地保留；见 publication/evidence-index.json） | Frappe/ERPNext schema初始化完成；没有客户部署或UI验收 |
| 原生库存精度用例 | `test_material_transfer_for_manufacture_qty_precision`：1项，0.204秒，OK，命令退出0；日志（仅本地保留；见 publication/evidence-index.json） | 内存单据剩余0.001允许、0.002拒绝；没有六位库存回读证明 |
| 原生工单两个用例 | `test_job_card`、`test_non_consumed_material_return_against_work_order`：2项，2.854秒，OK，命令退出0；日志（仅本地保留；见 publication/evidence-index.json） | 原生转WIP/作业卡/制造与下游取消保护；余料仅生成草稿，不能当提交退料通过 |
| 原生作业卡数量用例 | `test_job_card_proccess_qty_and_completed_qty`：1项，1.222秒，OK，命令退出0；日志（仅本地保留；见 publication/evidence-index.json） | 原生计划10报8后自动损耗2、最终产出8仍Completed的断言通过；正好确认与本项目明确良/不良输入存在语义差异 |

实际命令使用第3节已核选项，将`<隔离站点>`绑定为`r05.localhost`，前缀为`docker compose -f .evaluation/r05-erpnext/compose.json run --rm -T bench`，并加`--failfast`。上述三次调用严格顺序执行，未并发改同一测试库；日志保留完整输出。

**合计仅为上游定向测试4项通过。** 不是R02的4项通过，不是完整CASE-01～07通过，不是全ERP回归；测试均以原生测试身份执行，不能证明普通角色权限。此前静态结论中涉及这些同名测试的“未执行”仅指静态阶段，当前结果以本节为准。

### 5.2 R02 主链和领退料数量子集

实际入口为`bench --site r05.localhost console`，在隔离站点执行[evaluation脚本](../../.evaluation/r05-erpnext/probes/r02_probe.py)：`exec(open('/eval/r02_probe.py').read(), {'__name__': '__main__'})`。原生factory只构造合成主数据/文档，正常`insert/submit`调用产品方法，没有改产品代码。操作者为Administrator；不能证明普通角色或HTTP权限。每个成功案例提交事务，异常案例回滚；控制台会捕获Python异常，因此**不以console退出0判定成功**，以保存JSON中的状态、回读量和日志为准。

| 子集 | 实际输入及结果 | 证据与边界 |
|---|---|---|
| CASE-01数量主链 | 计划10、三工序各报10、BOM每件0.5、原料初20；领5到在制、制造10；最终源15、WIP0、成品10、工单产出10，5项数量检查一致，已commit | attempt4 JSON（仅本地保留；见 publication/evidence-index.json）、日志（仅本地保留；见 publication/evidence-index.json）、[当次脚本](r02-probe-attempt4.py)。工单`[本地样例编号已移除]`。原生自动生成作业卡，非目标“人确认生成”；没有生成防重、普通角色、全部失败分支、手机验收。 |
| CASE-06领退及草稿 | 原料初20，领10、退2，再存未提交领料草稿3；最终源12、WIP8、累计领10/退2、成品0，6项数量检查一致，已commit | attempt5 JSON（仅本地保留；见 publication/evidence-index.json）、日志（仅本地保留；见 publication/evidence-index.json）、[当次脚本](r02-probe-attempt5.py)。工单`[本地样例编号已移除]`。草稿不是已配置审批工作流；字段consumed_qty=0仅表示未提交消耗记录，不能当测量实耗0。未验证实耗7、进度UI或全部越限。 |

制造单的用料根据已转数量生成，未测量实际消耗；不能用该结果证明实耗来源符合要求。时间行采用执行时刻且没有Employee，未执行上海时区工时/休息/预计工资样例。两条成功主链未因后续边界检查重复创建。

首次退料helper生成单据带站点默认公司，与测试工单公司不同；选择工单公司及其成本中心后退2提交成功。这是评估输入修正，未关闭仓库公司校验。实际UI是否自动补对公司未验证。

### 5.3 精度回读：两项一致，一项目标差异

[脚本](../../.evaluation/r05-erpnext/probes/precision_probe.py)调用原生BOM提交和Work Order草稿保存；临时通过System Settings正常保存设置`float_precision=6`、`Commercial Rounding`，随后恢复原字段及defaults并比较一致。没有Property Setter、库存过账或产品计算改动。结果JSON（仅本地保留；见 publication/evidence-index.json）、日志（仅本地保留；见 publication/evidence-index.json）。

| 输入 | R02最终期望 | 实际保存回读 | 判定 |
|---|---:|---:|---|
| Q02：100×0.083333 | 8.3333 | 8.3333 | 本次BOM→工单草稿数量子集一致 |
| Q04：100×0.000167 | 0.0167 | 0.0167 | 同上 |
| Q05：3×0.00005 | 0.0002 | 0.00015 | 当前配置未做目标最终四位舍入 |

三项BOM原始小数均保留，DB行与文档回读一致。Q05不是证明底座无法配置，而是证明**仅把全局设6位并不能同时实现六位输入和最终四位规则**。结果字段单独精度能否满足、跨单位/库存/展示/导出/AI一致性仍未验证；源码中Python float也未因两个数值一致而变成全程十进制。

### 5.4 重复过账、超退和取消修订

执行[boundary_probe.py](../../.evaluation/r05-erpnext/probes/boundary_probe.py)，调用原生文档方法，不经HTTP；失败在评估脚本事务边界回滚。分支分别记录，不合计成“CASE-04/05/06通过”。

| 动作 | 实际观察 | 结论限制 |
|---|---|---|
| 同一已提交领料Stock Entry再次submit | 调用返回；源12/WIP8不变，相关库存账5条不变 | attempt2结果（仅本地保留；见 publication/evidence-index.json）：同一单据此路径无重复记账；不证明不同单据请求去重、丢响应找回或并发。 |
| 保持作业卡批量10，取消10后仅改完成量8、继承损耗0 | 拒绝：Total Completed Qty 8必须等于Qty to Manufacture 10；此案例回滚 | 原生卡的批量与提交校验限制，不当作逐笔更正通过；见attempt2。 |
| 取消10后修订卡批量为8、完成8，工单计划仍10 | 成功提交；原卡`[本地样例编号已移除]`取消且保留完成10，修订卡`[本地样例编号已移除]-1`关联amended_from、完成8/损耗0；工单`[本地样例编号已移除]`计划10，工序完成8、Work in Progress | attempt3结果（仅本地保留；见 publication/evidence-index.json）：可复用原生cancel/amend和批量机制；它改变作业卡批量，不是已经实现“每笔时间行独立冲销”。原卡普通删除限制、工资回写和更正重试未验。 |
| 领10退2后，再复制有效退料单为新草稿，要求退9 | 原生NegativeStockError拒绝；事务内曾出现WIP -1/第6条账，脚本回滚后恢复WIP8/5条账 | 只证明本输入的负库存拒绝与评估回滚；**不是**已证明请求层自动回滚，也不是工单最大可退量校验。若在制仓有其他工单库存，仍须另核关联上限。 |
| 领10退2后再次调用原生退料生成器 | 返回两行：WIP→来源10、来源→WIP2，未得到单一“剩余8”行；只保存观察，不提交这张生成草稿 | 见attempt3的`native_return_factory_observation`；这是需要核对的真实生成结果，不能记退料全通过。是否有UI后处理、正确二次退料路径及最小适配仍未验证，不改产品绕过。 |

attempt3日志（仅本地保留；见 publication/evidence-index.json）与attempt2日志（仅本地保留；见 publication/evidence-index.json）保留。保留原生仓库归属、单据状态、下游依赖、完成量和负库存校验；未关闭这些保护以制造通过结果。

### 5.5 失败尝试及证据保留

| 尝试 | 实际失败与处理 | 不可据此得出的结论 |
|---|---|---|
| r02 attempt1 | 上游_Test UOM只允许整数，初始化拒绝；JSON（仅本地保留；见 publication/evidence-index.json） | 尚未开始生产样例，不能算产品主链失败 |
| r02 attempt2 | R02 件尚未初始化；脚本初始化位置不正确，随后独立正常插入/回读；JSON（仅本地保留；见 publication/evidence-index.json）、诊断（仅本地保留；见 publication/evidence-index.json） | 不是已证明的数据库缓存缺陷 |
| r02 attempt3 | IPython exec命名空间问题导致build_case未找到；两案例都无业务步骤；JSON（仅本地保留；见 publication/evidence-index.json） | 不是ERPNext方法不存在 |
| r02 attempt4 CASE-06 | 默认公司与仓库不匹配被原生校验拒绝，整个CASE-06回滚；CASE-01已提交并保留 | 不把回滚前的领料快照当已持久化CASE-06 |
| boundary attempt1 | 写结果前的恢复核对遍历被set_single_value原地添加的modified字段而报错，未生成结果JSON；日志（仅本地保留；见 publication/evidence-index.json）、[脚本](boundary-probe-attempt1.py) | 无可用完整结果，不计通过；随后只读确认未留下该C05工单/卡，见恢复检查（仅本地保留；见 publication/evidence-index.json） |
| boundary attempt2超退 | 脚本预期生成器一行，实际多行，尚未提交超退输入 | 不是已验证的超退拒绝；attempt3改从有效退料单复制输入并另存生成器观察 |

一次失败的结果复制留下空文件`boundary-result.json`，不是JSON证据；有效结果为带attempt2/3后缀文件。没有删除失败日志或重写它们为成功记录。

### 5.6 当前状态与待验项

R05 **部分完成**：静态筛选、4个原生定向测试、CASE-01/06数量子集、三个小数回读及上述边界已取证；完整R02样例与成本判断未完成。待补：最终精度及跨单位库存、二次退料生成、普通角色对象权限、请求级重试/并发、逐笔冲销保留、PC/手机。AI、客户恢复部署和真实试点仍分别受后续卡约束，没有运行。

下一步先处理影响选型的这些具体证据缺口，再做R06；不能把本机管理员CLI成功写成可交付。已确认的失败或差异保留为改造输入，本轮没有开始产品改造。

### 5.7 持久化复核与服务收尾

2026-10-26 10:23:03 UTC（18:23:03北京时间），新建console连接只读回查：persistence-readback.json（仅本地保留；见 publication/evidence-index.json）、日志（仅本地保留；见 publication/evidence-index.json）。确认工单00001的三工序/入库、00002的领10退2和草稿、00006的原卡取消/修订关联均已保留；制造设置恢复为`disable_capacity_planning=0`（未禁用容量规划）、backflush=BOM、独立消耗0、超产0，系统精度3/Banker's Rounding。站点样例时区为America/New_York，未当成CASE-03上海工时验收。

运行后仅停止`xgd-r05-20261026`的db/redis-cache/redis-queue，保留数据卷与镜像；Docker Desktop保持运行。停止后的实际状态见容器状态（仅本地保留；见 publication/evidence-index.json）。没有客户部署，没有删除任何用户数据或其他项目容器。

## 6. 权限、并发、数量与小屏补证（同日追加）

用户授权先补R05再进入R06。本轮沿用第5节已保存成功证据，只对缺口建立 `R05F-M`、`R05F-A`、`R05F-U` 新合成样例。物料／账号准备／HTTP测试／UI顺序执行，仅明确并发案例使用两个重叠请求。没有修改ERPNext或Frappe产品代码。

| 补证 | 实际结果 | 依据与后续约束 |
|---|---|---|
| 二次退料、上限、明确实耗 | 自动二次退料仍混入正反两行；原生手工退余8可接受（试验回滚）；WIP有其他来源库存时本工单余8退9也接受（回滚）；明确耗7已提交，净领8／实耗7／余1分别有单据 | [物料报告](followup-material.md)、原始JSON（仅本地保留；见 publication/evidence-index.json）。生成净额和工单关联上限必须适配，不新建库存账 |
| Q05配置与U01单位 | 需求字段设4位仍存0.00015；库存字段设4位可入0.0002，但工单不一致。0.5g消耗正确扣库存0.0005kg，工单却汇总为0.5kg | 配置不能独立满足端到端数量目标；全程十进制改造范围仍待R07绑定 |
| 普通角色／对象权限 | 所测资源GET/列表/写/计时接口能拒绝无权对象；辅助get_operation_details仍向无业务角色返回受限子行name/idx。Manufacturing User可写库存草稿 | [权限报告](followup-access.md)、请求（仅本地保留；见 publication/evidence-index.json）。显式对象白名单不是自动部门/指派策略；需要收窄岗位并补辅助入口 |
| 并发／重复请求 | 同卡各2为200/417且净+2；同卡各1只留一笔并自动损耗1；不同卡各1为200/500死锁，仅+1。查失败卡后一次顺序恢复成功，最终10 | 并发（仅本地保留；见 publication/evidence-index.json）、恢复（仅本地保留；见 publication/evidence-index.json）、重试（仅本地保留；见 publication/evidence-index.json）。原并发仍失败；无请求原结果找回，I05/I06未验 |
| 原事实保护 | submitted原量改/删拒绝；同普通账号取消后可删除原卡，原时间子行也不存在；Deleted Document另存副本 | delete.json（仅本地保留；见 publication/evidence-index.json）、回读（仅本地保留；见 publication/evidence-index.json）。审计副本不等于业务原事实不可删除 |
| 小屏普通业务 | 390×844普通工人报10提交并刷新，工序10／成品0／时间行1；普通仓库角色提交既有领5草稿，源15/WIP5；在制工单没有原生退料入口 | [小屏报告](followup-mobile.md)。真实手机、网页退料完成、扫码、弱网未验证；需要配置/必要页面适配 |

配置恢复结果见物料JSON和账号/库存初始化JSON；无真实客户数据。浏览器新增本机Web服务的命令、限制和收尾见[环境追加](../R03-R05/environment.md)。脚本错误、接口拒绝和死锁保留原始日志，不合并为通过数量。

**收口依据：**已能区分统一库存链等可保留能力、已复现必改点和未验证项，达到本卡“核心适配与成本差异明确后停止”的条件。R05完成指选型核验收口，不指修复完成、全部R02判据通过或可交付。未验成本量化、全程十进制、完整权限/并发/冲销、真实手机、AI与客户环境继续列入后续卡；不自动启动B/A/Z实施。
