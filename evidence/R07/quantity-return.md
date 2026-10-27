> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

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
