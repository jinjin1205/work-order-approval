> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R07 数量、单位与退料入口绑定

2026-10-26。**仅静态绑定计划；没有产品改动、测试实现或数据库执行，不是修复通过证据。** 对应 B04 数量子项、B07 用料生成子项、B10 单位与实耗子项、B11 退料子项。B04 工时／指标、B07 结构锁与全局 BOM 修改、B10 成本、B13 手机整卡不在此文件解锁。

## 1. 依据、身份与已知反例

- 规则：[决策与范围 C05](../../docs/决策与范围.md)、[R02 输入](../R02/fixture-spec.md)、[预期 CASE-02/06](../R02/expected-results.md)。数量输入及中间量保留十进制六位能力，需求最终四位、四舍五入；库存单位不得混加。累计领、退、净领与明确实耗分别保留。
- 失败输入直接复用 [R05 物料补证](../R05/followup-material.md)：Q05 `3×0.000050`，工单需求仍 `0.00015`、库存已领为 `0.0002`；领10退2再次生成反向两行；本工单余8而WIP另有10时退9被接受；消耗 `0.5g`，库存扣 `0.0005kg`、工单耗量却为 `0.5kg`。这些是历史受控运行结果，本轮不重跑。
- 基线：ERPNext `v15.124.1 / 4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；Frappe `v15.124.0 / f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab`；ARM64 镜像 `sha256:4160d3c77aafb41c7770aad3daa67254a13f8750765ee83d632434ed564a4834`。
- 读取本地只读副本 `.evaluation/r07-sources/`。`git hash-object` 本轮回读：`work_order.py=808777b02a1833279c5073fce26902d83eca60c6`、`stock_entry.py=fed639c03b7889d5c3897edcf5c9aaa59d3295de`，与 R05 已登记 blob 相同。另记录 `bom.py=cbd9d38d1bd3b0cf37debb0ea4dca8b929d7536c`、`frappe/utils/data.py=1f2eb5f02159f0e0ee811277675bb2e92905685b`、`frappe/model/base_document.py=ae015e0503a48c61193d2e677d55f877f9810b77`。不扩称全镜像逐文件一致。

下表路径是上游仓库真实路径；本地副本在上述目录下。行号为本基线。

## 2. 权威入口、调用链与最小允许范围

| 绑定项 | 已存在的文件／签名／调用者 | 复用及局部改动边界 |
|---|---|---|
| Q：工单最终需求 | `erpnext/manufacturing/doctype/work_order/work_order.py:1238` 的 `WorkOrder.set_required_items(self, reset_only_qty=False)`，由 `validate:176`、`get_items_and_operations_from_bom:1221` 调用；后者由 `work_order.js:580` 表单调用。该函数调用 `erpnext/manufacturing/doctype/bom/bom.py:1159 get_bom_items_as_dict(bom, company, qty=1, fetch_exploded=1, fetch_scrap_items=0, include_non_stock_items=False, fetch_qty_in_stock_uom=True, ignore_permissions=True)`。 | **局部改造＋配置候选**：在 `set_required_items` 的追加和 `reset_only_qty` 两条赋值路径落实同一个最终需求舍入，不新增计算服务，不在页面再算一次。`required_qty` 为库存单位；`StockEntry.get_work_order_raw_materials(self, qty):3021` 已消费它，核该调用量与保存量一致。此范围只足以绑定 Q05 等最终值修复，不等于全程十进制要求达成，见第3节。 |
| U：工单实耗单位 | `work_order.py:1382 WorkOrder.update_consumed_qty_for_required_items(self)` 现为 `SUM(detail.qty)`；`StockEntry.on_submit/on_cancel → update_work_order:2285 → WorkOrder.update_status:421 → update_required_items:1197` 到达此汇总。 | **局部改造**：改用与库存账一致的 `detail.transfer_qty`，保留已提交、同工单、实际出库行、原料／替代料原有过滤；领退汇总 `update_transferred_qty_for_required_items:1286`、`update_returned_qty:1354` 已读 `transfer_qty`，不另造平行合计。取消后按仍生效单据重算。 |
| T：换算与过账 | `erpnext/stock/doctype/stock_entry/stock_entry.py:682 StockEntry.set_transfer_qty(self)` 在 `validate:242` 调用，计算 `qty×conversion_factor` 并按库存数量精度舍入；`on_submit:532` 调 `update_stock_ledger:2072` 后回写工单。 | **配置后使用＋必要校验**：保留正常 `save/submit/cancel`、原生单位、仓库、负库存与估价入口；U01 库存换算历史子项正确。B10 核领料超额分支 `_validate_no_excess_transfer:1257` 仍累加 `item.qty`，若纳入跨单位领料，须同次改为库存单位比较并补回归；不能只修退料。零／负换算系数和非法数量必须在外部业务输入边界明确拒绝。 |
| R1：退料生成 | `work_order.py:2017 make_stock_return_entry(work_order)`；网页 `work_order.js:257 create_stock_return_entry` 调此白名单方法。它调用 `stock_entry.py:4378 get_available_materials(work_order, stock_entry_doc=None)`；后者调用 `get_stock_entry_data(work_order, stock_entry_doc=None):4442`。`StockEntry.add_transfered_raw_materials_in_items(self):3262 → update_item_in_stock_entry_detail(self, row, item, qty):3324` 填草稿行。 | **局部改造**：查询补实际方向和库存数量，领入加、退回减、明确耗料减；按实际物料及在制仓聚合，不把退入来源仓再次当领入。仅生成正的剩余量，零不生成、负额报告需核对，不造反向／负数草稿。保留单据生成和同一库存账。 |
| R2：提交时可退上限 | `StockEntry.validate_component_and_quantities:1222` 仅部分条件调用 `_validate_no_excess_transfer`，后者对 `is_return` 直接返回；不能依赖它阻止超退。`validate:242` 在过账前运行。 | **必须补校验，仍在原 Stock Entry 控制器内**：对 `purpose=Material Transfer for Manufacture AND is_return=1` 的每次提交，按当前生效事实重新检查第4节额度及原单；不可受 `fg_completed_qty`、BOM组件校验配置或回冲配置开关绕过。可在本类增加一个只负责退料校验的方法，由既有提交生命周期调用；名称属拟新增，不冒称已有接口。 |

**共享调用影响：**`get_available_materials` 还被 `_set_serial_batch_for_disassembly_from_available_materials:470` 调用；`add_transfered_raw_materials_in_items` 还在 `get_items:2694` 的制造／实耗生成分支调用。保留 `stock_entry_doc.purpose == "Disassemble"` 的原语义，回归拆解、批次、序列号及替代料。`get_bom_items_as_dict` 被 BOM 查询、Stock Entry 原料／废料和 Work Order 共用；不得为修 Q05 无范围地全局改变返回数量或单位。

## 3. 十进制的已绑定范围与未满足门槛

**2026-10-27 B04 六位/损耗续接绑定与实测（不覆盖下方历史计划）：**见[B04本批记录](../B04/precision-loss/run-record.md)。复用 B01 既有两站、原生 `System Settings.save → on_update/set_defaults`，仅将本地开发/测试站默认 Float 精度设为6；不改 Currency 精度、各字段显式精度、舍入方法或 Frappe。`configure_quantity_precision.py` 限定两站，默认只读，`--apply` 才保存。探针的数量、库存保存通过原生单据；设置临时六位后，0.123456 的 transfer_qty/库存流水/余额一致。该配置影响所有未显式指定精度的原生 Float 字段，不是仅显示位数，也不证明全程 Decimal。

两层 BOM 原始行 0.083333×0.000167，在展开子表保存为0.000013917；计划1000000后原生最终13.9170，不提前舍入参考13.9166，六位配置前后相同。读库、BOM、需求、库存对象均为float，故完整G1仍未通过。Q03原生BOM Item无材料损耗字段，成品工序损耗10%得到成品损耗0.2，用料仍25，未得到27.5。

**材料损耗候选绑定（本批实施前判断，最终结果见下）：**唯一输入应在BOM Item行新增中文“材料损耗率（%）”，默认0；Work Order Item不再配置。`BOM.get_exploded_items` 的叶项/子BOM分支、`get_bom_items_as_dict` 的非展开分支须消费同一损耗源；展开结果不得再次乘损耗，`stock_qty=qty×conversion_factor` 单位恒等式必须保留。新增字段还涉及原生元数据迁移、BOM成本显示和已提交BOM冻结，必须在精度方案确定后绑定其影响及真实命令，不能先改stock_qty掩盖损耗或只改工单造成两套结果。仅缺字段不能推断整套改动已可实施。接受标准是Q03=27.5000、零损耗保持原结果、单层/两层每层损耗各计一次、保存重读及原生下游一致、旧单不回填；本批最终限定合法范围为有限非负数，不擅定100%上限。

**用户续答已确认第一种方案：**保留ERPNext内部数值类型，对限定数量链采用十进制计算和一致性验收；准确性要求不降低，不改Frappe全局/库存估价/数据库现有数字类型。原TRD的“所有内部类型必须Decimal”在本绑定范围内调整为关键数量链精确计算及输入/保存/下游一致性验证，不推及未验的其他业务。

**本轮实施新增绑定：**复用`bom.py:BOMTree`的树结构与遍历，从原BOM/BOM Item的数据库文本数量读取Decimal，避免用已舍入的BOM Explosion Item数量重算；`get_bom_items_as_dict`保留原元数据/权限/仓库查询，原料数量改消费同一树计算，废料分支保留原语义。只在原料最终需求输出统一四位四舍五入，然后交还原生接口数值类型；移除WorkOrder原来独有的最终舍入，避免两个计算出口。BOM Item新增唯一中文“材料损耗率（%）”，默认0，禁止负数/非有限数；BOM用料成本显示须计入同一损耗，仍用原成本计算，不改库存估价。每层损耗仅计一次，保留原qty和换算关系。允许改`bom.py`、`bom_item.json`、原WorkOrder最终舍入三行及`test_bom.py`，不新建数量框架或平行BOM树。

**运行与验收：**先把当前失败固化到原`test_bom.py`的新`TestBOMRequiredQuantity`，只运行该类；先红后绿。复用原生测试fixture，新增两层差异、Q03、每层损耗、库存单位换算、负损耗拒绝/批准后冻结和废料不变样例。元数据只在既有隔离测试站执行原生`bench --site xgd-test.localhost reload-doc manufacturing doctype bom_item`，在测试事务之外，记录前后；业务样例回滚。源码变更后重新构建并核文件哈希，验证消费者实际Stock Entry及保存重读。已验Q05不再原样重跑；共享计算出口变化的舍入边界以新半值样例验证。满足本批范围即停止，G1完整范围/工时/G2/G3继续保留。

已核实：`BOM.update_stock_qty:610` 使用 `flt` 相乘；爆炸展开 `get_child_exploded_items:931`、`get_bom_items_as_dict:1159` 使用数据库比例与后续 Python 计算；`frappe/utils/data.py:939 flt(...)` 先转换为 Python `float`，非法文本可变成0；`BaseDocument.get_valid_dict:404` 与 `_fix_numeric_types:724` 会把 Float/Currency/Percent 转成 `float`。MariaDB 映射 `database/mariadb/database.py:174-178` 虽为 `decimal(21,9)`，**数据库字段为 decimal 不证明输入、计算、序列化全程为十进制**。

- 可绑定的首个局部验证：保持既有 BOM 展开和工单入口，明确 Q05 的最终四位权威值，并核保存／重读／下游取值一致；只改显示精度不合格。最终舍入只在定义的输出边界执行，不能先四舍五入每个中间用量。
- **仍未解锁 B04 完整数量实现**：需补六位原始输入→BOM单层／多层→父项基数→需求→入库数量的类型及舍入证据，证明局部 Decimal 处理不被 Frappe 存储前转换破坏。不能从 `Decimal(str(已经计算过的 float))` 声称恢复了原十进制精度。
- Q03 的材料损耗率来源也未绑定：已读 BOM Item 无对应材料损耗率字段；BOM `process_loss_percentage` 由 `set_process_loss_qty:1048` 计算成品损耗，不能直接充当 `单位用量×(1+材料损耗率)`。该子项保留待绑定，不擅自新增字段或把损耗预先混入单位用量后宣称公式通过。
- 如果满足六位中间量必须广改 `flt`、Frappe全局序列化、库存估价或财务，按 R06 重评该项范围；本绑定禁止全局替换 `flt`、改数据库数字类型、复制新账本。B04 工时、良品率等另行绑定。

## 4. 退料对象、原单、额度与事务

仅统计 `docstatus=1` 的原生 Stock Entry；草稿／待审批不入正式累计，取消记录不计生效数量但保留原文档。数量统一使用 `transfer_qty` 及该实际物料的 `stock_uom`。

1. **工单额度**：同公司、同工单、同实际物料、同在制来源仓，`可退＝已有效领入该仓−已有效退回−已明确从该仓耗用`。当前待提交退单自身不预先减一次；同单重复行先合计再比较。`original_item` 只服务工单计划项对应，不能把不同实际物料库存互相抵额度；批次／序列号在对应物料额度内再核原生可用身份。
2. **原领料关联**：复用 `Stock Entry Detail.against_stock_entry`（Link）和 `ste_detail`（子行ID），字段定义在 `stock_entry_detail.json:453/463`，当前退料生成未填。仅制造退料分支由服务端填写／验证：原单生效且非退料、同工单／公司／实际物料，原单目的仓等于本次退料来源仓；退料目标仓回到该原领料来源仓，且操作者有权。另核 `本原领料行数量−已关联有效退料`，防止同一原行重复退。工单总余量与原行余量两个条件均须成立；不根据仓库总库存或相同物料名称猜原单。
3. **多笔来源**：生成器根据真实原领料行拆行并填写上述引用。**本轮工程方案，非原生既有行为**：按 `posting_date`、`posting_time`、`Stock Entry.name`、子行 `idx`／`name` 升序分配，只能在已核实的工单可退额度与各原领料行余额内分配，合计不得超过工单可退量。已有无法确认原单的历史退料不能静默猜关联或自动迁移，须作为该对象的人工核对阻塞。该引用方案不创建新库存事实表；`against_stock_entry/ste_detail` 的现有在途调拨与拆解用途保持不变（`update_transferred_qty:3636` 仅在普通 `Material Transfer + outgoing_stock_entry` 分支运行）。
4. **统一事务锁门槛**：只在退料生成时算余额或只锁退单都不足以防并发。退料、领料、明确实耗／制造耗料及它们取消会改变同一额度，须在同一数据库事务中先取得同工单锁、重读有效量，再校验并经原生入口完成库存与汇总；不能中途提交或无限重试。真实现有原语为 `frappe.db.get_value(..., for_update=True)`／`frappe.get_doc(..., for_update=True)`，`Document._save:380` 自身已锁当前单据但并未统一锁工单。**与权限／并发绑定统一确定获取顺序、当前读方式、取消顺序及失败回滚后才能实施 R2**；此文件不另外发明一套锁协议。
5. **取消／更正**：已发生关联退料或耗料时，取消原领料必须按同锁检查剩余事实及下游依赖；不靠取消原领料替代部分退料，不通过改工单合计处理。退料取消后原单和取消记录留存、库存反向凭证与有效累计一致。普通角色校验当前对象与仓库权限，隐藏按钮不是授权。

中文业务显示统一“累计领料、累计退料、净领料、实际消耗、可退数量”；净领8不自动显示为耗8；材料损耗和产出损耗不混称。错误应给出物料、库存单位、可退量及关联单据，不能把内部异常当成功提示。必要网页入口由 B13 绑定：原 `work_order.js:244` 只在 Closed/Completed 显示退料按钮，不能为退料强行关闭工单。

## 5. 测试绑定与执行前置

本节均为**实施后待执行**。使用 B01 绑定的隔离测试环境及改动后源码，独立合成前缀；不得在客户库执行。先记录源码提交／工作区diff、镜像、站点、配置、输入、实际输出、回读和限制。R05 四项历史测试及原 JSON 保留，不重复运行原前缀探针，也不把已有成功数累加成当前全量结果。

已核真实测试与能力：

| 现有测试（可直接复用，不能替代新增反例） | 文件／验证范围 |
|---|---|
| `test_non_consumed_material_return_against_work_order` | `manufacturing/doctype/work_order/test_work_order.py:2115`；含批次／序列原料，领7耗5生成退2，但只保存退料草稿，未覆盖二次退料／超退提交。 |
| `test_partial_material_consumption`、`test_partial_material_consumption_with_batch` | 同文件 `971/2576`；正常部分实耗及批次路径。 |
| `test_material_transfer_for_manufacture_qty_precision` | `stock/doctype/stock_entry/test_stock_entry.py:1581`；直接调用超额领料校验，`33.876−33.875` 时0.001接受、0.002拒绝；不是 Q05 或真实库存过账。 |
| `test_work_order_manufacture_with_material_consumption` | 同文件 `1612`；明确实耗与制造入口关系。 |
| `test_get_items`、`test_get_items_exploded` | `manufacturing/doctype/bom/test_bom.py:30/41`；共享BOM单层／展开基本行为，只有改变BOM共享路径时才需要重跑。 |
| `test_disassembly_with_multiple_manufacture_entries`、`test_disassembly_batch_tracked_items`、`test_disassembly_serial_tracked_items` | `work_order/test_work_order.py:2793/3144/3260`；共享余料查询涉及拆解分支时必须回归。 |
| `test_partial_alternative_item_transfer_with_material_consumption`、`test_backflushed_batch_raw_materials_based_on_transferred`、`test_backflushed_serial_no_raw_materials_based_on_transferred` | 同文件 `4049/1720/1792`；修余料生成与实耗汇总后检查替代料、批次／序列的原有调用。 |

拟新增测试名及位置（**现在不存在，不是已通过测试**）：

| 名称／拟放现有文件 | 输入、动作与必须得到的结果 |
|---|---|
| `test_required_qty_q05_rounds_at_final_boundary`；`work_order/test_work_order.py` | Q05 BOM量0.000050、工单3；生成／保存／重读 required_qty=0.0002，后续原生领料草稿与提交库存数量同值；覆盖 reset_only_qty。仍不能单独判定完整 Decimal 通过。相关实现变化后加 Q01/Q02/Q04 的回归，Q03待损耗映射。 |
| `test_consumed_qty_uses_stock_uom`；同文件 | U01 领0.001kg、退0.0004kg、明确耗0.5g；工单耗0.0005kg，库存余0.0001kg；取消耗料后回到耗0与WIP0.0006kg，文档仍留存。 |
| `test_repeat_return_uses_remaining_stock_qty`；同文件 | 领10退2，再生成仅 WIP→原来源的8；耗7分支生成1；U01耗后生成0.0001kg；无反向2、负数和混单位行；提交部分退、再次生成直到0时无可退行。 |
| `test_return_rejects_excess_and_wrong_source`；`stock_entry/test_stock_entry.py` | 本工单余8、WIP另有10，退9拒绝且无库存／累计变化；未领直接退、跨工单／物料／仓库原行、取消原单、同单拆成5+4绕额度、零／负系数均拒绝。退8正常，累计领10／退10；历史不删除。 |
| `test_return_reference_and_cancel_preserve_totals`；同文件 | 两笔原领料生成的引用明确；部分退2关联正确；重复 submit 不多记，取消退2恢复有效退0与库存，取消后原记录可追；有下游时取消原领料按依赖拒绝／逆序处理，无部分账。 |
| `test_transfer_limit_uses_stock_uom`；同文件 | `required_qty/transferred_qty` 用kg、输入行用g；同单位折算后正常余量通过、超额拒绝；不能比较g数值与kg余额。 |
| 并发验收见并发绑定；本表不虚构现有测试函数 | 两个独立HTTP／DB事务同时退5、余8：最多一笔生效，另一笔明确失败，结果可查；退与耗竞争、退与取消领料竞争同样不能突破额度。失败后无半张库存账，死锁记录并归为未通过，顺序补跑不覆盖原失败。 |

现有 runner 已从 `frappe/commands/utils.py:757` 核实 `--module`、可重复 `--test`、`--failfast`。以下命令须在 **B01 新建的隔离测试容器内、bench 目录**运行，拟用站点 `xgd-test.localhost` **当前尚不存在，本轮未执行**。B01 须先创建站点，并挂载或构建改动后源码，核实容器内实际版本／文件确为待测改动；否则不得将运行结果计为实施回归。R05 站点及历史证据保留，禁止使用 R05 Compose／站点作为开发测试环境：

```sh
bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --test test_non_consumed_material_return_against_work_order --test test_partial_material_consumption --test test_partial_material_consumption_with_batch --failfast
bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.stock.doctype.stock_entry.test_stock_entry --test test_material_transfer_for_manufacture_qty_precision --test test_work_order_manufacture_with_material_consumption --failfast
```

新增测试写入上述真实模块后沿用同一命令，将 `--test` 换成对应新增名称；不得在函数尚不存在时将“未收集到测试”当通过。新测试站点必须已允许测试，设置入口为 `bench --site xgd-test.localhost set-config allow_tests true`（仅在上述 B01 新隔离测试容器内执行）。真实并发另由普通角色独立请求执行，不能用同连接顺序 submit 冒充。

## 6. 停止条件与禁止区域

本证据完成“现有入口／反例／可复用命令／局部范围”的绑定。实施卡仍按依赖逐项判断：UOM汇总和退料生成可作为独立修复子项；R2依赖统一锁／权限绑定；Q05局部结果不解除完整Decimal门槛。所有拟新增测试均未实现、所有修复效果均未验证。

只允许改本表列明的 ERPNext 原生控制器相关分支、必要中文提示及对应已有测试文件；字段配置复用原生 Property Setter，持久配置与源码打包由 B01/B03 绑定。不得直接编辑此只读镜像副本作为已部署实现；不得改原 R05 探针及已落证据、全局 Frappe 数字处理、库存账／估价核心、财务、无关BOM行为、所有界面或客户数据。不新增通用数量引擎、平行库存账、吞异常／默认0兜底。发现修改需要越过以上范围，记录实际证据并重开对应绑定，不自动扩卡。


## 2026-10-27 本批数量/损耗交接

用户已确认局部数量方案，最终8项真实隔离验收通过6.304秒；源码/失败/修补/受限范围见[B04记录](../B04/precision-loss/run-record.md)。后续不重复Q05或本批不变项。材料损耗仅一个BOM行字段；原料在库存单位最终舍入后再表达交易数量；普通保存及成本直接持久化入口复用同一冻结检查。Frappe、库存估价与已有字段数据库类型未改，完整G1及B04工时/指标未关闭。开发/专用HTTP网页未迁本批字段，不能拿测试站通过作网页部署证明。


## 2026-10-27 B04输入/保存与中文BOM本批绑定

用户已授权先补输入/保存再联调中文BOM，有限范围/真实入口/验证方式和结束条件见[B04本批记录](../B04/input-ui/run-record.md)。先核BOM.quantity、BOM Item.qty与Work Order.qty的原生行为及最小样例，再补失败边界；原生单位正数/整数校验保留。页面只改原BOM成本预览、材料损耗事件与必要中文精度说明；允许既有开发站导入相同元数据并在独立本机端口运行当前源码，原18088审批演示/客户站不变。新增共用函数仅限确有重复的输入校验，不建通用计算层；实现位置在实际失败后补记。G1/G2/G3不因本次绑定通过。

本批实际收口：三处输入在原bom.py/WorkOrder.before_validate共用一个校验；BOM成本直接保存/查询边界复用，舍入后存储上限有真实反例与修补；BOM原生JS预览和中文字段说明完成PC联调。最终4项2.698秒及普通账号页面证据见上述B04记录。开发站18086已导入元数据/当前源码，18088与客户站不变；其余R07绑定与完整门槛保持。


## 2026-10-27 B04工时/指标有限绑定（先于实施）

依据：原CASE-03 T01～T11、M01～M04、C05及本次用户确认C13。基线公开59e6344，实际源码/环境及原生结果见[本批台账](../B04/time-metrics/run-record.md)。本节只解锁下表，不解锁B08/B14整卡。

| 真实入口 | 本次分类与允许改动 | 验收与限制 |
|---|---|---|
| `job_card.py:JobCard.validate_time_logs` → `set_expected_and_actual_time` | 原生起止差、跨天、重叠检查复用；真实探针发现未结束行可保存伪造分钟、只有结束时间可把伪造分钟汇入总数。只补缺开始时间拒绝和未闭合行分钟清零；完整原生经过分钟保持原语义 | 保存重读，闭合时间重算、开放计时0、缺开始拒绝、倒序及相交保护。审批/权限/原记录保护不移除 |
| 同模块新增非白名单内部`calculate_report_time(start,end,*,rules,operation=None,shutdown_seconds=0,overtime_seconds=0)` | 没有可直接套用的休息/人工停工/允许加班计算。复用Frappe日期解析，新增本项目必要的整秒、日循环重叠并集和确定性首条规则匹配；不新建服务/规则表 | T01～T11、跨3天、优先级/工序、缺配置与无匹配区分、非法秒值/时段。规则列表必须由调用方明确提供，`[]`明确无规则，`None`为缺上下文拒绝；返回命中ID和无规则说明。Asia/Shanghai为本批时区；未生成业务事实 |
| 同模块新增非白名单内部`calculate_report_metrics` | 良品率/未清/完成比例/领料比例/效率/计价使用C05/C13的已授权数据参数；不把原生自动process_loss认作不良，不把工序hour_rate认作工资 | M01～M04、计时2小时×10=20、计件只良品、零分母None（页面“—”）、无效输入。返回Decimal及必要分子/分母，不保存百分比，不构建聚合账或改状态 |
| 原`bom.py:validate_quantity_input` | 同一正数量规则增加明确`allow_zero`选项供统计数量使用；已有三处默认仍拒绝0，复用<10亿/六位/有限校验，不复制新数量框架 | 新参数0正例及既有默认0拒绝、上限/六位边界；其余不变样例不重跑 |
| 原`test_job_card.py` | 新`TestProductionTimeMetrics`，复用已有B04造单/原生Operation/Workstation；原生fixture先运行，再红绿回归 | 原命令`bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.job_card.test_job_card --case TestProductionTimeMetrics --skip-test-records --skip-before-tests`；全事务回滚，不初始化无关测试模块 |

最小方案：两个明确计算函数放原JobCard模块，供B08/B14/B16后续接入；不建新policy服务或数据表。原生分钟仍用于原作业成本，有效秒不暗改该链。内部计算参数不是对外授权接口，不提供客户端可直接写事实的通道。B14负责规则读权限、配置与快照；B08负责确认/人工不良/预计工资字段持久化；B16按生效状态取数据及显示。该计算层可先验，不将消费方尚未完成写成生产可用。

整秒处理：起止保持原值；内部计算返回完整秒（不足1秒部分不计），休息并集后统一取完整秒，不在每个重叠段分别舍入。时区按上海明确转换；不改原生数据库/其他时区链。规则使用priority升序、同priority按规则名稳定排序；错误的启用规则拒绝，停用规则不参与。金额返回精确Decimal，页面/持久化币种精度接入归B08，不另定薪资结算政策。

结束条件：可运行fixture和实际原生失败；上述有限计算及修补红绿通过；原数据/源码核对；原卡和可公开证据提交推送回读。仅关闭本批子项。完整G1、G2、G3，B08/B14/B16持久化/页面与客户验收不提前关闭；新发现登记归属，不自动扩大。

本批实际结果：6组原生探针、初次红色及亚秒交集审查反例保留；最终`TestProductionTimeMetrics`12项通过1.854秒，22项运行源码匹配、11张业务表不变，见[B04工时证据](../B04/time-metrics/run-record.md)。实际入口为`job_card.py:205/1434/1474`、`bom.py:44`及`test_job_card.py:1642`（以本批补丁为准）。规则先按真实交集匹配，再取并集完整秒；计件只良品、效率良+不良按C13。此次只完成计算层及分钟漏洞，不关闭原记录/并发/配置页面与其他数量保存门槛；既有网页未替换。

# 2026-10-31 B10实际领料提交与取消绑定

执行前基线：公开main d5ea916c1e542e32eae6a8f042c72fa7e2c65bb6已fetch一致；维护codex/xgd-maintenance/ERPNext15.124.1上游4e0dce9、Frappe15.124.0。现有41源文件/22Python与b87b2f8累计补丁一致。Docker原未运行，已仅恢复现有dev数据库/Redis与b08-check/ui；不初始化站点/模块、不启动其他项目。五底座选择沿原R03～R07，不再重选。U01单位、B19原审批拒绝、B07用料冻结、B08/B09已验事实保护直接复用。

**做/不做/通过：**推进原B10已有下一包，复用原生Stock Entry、Stock Ledger Entry、Bin和估价。普通限定仓管生成/保存/提交/取消领料，单据、库存、工单累计一致；草稿不入账；真实并发不超本单额度，权限和失败无残留；CASE02移动平均20/60/3→出5余15/45。本卡不实施B11退料生成器或B12成品入库，不更改库存账/估价核心、Frappe、自动发料、财务、字段/DocType和手机。取消只恢复授权本包新样例单据，不删客户/旧记录。完整逆向与跨对象G3仍按原责任卡验收，不以此包代替整体验收。

**已读真实入口与白名单（4个原文件）：**
- work_order/work_order.py:make_stock_entry（whitelisted）当前直接get_doc后生成原生草稿，未显式read/create检查；核无权调用后才补必要权限。get_items/get_raw_materials从已批准本单需求和BOM生成，计划和实发分开；不重算U01。
- stock_entry/stock_entry.py:validate_production_execution→check_production_execution当前未for_update；validate→set_transfer_qty→validate_component_and_quantities/_validate_no_excess_transfer；on_submit先update_stock_ledger后update_work_order；on_cancel先update_work_order后update_stock_ledger。两者必须在库存/工单派生前取得同一父工单锁并重读当前状态/额度，复用原父锁和原数据库事务，不建锁框架。
- 同上：原生组件限额仅fg_completed_qty为空时调用，且Material Transferred回冲设置提前返回；先测真实领料输入，任何最小修补仅限本项目正向领料。原退料、制造/拆解和非项目行为不在此包重写。仓库/物料来源按已批准用料行核实际失败后补，保留原生公司、用户权限、换算和库存不足检查。
- work_order/test_work_order.py:make_approval_execution_fixture最小扩展仅合成库存输入/估价参数，原调用默认不变；stock_entry/test_stock_entry.py新增TestProductionMaterialIssue，复用此fixture、普通仓管和原StockEntry生成/提交/取消；不复跑旧审批或U01全套。

**唯一任务：**原B10的5条勾选及原2026-10-29下一包顺序，新增本日期进度注释即可，不复制清单。沿现有OpenSpec b08-followup-20261028引用到B10；CLI引用模式0任务/blocked不当作完成证明，依用户AGENTS不另造任务表。

**验证计划/命令：**先最小fixture/P0，再真实无权草稿接口、非空fg下超额、物料/错仓/跨单和取消/重复入口反例；仅修已证实缺口。`docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py erpnext.stock.doctype.stock_entry.test_stock_entry.TestProductionMaterialIssue.<明确方法>`，全事务回滚；runner新增Bin/GL Entry等库存旧表保持。允许checks/b10_issue_*构造本包独立物料/仓/工位/普通用户，真实HTTP或独立DB事务并发、受影响浏览器流程及回读；只操作新名单，原始行/凭据私有保存。并发须独立事务真实重叠，不能仅测试for_update参数便称已验。网页若无产品改动也需原生生成/保存/提交的实际操作证据，API不能代替页面。每步记录命令/版本/实际失败；结束前一次独立审查、白名单公开推送/新克隆与精确SHA CI。
