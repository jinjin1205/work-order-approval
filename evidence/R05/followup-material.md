> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R05 物料、精度补证

2026-10-26。范围：独立合成前缀 `R05F-M` 的二次退料、工单可退上限、显式实耗、Q05 局部精度配置、U01 跨单位消耗。沿用 R02 fixture v1；不重跑 Q02/Q04，不改 ERPNext/Frappe 产品代码，不复写历史 CASE-06。当前阶段：**定向源码核查与本机受控补测已完成；三组均有已复现的目标差异，产品未改造**。

## 源码依据

本轮通过 `.evaluation/r05-erpnext/compose.json` 中固定 ARM64 镜像运行只读 Python，读取 `/home/frappe/frappe-bench/apps` 下源码；未在这些读取中初始化 Frappe 站点或执行数据库业务。下列链接为此前 R01 固定版本，运行脚本另记录镜像中对应文件 Git blob SHA，不把版本号相同当作整镜像逐文件核验。

| 问题 | 已读实际入口 | 可据此得出的有限结论 |
|---|---|---|
| 二次退料混入已退记录 | [work_order.js 257～267](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.js#L257)调用 `make_stock_return_entry` 后只 `frappe.model.sync` 并跳转表单；[work_order.py 2017～2035](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L2017)调用可用料查询与自动填行 | 此入口未执行净额合并；全文检索 `stock_entry.js` 未发现 `is_return` 的同类净额处理。真实浏览器操作未验证。 |
| 退料生成根因 | [stock_entry.py 4378～4500](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L4378)：查询读取 `detail.qty`、目标仓和 purpose，未读取 `is_return`；所有 `Material Transfer for Manufacture` 按目标仓累加 | 代码把该 purpose 的退料也作为目标仓转入累加，可解释原证据中的“WIP→来源10、来源→WIP2”。下文独立样例重现，生成草稿没有提交。 |
| 工单关联可退上限 | [stock_entry.py 1257～1259](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L1257)在 `is_return` 时退出 `_validate_no_excess_transfer` | 这一函数没有验证退量上限。不能仅据这一处断言整个提交链无保护；补测在在制仓有其他来源库存时要求本工单超退，以排除负库存检查的混淆。 |
| 跨单位耗量 | [work_order.py 1286～1409](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L1286)：领退汇总 `transfer_qty`，消耗汇总 `detail.qty`；[stock_entry.py 682～693](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L682)计算库存数量 | 原料输入单位不同于库存单位时，工单消耗数和库存数存在明确的口径风险。下文实测已复现为工单耗量口径错误，库存账换算正确。 |
| Q05 局部配置 | [work_order.py 1238～1278](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.py#L1238)将 BOM 数量写入 `required_qty`，未在该入口按字段精度舍入；[stock_entry.py 3021～3033](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/stock/doctype/stock_entry/stock_entry.py#L3021)生成原料量时读取 Stock Entry Detail 数量精度；[property_setter.py 64～90](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/custom/doctype/property_setter/property_setter.py#L64)为原生字段设置入口 | 字段精度可能只改变显示或部分后续入口。补测分别观察仅工单精度配置、再加库存字段精度配置后的保存和账；不在脚本中自行四舍五入。 |

## 实际执行范围与证据约束

脚本：[material_followup.py](../../.evaluation/r05-erpnext/probes/material_followup.py)。在已连接 `r05.localhost` 的 console 中执行：

```python
exec(open('/eval/material_followup.py').read(), {'__name__': '__main__'})
```

本次由协调方串行执行，未与其他业务探针并发改库。结果独占写入容器 `sites/r05-followup-material.json`；已有文件或同合成前缀时拒绝执行，不覆盖原证据。语法检查实际通过；最初 `py_compile` 因 macOS 外部缓存目录写权限失败，随后使用 `compile(source, path, 'exec')` 完成无缓存写入的检查。语法检查不等于业务运行。

1. 新单领10退2，保留自动生成二次退料的原始两行或实际返回；复制已有效退单作为新的原生草稿，输入8，观察能否提交并回滚；另一独立事务给同料在制仓补其他来源10后输入退9，观察工单上限是否拒绝并回滚。随后提交明确输入的消耗7，核来源12、在制1、工单耗7和对应库存账。
2. 全局精度6与 Commercial Rounding 下，仅配置 `Work Order Item.required_qty` 为4，保存 Q05 BOM→Work Order，记录生成库存草稿；再配置 Stock Entry Detail 的 `qty`、`transfer_qty` 为4，生成、提交并回读。只删除本脚本新建的 Property Setter；如原配置已存在则拒绝覆盖。Q05 完成即恢复这些字段，U01 不继承四位库存配置。
3. 新建明确命名的合成 kg/g 单位与1kg=1000g换算。领0.001kg、退0.0004kg后核在制0.0006kg；独立输入消耗0.5g后，核库存扣0.0005kg、在制0.0001kg及工单消耗字段是否同单位一致。

每个分支保留输入、真实ID、文档/数据库回读、库存账、配置、时间与源码blob；异常保存traceback。成功或目标不符均如实保留，异常仅回滚当前事务，明确标注此前已提交的检查点。System Settings、Manufacturing Settings 和 Property Setter 分组恢复，某组失败仍尝试恢复其余组。

## 运行结果

原始结果：material.json（仅本地保留；见 publication/evidence-index.json）；控制台日志：material.log（仅本地保留；见 publication/evidence-index.json）。执行身份 `Administrator`；站点 `r05.localhost`；ERPNext `15.124.1`、Frappe `15.124.0`；时间 **2026-10-26 10:42:44.727607～10:42:48.386595 UTC（北京时间18:42:44～18:42:48）**。实际 console 调用为前述 `exec(...)`；日志返回 `executed_with_target_mismatches`，`errors=[]`，三个分组均有目标差异。此处“无执行错误”不表示业务判据全通过。

| 补测子项 | 真实输入、ID与输出 | 本次判断 |
|---|---|---|
| 二次自动退料 | 工单 `[本地样例编号已移除]`，原料 `R05F-M-RET-RM`；领料单 `[本地样例编号已移除]` 为10，退单 `00014` 为2。再次调用生成器仍为 WIP→来源10、来源→WIP2；期望单一剩余8 | **失败：自动生成数量/方向不符合剩余可退料语义。** 草稿未提交，未把它当成功退8。 |
| 原生手工二次退余8 | 复制已有效退2单为新草稿，明确 `docstatus=0`、输入8，正常 `submit` 接受；事务内来源20、WIP0、累计退10 | **此手工路径通过。** 随后回滚恢复来源12、WIP8、累计退2；不是自动生成器已正确。 |
| 工单关联上限 | 同一初态领10退2；只在分支事务内给WIP另入10，因此WIP可用18；本工单再退9被接受，输出来源21、WIP9、累计领10、累计退11 | **失败：在仓库库存充足时，此原生提交路径允许超过本工单余8。** 随后回滚恢复来源12、WIP8、累计退2，其他来源10也未保留。不能用先前负库存拒绝替代此项。 |
| 明确消耗7与在制余1 | 正常提交消耗单 `[本地样例编号已移除]`，输入7；库存账对应 WIP `actual_qty=-7`、`qty_after_transaction=1`；工单耗7，来源12，累计领10/退2 | **此数量子项通过。** 净领8和实耗7有分别可追溯的单据；余1是本合成样例的在制库存事实，不推断原因或责任。消耗后自动退料仍生成WIP→来源3、来源→WIP2，未提交。 |
| Q05：仅工单字段4位 | 工单 `[本地样例编号已移除]`，BOM原料输入0.000050、计划3；BOM qty/stock_qty精度6且回读0.00005；`required_qty`元数据精度4，但数据库/文档需求仍0.00015；生成Stock Entry也是0.00015 | **失败：仅配置精度不能使权威存储结果成为0.0002。** 不是输入小数被截成0。 |
| Q05：再配置库存字段4位 | 同单再把 Stock Entry Detail 的qty/transfer_qty设4，原生生成及提交单 `[本地样例编号已移除]` 的两字段均0.0002，数据库回读一致，来源0.9998、WIP0.0002；工单已领0.0002但需求仍0.00015 | **部分可配置，端到端目标仍失败。** 库存单/账达到本例四位期望，工单权威需求未统一；不能只展示四位即判通过。没有在脚本中自算并覆盖结果。 |
| U01：领退换算 | 工单 `[本地样例编号已移除]`；合成单位 `R05F-M-kg`、`R05F-M-g`，1kg=1000g。单 `[本地样例编号已移除]` 领0.001kg，单 `00020` 退0.0004kg；来源0.9994kg，WIP0.0006kg，领退汇总分别0.001/0.0004kg | **此领退数量子项通过。** 净领0.0006kg与库存位置一致。 |
| U01：非库存单位消耗 | 单 `[本地样例编号已移除]`输入0.5g、系数0.001；保存qty=0.5g、transfer_qty=0.0005kg，库存账WIP扣0.0005kg，余0.0001kg；工单 `stock_uom=kg` 的 `consumed_qty=0.5` | **失败：工单消耗汇总数值与库存单位不一致。库存单和库存账的换算正确。** 不是整个库存计算都错。 |
| U01：跨单位后自动余料 | 上述消耗后生成器返回 WIP→来源 `-0.499kg`、来源→WIP `0.0004kg`，实际在制0.0001kg | **失败：生成草稿继续混用非库存单位qty和退料方向。** 只观察，没有提交负数量草稿，不能据此声称负数能过账。 |

三个工单与正常提交的合成单据保留。退余8、额外WIP入10及超退9的试验仅在各自事务中观察后回滚；回滚后快照均回到领10/退2的基线，不把试验中的单号当永久凭证。

## 配置恢复与源码身份

JSON 的 `settings_restored=true`：System Settings及默认值均从临时 `6 / Commercial Rounding` 恢复到 `3 / Banker's Rounding`；制造设置恢复 `disable_capacity_planning=0`、backflush=`BOM`、`material_consumption=0`、超产0。三个本脚本新建的精度 Property Setter 已删除，`setter_absent=true`，各字段精度元数据均回到原来的 `null`。没有删除任何历史业务记录。Q05字段在U01前已经恢复；U01运行使用全局6位，未沿用Q05库存字段4位。

镜像内实际源码 Git blob（运行报告记录）：

| 文件 | Git blob SHA |
|---|---|
| `work_order.py` | `808777b02a1833279c5073fce26902d83eca60c6` |
| `work_order.js` | `fb71e640faec10a1404679fa22b9950f2dd1d4a6` |
| `stock_entry.py` | `fed639c03b7889d5c3897edcf5c9aaa59d3295de` |
| `stock_entry.js` | `8f07eb4ed22cbcb3980107dcdaa5741c77ecd701` |
| Frappe `property_setter.py` | `08fb76851d125229fb6c751b2f69b0ddd15899dd` |

两份核心Python业务文件blob与既有固定来源证据一致。其他三份本轮记录了实际镜像身份；不扩称全镜像源码审计。

## 复用判断与最小改造定位

| 需求 | 分类与依据 | 最小后续范围（未实施） |
|---|---|---|
| 库存位置、领退凭证、库存单位换算、明确实耗 | **配置后使用**：本例原生Stock Entry正常提交与同一库存账给出正确数量；制造设置可启用独立消耗 | 继续沿用Stock Entry、UOM conversion和Stock Ledger；在页面/查询中分别显示理论需求、领、退、净领、明确消耗及来源，不另建库存账。 |
| 剩余料自动生成 | **局部改造**：退单按转入累加、qty未统一到库存单位，已复现两类错误草稿 | 定位 `stock_entry.py:get_stock_entry_data / get_available_materials / add_transfered_raw_materials_in_items`，将有效领退耗按其方向及同一库存单位处理，并复用这一结果供原生退料生成。涉及批次/序列、替代料和拆解共用调用的影响须在R07限定并验证，不能把本次单料结果扩成全场景结论。 |
| 工单可退上限 | **局部改造**：本工单余8而有其他库存时退9接受 | 定位Stock Entry提交校验与已有工单关联；按当前有效领、退、耗及库存单位验证该工单/物料可退量，保留原生仓库负库存校验。请求并发下的一致性另由相应证据与R07绑定，不把本次串行探针当并发通过。 |
| 工单累计实耗 | **局部改造**：`WorkOrder.update_consumed_qty_for_required_items`当前SUM(detail.qty)，与库存账差1000倍 | 在既有汇总入口采用与库存账一致的库存单位数量，保留已生效单据过滤与引用；退料可用量查询同时统一单位。无需新建计算框架。 |
| 六位输入、四位最终需求 | **局部改造＋配置**：字段配置只使库存分支达到0.0002，WO仍0.00015 | 在既有BOM→Work Order权威需求计算/保存入口绑定最终舍入规则，并使后续库存、展示、导出、AI引用同一结果。全程十进制算法要求仍需沿既有入口评估；本次Property Setter试验没有证明仅用float字段配置即可满足。 |

本次证据足以把上述问题从“待确认风险”转为具体改造输入。**未验证**：UI实际操作与手机、普通角色权限、HTTP事务、请求重试/并发、批次/序列/替代料、成本精度、完整十进制链、导出/报表/AI一致性、客户部署与业务验收。本材料不提供无依据人天或节省比例；达到本补证范围即停止，不重跑已完成Q02/Q04，也未执行任何R07前的产品改造。
