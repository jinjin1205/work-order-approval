> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B04 数量输入/保存与中文 BOM 页面

2026-10-27，按最新原卡续接；上批公开提交`5a88c74521e5bcf89e8e6882df0ec2703d049092`，维护源码累计补丁`ac2baec0af1bc8d046d39fb349ce21c10faad8a018f4cb0adf745c2aeb4ff5fe`。不重复Q05、上批不变样例或B19，不重建环境。

## 本批范围与停止条件

1. 复用现有原生fixture，在`xgd-test.localhost`验证BOM父项基数、BOM Item原料用量、Work Order计划数量。三处分别核六位数字/数字文本、零、负数、非法文本、非有限数、布尔值、超六位与超过可准确保存范围的数值；逐例保存点回滚，记录真实拒绝类型或数据库文本/重读值。
2. 先保留原生结果，再在原控制器外部输入边界补必要校验。只处理这三种输入；不改全局Frappe数字控件/数据库类型、库存估价、交易单位换算、报工或完整并发。
3. 中文BOM页面复用原表单及原材料成本预览；在已有本地开发站导入BOM Item元数据并用当前源码启动本地网页。使用专用合成BOM与有限普通角色，核中文字段、六位输入、损耗改变后的预览、保存重读与中文错误。审批演示18088及客户站不变，不启用新审批。
4. 页面精度处理先按实际原生控件核验。原`ControlFloat.parse`会按配置舍入；不得只在保存后猜测用户原始输入。超过六位须明确拒绝或按显式说明的配置处理，不能把静默舍入写成通过。
5. 本批以限定边界及中文页面证据、必要修补/回归、原卡更新和公开白名单推送回读为结束。G1/G2/G3、完整B04/B13与客户验收仍保留，不扩展整页重写或通用校验框架。

## 原生入口绑定

- `bom.py:BOM.validate/validate_main_item/set_bom_material_details/validate_materials`：现有数量校验先核实；`before_validate`为候选早期边界，须早于原生flt/计算。`get_bom_items_as_dict`已有十进制计划量解析，复用正确部分。
- `work_order.py:WorkOrder.validate/validate_qty`：原生正数及整数单位校验保留；原生审批校验不改变。
- `bom.js:erpnext.bom.calculate_rm_cost/update_cost`及原BOM Item字段事件：已有成本预览不含材料损耗。只补该字段事件和同一原生预览函数，不另建计算服务；最终保存仍由原服务器控制器计算。
- `bom_item.json`与必要BOM数量字段说明：仅中文说明/精度呈现候选，不改现有数字存储类型。
- 测试仍放原`test_bom.py`，复用现有fixture；新探针`b04_input_probe.py`不收集旧Q05。页面测试留真实浏览器状态与服务端重读，不把JS模拟当页面验收。

以上为开工时绑定；实际实施和收口结果见下文，历史原生失败不覆盖。


## 原生结果与新增绑定

33组真实探针已完成：六位值可保存；7位值被接受；原料0/False被补为旧用量0.5；非法父项触发ZeroDivisionError、非有限原料触发MySQL ProgrammingError；大数123456789012.123456保存为123456789012.123460000。日志`native-inputs.jsonl`仅本地。用户已明确接受单次数量小于10亿且最多六位小数，三处须为正数；数字文本按验证后统一转为原生值，不让TypeError充当业务反馈。

允许在原`bom.py`新增一份简单输入校验，由BOM.before_validate与WorkOrder.before_validate复用，早于原生默认值/计算；现有WorkOrder已导入BOM模块，不新建模块或框架。同轮核算后需求超出原decimal(21,9)存储范围的拒绝入口，只加显式错误，不改字段类型。新测试类TestProductionQuantityInput验证这三处及派生需求溢出；先红后绿，其他已完成不变项不跑。


## 实施、审查与实际结果

