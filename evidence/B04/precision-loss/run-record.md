> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B04 六位数量链与材料损耗

2026-10-27。本批从未完成处续接，不重跑已完成 Q05，不依赖 B19 整卡。

## 执行范围与有限结束条件

1. 核对当前维护源码与容器，沿用隔离站点 `xgd-test.localhost`，原生 fixture 及事务回滚；不启用审批，不改旧中文演示站点。
2. 固定三组验证：六位输入及库存保存、两层 BOM 展开及最终需求、Q03 材料损耗来源。记录输入、数据库文本值、Python 类型、原生结果与十进制参考值。参考计算仅为测试判据，不加入产品计算链。
3. 先落真实输出，再决定局部修补。若需要全局 Frappe 数字转换、数据库类型或库存估价改造，记录具体失败和最小决策，停止该部分；不能以配置小数位宣称全程 Decimal。
4. 本批以三组结果、能在原允许边界解决的修补及验证、原任务卡更新和公开归档回读为结束条件。不重复 Q05、不扩大到工时、报工原记录、完整并发、其他工单类型。

## 源码和测试入口绑定

- 基线：ERPNext 15.124.1 `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，Frappe 15.124.0；当前累计补丁 `a0e334eee289144d99f35c4907e426227cecc5879e9a99cfa03f58790e0899dd`。当前 14 文件已与运行镜像核对；BOM/数据库转换源码将另记录哈希。
- 复用 `TestWorkOrderRequiredQuantity.make_quantity_order`、原生 `make_item/make_bom`、Work Order 的 `set_required_items` 和 Stock Entry 的 `insert/submit`；新增探针 `.development/checks/b04_precision_probe.py` 只运行本批样例，不收集旧 Q05。
- 核查 `BOM.update_stock_qty/get_child_exploded_items/add_exploded_items`、共享 `get_bom_items_as_dict`、`StockEntry.set_transfer_qty`、Frappe `BaseDocument` 和 MariaDB decimal 解码；只读后两者，不改 Frappe。
- Q03 的材料损耗须来源于 BOM；原生 `process_loss_percentage` 是成品损耗。新增字段/公式之前，先记录原生是否可表达及与库存单位的关系，另补原 R07 的具体范围。
- 基线数据 `data-before.json` 为本地原始记录，不公开。每次事务结束回滚并核对原业务表；原始输出同样仅留本地，公开经过筛选的判据及数值汇总。

## 实际过程、失败和修补

下列均为2026-10-27本机隔离运行，普通业务通过原生BOM/Work Order/Stock Entry入口；测试使用Administrator，不能代替岗位HTTP或客户验收。所有原日志仅本地保留，不以最终结果覆盖失败。

| 阶段／本地日志 | 事实与结论 |
|---|---|
| `native-probe.log` | 第一次探针写Singles未同步默认值，实际仍3位；多层fixture把字符串直接交给原生Python helper触发TypeError。属于样例准备问题，未作为“六位配置失败”。 |
| `native-default.log` | 改成原生数字输入后，默认3位库存0.123456→0.123；多层中间量0.000013916611保存为0.000013917，最终13.9170；损耗fixture用整数单位成品导致0.2成品损耗被原生校验拒绝。保留原保护，换用分数单位样例。 |
| `native-six.log` | 原生System Settings.save临时6位后，库存0.123456保存/流水/余额一致；多层仍13.9170，不提前舍入参考13.9166；原生成品工序损耗10%得到损耗0.2，用料仍25，Q03要求27.5。三组已可运行，事务回滚。 |
| `config-test.json/config-dev.json`、`stock-configured.log` | 本地开发/测试站原生默认Float精度3→6并提交；测试站在新进程实际入库仍为0.123456，样例回滚。其他显式精度、Currency和原舍入配置不变；不是全程Decimal。 |
| `red-tests.log` | 原TestBOM模块新增6项，真实运行6失败/0错误，包含13.917≠13.9166、25≠27.5、5≠6.05、负损耗未拒绝、0.05≠0.055和新半值0.00035未统一舍入。未收集Q05。 |
| `fixed-tests.log` | 局部修补后5通过/1失败：成本fixture没有初始库存价格，原生单价0，不能期待成本1.1。补真实原料入库2元前置，没有更改成本期望去迁就结果。 |
| `final-tests.log` | 价格前置修正后，发现同一BOM对象的原生成本更新留下ignore_validate_update_after_submit标志，允许把已提交损耗10改20。保留失败，补新字段的持久化保护。 |
| `freeze-tests.log` | 当时6项通过4.637秒；仅是该版本的阶段结果。 |
| `review-red-tests.log` | 一次独立审查提出两项后，实测2失败：交易单位先舍入再换算入库0.001235≠库存权威0.0012；更新成本夹带损耗修改使数据库20≠原10。 |
| `review-fixed-tests.log` | 统一库存单位舍入后换算、成本写入共用冻结检查，8项通过8.669秒。 |
| `delivery-tests.log` | 按原卡补齐Q03实际工单/领料/库存核对，产品补丁不再变化；最终同一类8项通过6.304秒。不把多轮通过数相加。 |

## 用户决定与最小实现

用户先要求白话说明，随后明确“按照你的建议，使用第一种”：保留ERPNext内部类型，只在已绑定数量链做精确十进制计算与一致性验收，准确性不降低。决策已写回`docs/决策与范围.md`和原R07；不是自动放宽要求。

- 复用`bom.py:BOMTree`，读取原BOM行的数据库文本数量、基数、换算和损耗，用Decimal遍历。原展开缓存仍存在，不再拿其已舍入数量当最终需求的计算源。
- 复用`get_bom_items_as_dict`的权限、物料、仓库、单位及废料查询。原料按库存单位汇总后统一四位HALF_UP，再按需要换算交易单位，最后返回原生数值类型；删除原WorkOrder独有的舍入三行，没有平行计算服务/账本。
- BOM Item只新增中文“材料损耗率（%）”一处，默认0。原始qty与stock_qty换算关系保留；每层损耗计一次，BOM成本显示沿原计算包含损耗。负数/非有限/非法输入拒绝；普通save及原生成本直接写入共用已提交依据保护。
- 此次产品/测试增量只涉及原`bom.py`、`bom_item.json`、`test_bom.py`及WorkOrder上述三行。其他B19/B02/B10既有改动保留。未改Frappe、库存估价、数据库现有数字类型或财务。
- 元数据仅在`xgd-test.localhost`用原生`reload-doc manufacturing doctype bom_item`导入。开发站只改了默认精度；开发/18088专用HTTP站未迁新字段，未重启其网页，不宣称这些页面已运行本批功能。下次运行新源码前须先对目标本地站导入字段；客户部署另验。

## 最终验收及版本

最终8项覆盖：多层原始用量13.9166→工单→实际领料→库存余额；Q03含10%材料损耗27.5→同一链；两层损耗6.05与直接子件22；库存/交易单位换算一次；负数、NaN、Infinity、非法文本拒绝；新半值0.000035×10→0.0004及废料0.2不变；不整齐单位1.234567×0.001最终0.0012并实际过账；正常成本更新保留、夹带损耗更新拒绝且数据库仍10。

最终累计补丁`ac2baec0af1bc8d046d39fb349ce21c10faad8a018f4cb0adf745c2aeb4ff5fe`，基线提交不变；完整补丁`combined-implementation.patch`，21文件清单`source-delivery-manifest.json`，运行回读`source-delivery-runtime.json`。此前各清单按各自批次保留，不用新SHA覆盖旧结果。

```sh
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json run --rm --no-deps -T bench bench --site xgd-test.localhost reload-doc manufacturing doctype bom_item
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.bom.test_bom --case TestBOMRequiredQuantity --skip-test-records --skip-before-tests
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b04-precision-delivery-source-manifest.json
```

## 必要防护、审查与停止点

原生权限、提交/库存过账、负库存与单位校验保留。10张原业务表整表哈希未变；Version增加1条原生“Float精度3→6”配置审计，移除这一条后的34条原审计哈希与批前一致，见本地`config-audit.json`及公开摘要；这不是对所有数据库表的完整审计。测试样例回滚，原始单据/日志/凭据不公开。

独立审查只有一次，2项Important已各留红绿证据并修补。Minor：原`bom.js`未保存时的材料成本预览仍按旧公式，服务器保存值已含损耗；浏览器表现未实测。按既定边界留给原B13页面联调，不顺手改JS。审查未判断的完整G1、报工/G2、并发/G3、未迁站点/客户/手机、旧B19/B02/B10及远程保存分别保留原范围；没有据此推定通过。

Ruling：不扩大成全局Decimal、BOM结构保护整卡或网页重写；本批实际数量/损耗样例及修补完成后收口。G1还需原卡的输入/保存边界及未覆盖范围核对，B04工时/其他指标另绑定，G2/G3未变。完整BOM历史结构保护归B07，不能仅凭新损耗字段冻结声称整张BOM不可被其他入口改变。本批接下来只做文档一致性、公开白名单提交/推送及远程manifest回读，不再启动业务复测。
