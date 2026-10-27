> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B04 工时与指标本批记录

2026-10-27。上一批公开提交59e63446c9ad9f27bb49b9e91aa7ffcd3da8e693；ERPNext15.124.1上游4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e，Frappe15.124.0。现有维护分支/已发布12份源码一致，实际镜像22份清单一致。旧Q05、数量/损耗、中文BOM及B19不重复。

## 有限范围与结束条件

1. 在原隔离测试站让一个工单/任务/时间行fixture可保存重读；核原生起止差、跨天、倒序、客户端伪造分钟、未结束行及自动process_loss真实行为。保留原生结果，不把缺少休息字段的经过时长称为有效工时失败。
2. 对CASE-03 T01～T11及M01～M04、C13明确的效率/计时计件预计工资，绑定并验证一个内部确定性计算入口；不新建HTTP服务、配置表/页面、事实账或薪资模块。输入需明确包含服务端选定的规则列表及已授权来源的数量；计算结果不是正式报工/工资。
3. 若原生时间输入/派生分钟保存有真实缺陷，只修原JobCard.validate_time_logs；已有审批、权限、重叠检查和原始时间字段保留。有效工时不覆盖原生工作中心成本分钟，不能借B04悄悄改库存估价。
4. 配置读取/规则快照归B14，逐笔事实、良品不良适配/确认入口归B08/B09，页面/查询归B13/B16。B04内部计算验证不能冒称这些接入完成。其余数量对象/完整G1、G2、G3保留。
5. 本批以原生证据、R07入口绑定、限定红绿测试、必要修补、原卡更新及公开白名单提交推送/回读为结束，不增开循环测试批次。

## 开工判断

原生Job Card Time Log字段仅起止、员工、分钟、完成量及工序；validate_time_logs重算已结束行分钟，工作中心hour_rate用于运营成本；set_process_loss会用计划与已报差额推损耗。不能将缺字段视作默认0工时调整，也不能把差额自动当作人工不良。

先作原生探针；后续允许实现范围必须先在原R07绑定。本记录同时作为执行台账，不另建平行任务卡。技能执行计划的全量/清理步骤服从用户的有限重检和保留证据要求；已授权本地测试与白名单推送不再重复申请。


## 原生实测与实现判定

`native-probe.jsonl`6组真实insert/reload：闭合09–17重算480分钟、跨天240分钟、倒序拒绝，均可复用；开放行伪造999999分钟仍保存，缺开始仅有2099结束可把999999计入总数，需修补。`set_expected_and_actual_time`读取to_time存在行的time_in_mins，说明不能只修总和而放过行的派生值。良品输入8自动产生loss2，只证明差额推导，不能证明人工不良记录符合M01。

Ruling：B04仅完成计算层及明确原生分钟保存漏洞，不把B14配置存储或B08逐笔报工塞入本卡；否则会绕过尚未满足的原记录/权限并发门槛。计算结果暂不接正式报工，代价是本批不能宣称已可在网页录入休息/停工/加班。

优先复用本底座日期解析、对象保存、权限、重叠、测试fixture和数量校验；缺少本项目规则的部分做必要新增。下表只覆盖实际读到的文件，不将局部核查说成全仓不存在，也不将静态代码当运行通过。

## 五项目复用核查（固定版本，2026-10-27）