- 运行ERPNext 15.124.1（上游`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`）、Frappe 15.124.0；复用已有ARM64 Docker、开发站18086和测试站。最终源码累计补丁`e56d3bb7914ef123ac13fe8d21fceb433a6ebfd7e5d844e19cfa74581a867e85`；测试容器及实际Web各22个清单文件相符，见`final-runtime.json`、`web-runtime.json`与`source-manifest.json`。未改Frappe、数据库数字类型或审批演示18088。
- 原3项新测试先执行：5.994秒，11个失败子项、12个错误子项；不是23个独立测试。原生fixture正常创建后才触发数量失败。局部修补首次3项通过2.462秒。
- `bom.py:validate_quantity_input`为三处唯一校验实现；BOM与WorkOrder的原生`before_validate`早于默认值/计算，数字文本经验证后转原生值。BOM成本直接保存及原材料查询的外部数量入口复用此校验；不新建服务、全局控件或重复账本。原权限、审批、整数单位检查保留。
- 派生需求先阻止明显存储溢出。最终静态审查给出具体反例：父项3、原料999999.999999、计划3000000.000003，四位舍入后达到1e12。真实类级测试4项中1项失败后，在舍入后的新值处补范围检查；最终4项通过2.698秒。早期与舍入后检查对应不同状态，避免异常和舍入后漏检。先前`--case`与`--test`组合触发原生runner KeyError，未计入业务测试结果；改回原可运行类级命令，失败日志保留。
- 原浏览器`.6 × 2 × (1+10%)`的未保存预览为1.20，期望1.32。只修改原`bom.js:calculate_rm_cost`及损耗字段事件，预览复用原金额精度；服务端保存仍是最终依据。父项与原料数量均用中文描述明确原生六位舍入。原料说明最初放setup未显示，实测后改为原BOM Item元数据description，不加控件封装。

## 中文PC实际操作与可复验步骤

入口`http://xgd-dev.localhost:18086`；本地专用账号为普通Manufacturing User，凭据只保存在`.development/private/b04-bom-ui/access.json`。复用原生角色并不等于实际工厂岗位/班组权限已验收。保留一个合成BOM草稿及独立原料入库用于真实估价；不使用客户数据。

1. 打开本轮中文BOM草稿，父项数量填2.123456；原料行点编辑，数量填0.623456、材料损耗率填20（单价2）。原页面预览金额1.50，与服务端保存及SQL重读一致。数据库数量为2.123456000、0.623456000，没有丢失输入六位。
2. 把父项改为1000000000再保存，出现“小于10亿”中文错误；改为-1，出现“大于零”中文错误。未生成额外BOM或库存事实；恢复合法值后保存/刷新。原生零必填控制也阻止保存；服务端零/False等拒绝由矩阵测试证明，不用页面必填代替服务器校验。
3. 原网页输入1.1234567，离开字段显示1.123457；此为原生控件舍入，已明示保存前核对。直接数量入口传超六位则ValidationError；**没有声称网页拒绝原始第七位**。本轮仅联调BOM，Work Order中文页面尚未做相同操作验收。
4. 本地AX/截图：`ui-red-preview.*`、`ui-native-rounding.txt`、`ui-green-preview.txt`、`ui-limit-error.*`、`ui-negative-error.txt`及最终截图。`ui-readback.json`为数据库复核；这些含合成编号的原始记录不上传。

## 命令、数据与结束条件

新测试固定使用：
```sh
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.bom.test_bom --case TestProductionQuantityInput --skip-test-records --skip-before-tests
```
源码核验复用`check_source.py /b01/b04-input-source-manifest.json`；Web复用同脚本并经stdin传同一manifest。开发站只按绑定`reload-doc manufacturing doctype bom_item`及clear-cache，随后运行新Web镜像。测试站11张原业务表前后hash一致。开发站基线6类核心表原本均为空，不虚称保留了历史客户单；本轮合成草稿、原料入库与正常审计保留，未删除数据。

本批4项及中文PC限定步骤完成，保存原卡/证据并按公开白名单提交、推送、远程克隆回读后结束。原Q05、既定不变数量/损耗样例、B19不重跑；仅因本批新增反例重跑受影响类。完整G1、逐笔报工/G2、完整并发/G3、手机/扫码/弱网及客户验收均保留。其他数量对象、派生数量和交易换算的完整范围未覆盖，不能把此处存储上限检查称作全部溢出已解决。