| 来源与已查位置 | 实际发现 | 本批使用方式 |
|---|---|---|
| ERPNext `4e0dce9`，Job Card/Time Log/Workstation/Downtime Entry；真实探针只运行Job Card保存链 | 原生已正确重算闭合行经过分钟、支持跨天及拒绝倒序/重叠；原生分钟用于作业成本，process_loss会自动推计划差额 | 直接复用原保存、时间差、权限与重叠检查，局部修两处分钟漏洞；有效工时另在同模块计算，不改成本语义 |
| t3rik `8a40bfe`，R03的ProFeedback字段核查，见[原核查](../../R03/fit-matrix.md) | 已查报工字段是日期、数量、人员；没有取得符合本项目休息/停工/加班规则的代码证据 | 沿用中文业务组织参考；本批没有复制其工时实现，不声称全仓无此能力 |
| OpenMES `b952915`，R04质量公式核查，见[原核查](../../R04/fit-matrix.md) | 已查公式以produced减scrap作分子；在本项目8良2不良输入口径下为75%，与M01要求80%不同 | 借鉴少输入方向；不直接套用不同数量含义的质量公式 |
| qcadoo `94fd649003287b73a46e3ad1340eb3b4ddbb5f30`，[StaffTimeCalculator.java](https://github.com/qcadoo/mes/blob/94fd649003287b73a46e3ad1340eb3b4ddbb5f30/mes-plugins/mes-plugins-production-counting/src/main/java/com/qcadoo/mes/productionCounting/utils/StaffTimeCalculator.java)，blob `df7c86b4785d4e63d4048d503bcf322395de6f68` | `countTotalLaborTime`按productionRecordId汇总staffWorkTime.LABOR_TIME，依赖其Entity/DataDefinition；该文件未实现本项目时段交集规则 | 参考“工时挂到生产记录再汇总”；当前底座已有时间行，不引入第二套人员/事实模型；未运行qcadoo |
| 快格云 `32c46b01c1881863f4ced2db9412a4a9a68b7902`，[reporting_service.py](https://github.com/kuaigeyun/kuaigeyun-mes/blob/32c46b01c1881863f4ced2db9412a4a9a68b7902/riveredge-backend/src/apps/kuaizhizao/services/reporting_service.py)，blob `bb00a861694631b0dcb01ee53aac32ee0b5acd54` | `_derive_work_hours_from_operation`可用标准时间×数量推导工时；工资读取缺配置/异常回退30；零工时效率返回0。与本项目实际有效工时、缺配置不猜工资、零分母“—”不同 | 参考报工、人员工时、预计工资的关联；不搬入这些不符已确认口径的分支、不复制外推/薪酬模块；未运行快格云 |

qcadoo与快格云本轮通过GitHub连接器读取上述固定SHA公开源码，仅作有限静态核查；未据此声称其余模块不可复用。没有新增第三方源码副本到产品/公开归档，保持ERPNext单底座及既有许可证。

## 修补、审查与公式归属

新增两个非白名单内部函数放在原`job_card.py`，没有新增服务、配置表或事实账。只有原`bom.py`数量校验新增明确`allow_zero`参数；默认正数约束仍在。产品相对上批仅改这两个控制器及原`test_job_card.py`，累计维护文件仍12个。

原生两处漏洞由`validate_time_logs`在每行重算前清零派生分钟、拒绝只有结束没有开始的输入修补。原始起止时间保留，闭合行继续用原生时间差；原生权限、审批及重叠保护保留。此处不等于报工原记录防修改已完成。

一次最终独立代码审查发现：12:59:59.500–14:00期间，高优先级12–13规则真实交集0.5秒，若先取整则错误选13–14后序规则，或被当无规则放宽加班上限。`review-red-tests.log`真实12项运行2.142秒，同一新增测试的两组子样例均失败；修补为先按真实交集选规则，再取并集完整秒。保留原始小数秒，不重复逐段舍入；没有另建时段框架。

| 结果 | 唯一入口/口径 | 输入来源与尚未完成的消费方 |
|---|---|---|
| 有效秒 | `calculate_report_time`：经过秒−休息交集并集秒−停工秒＋加班秒；规则按priority/name首条匹配，时间转上海，完整秒 | B14须供经权限读取的配置及规则快照；B08须供实际起止与人员确认的停工/加班。当前只验证显式输入，不读取客户端任意规则作事实 |
| 良品率、未清 | `calculate_report_metrics`：良/(良+不良)，返工不参与；max(0,计划−良−不良) | B08明确良/不良事实，不能拿原生计划差额代替不良。返回Decimal及分子/分母，不存百分比 |
| 任务完成、领料比例 | 已完成任务数/任务总数；生效累计领料/需求 | B16按状态/权限取数；数量必须同库存单位，待审批不计。不能拿多物料异单位直接加总 |
| 实际效率、达标率 | (良+不良)/有效小时；实际效率/同单位标准效率 | C13已确认；零工时或标准效率时相应结果None，由页面显示“—” |
| 预计工资 | 计时＝有效小时×单价；计件＝良品×单价 | C13已确认；未配置返回None或缺必要上下文拒绝，不默认工资；金额返回Decimal，币种精度/持久化归B08；不做工资结算 |

以上统计函数只消费已授权、生效事实；它们不是HTTP授权入口，当前没有写入生产/库存/工资记录。B04计算层通过不代表B08/B14/B16的配置、中文页面、确认保存或来源过滤已通过。

## 最终执行结果与复现

环境：B01隔离`xgd-test.localhost`，ERPNext15.124.1/Frappe15.124.0，上海时区，原生Workflow未激活；本批用原fixture创建的工单/任务在测试事务内回滚。没有装入Payment Gateway或全量初始化依赖，没有修改原始客户/Downloads资料。

最终累计补丁SHA256：`fc68d4af7ab3c74ed84ca898bffebe36b24c5c66041b272ec851e241754214e3`。源清单22项与实际容器逐项一致；本批相对公开59e6344仅3个既有文件变化：bom.py、job_card.py及test_job_card.py。`git diff --check`及3文件Python语法检查通过，依据[收口核对](closeout-check.json)。

| 实际运行 | 结果与含义 |
|---|---|
| 原生探针6组 | 正常闭合/跨日/倒序可复用；开放行及缺开始分钟两处失败保留；原生差额不良不作为人工事实 |
| 初次限定测试11项，1.691秒 | 8失败/1错误；错误是原实现缺`allow_zero`新参数，不是fixture初始化失败 |
| 初修11项，1.892秒 | OK；随后一次审查新增亚秒交集反例，不将此轮作为最终结果 |
| 审查红色12项，2.142秒 | 同一测试两组子样例失败；选错后序规则与把真实匹配当无规则均复现 |
| 最终12项，1.854秒 | OK；含原生保存/重读4项，CASE-03时间/规则4项，指标/非法输入/共享数量4项。没有顺序调用冒充HTTP或并发 |
| 测试前后11张业务表 | 条数与内容哈希一致，原测试数据未改，Workflow仍0 |

具体时间期望：T01=25200有效秒；T02跨日=7200；T03停工超7小时拒绝；T04全休息=0；T06=23400；T07加班超3600秒拒绝；T08倒序拒绝；T09不采信客户端派生时间；T10无匹配休息0/加班上限3600；T11重叠休息并集5400。指标：M01良8/不良2=80%，未清0；M02返工3不影响80%；M03/M04零分母None；2有效小时按10元/小时=20，按良品8×10元/件=80，实际效率5件/小时、标准10时达标50%。这些是合成样例，不是工厂产能/工资事实。

复现命令（工作目录为项目根；凭据沿B01本地环境提供，不公开）：

```sh
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b04-time-source-manifest.json
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.job_card.test_job_card --case TestProductionTimeMetrics --skip-test-records --skip-before-tests
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/b19_prepare.py
```

最后一条无`--prepare`，只读核对11张表，不创建元数据。原生探针为`.development/checks/b04_time_probe.py`；红色源码/运行清单、实际输出日志在本目录保留。公开版仅输出定义、脱敏结论和哈希，不上传运行单据、原始日志或凭据。

## 收口与下一步

本批测试结束，不重复Q05、B19、已验数量或中文BOM；18086/18088现有网页未替换，本批新源码验证范围是隔离Bench，不能称为网页已上线。内部新增函数未白名单化，没有新增权限绕过接口；确认入口未来仍必须检查权限、当前状态及重复请求。

原TODO、B04/B08/B14/B16及C13已更新。下一步先在原R07绑定B14最小规则配置、授权读取与历史快照，以及B08真实报工字段/确认衔接，消费同一计算入口。B04其他数量保存边界、G1/G2/G3、手机/客户验收均保留。公开白名单推送及远程回读的实际SHA/manifest另存`evidence/发布/B04-time-metrics-2026-10-27-remote.json`；本记录不预写推送成功。
