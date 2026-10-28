> 公开归档副本（2026-10-28）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B08 单价与效率续接记录（2026-10-28）

**做什么：**沿原B08剩余项核对单价来源、预计工资和标准效率展示，先补足R07具体来源契约，再最小接入原计算/确认/快照/中文页面。

**不做什么：**不重跑已验且未变化的权限/时段/三笔/防重，不做工资结算、不采用工作站成本代替工资，不重建计算或权限，不关闭现场、G1/G2/G3、Z01，不恢复后台周期。

**怎样算通过：**来源/单位/权限/生效时点明确，服务器预览与确认一致，旧笔依据保持，相关正常和失败输入有实际证据，中文PC重开能核对；仍只关闭对应子项。

## 实际基线与工具核查

- 公开仓库main最新`35d63323659089eb9142cd8a7046ae1ec64bfb01`，实际fetch后HEAD...origin/main为0/0，发布工作区干净。维护副本24份累计源码及补丁与该版本逐一匹配；保留既有改动与数据。见[基线](baseline.json)。
- OpenSpec1.15.0、Playwright CLI0.1.22可用；根config、6个OpenSpec技能和Playwright项目技能存在，无安装/升级/重复初始化。Superpowers沿已读执行、测试与审查方法，未另建计划。
- OpenSpec原change为`b08-followup-20261028`；CLI仍为引用模式0任务/apply blocked（不解析原卡外链），不是新业务阻断或完成证明。原卡是执行权威，未归档。
- 原Docker数据库/Redis、`xgd-b08-check`、`xgd-b08-ui`实际运行中，复用，不清库或重建。

## 本轮发现与实际缺口探针

只读核对原B03/B08、C13/C15、CASE-03、R07及当前字段，确定公式已定、来源未完整绑定。细节和可审阅方案直接追加[原R07](../../R07/time-config-binding.md#2026-10-28-b08-单价与效率续接来源待确认)，没有复制任务清单。

使用既有专用合成站普通操作工，以真实HTTP仅调用一次`preview_production_report_time`，输入09:00–11:00；不调用confirm，不改配置。响应200，有效7200秒，但没有预计工资、标准/实际效率、达标率及工资来源；调用前后原fixture业务状态完全一致。脱敏输出见探针（仅本地保留；见 publication/evidence-index.json）。这是现有“仅工时预览”的运行缺口观察，不是新字段契约测试通过，也不是对旧权限/规则验证的重跑。

开工时曾向用户发出来源选择，当时尚未修改产品代码。用户随后明确选择“按工单工序填写并随审批冻结（推荐）”；以下为该确认后的实际实施和验证。原生作业成本不作为工资来源，上一包证据仍按原版本保留。

## 实现与来源

复用ERPNext v15.124.1/Frappe v15.124.0，源码基线`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`。原卡、C13/C16与[R07](../../R07/time-config-binding.md)是需求及允许改动范围；沿原OpenSpec引用式变更，不另立计划。

- 工单工序维护计时/计件、工资单价、标准效率；草稿或退回时可经父工单保存，送审后随审批冻结。币种取公司默认币种并一并冻结。缺配置显示“未配置”，明确0与缺失不同，价格不套用工作站成本。
- 原`calculate_report_metrics`仍为唯一计算入口：计时按有效工时，计件只按良品，实际效率按良品+不良品；无关计划/领料/任务指标未提供时不编造0。
- 服务器提供预览并在确认时重新计算，预览指纹包含来源；每笔Job Card保存来源与金额，金额用当次原生币种精度及Decimal四舍五入。旧记录不回填当前单价；更正沿原来源重算并保留原笔。当前币种/精度变化不会改写已保存金额。
- 中文页面显示单价来源、预计工资、标准/实际效率与达标率；数量变化重新请求预览，失败或较旧响应不留下可用旧指纹。预计工资不是工资结算。
- 审查发现直接保存Work Order Operation子行可绕过父工单验证。先记录失败，再在已补充R07绑定的原子行控制器阻止直接插入/修改计价字段及相关关联；合法父工单保存仍走原验证。该限定修补不替代完整G2审计。

累计交付25份源码（17份上游派生、8份既有新增），本轮相对公开基线修改9份。最终补丁SHA256为`ddc6efaf432e7fa1c0e2428d908b29a4e7789de6184646bdadd2357ef9794ad5`。见[完整源码清单](source-manifest.json)、[累计补丁](implementation.patch)、[本轮增量](metrics-only.patch)。构建成功；测试容器、Web容器及新构建镜像的33份指定文件哈希均匹配，见[runtime](runtime-final-source.json)、[web](web-final-source.json)、[built](built-source.json)。这是指定源码核对，不是全镜像审计。

## 先失败再修补：实际执行

最小fixture沿原独立测试站和审批入口，未重装依赖。下表保留每批结果，不能相加成一次全量通过。

| 证据 | 实际结果及解释 |
|---|---|
| `server-first.log` | 新接口契约1项10.390秒ERROR：旧接口不接受good_quantity；fixture已实际运行、回滚 |
| `ui-first.log` | 原页面6项新展示/刷新契约失败 |
| `server-fixed-first.log` | 7方法69.050秒，5方法通过、2方法因复制样例保留docstatus=1失败；unittest原始errors=7（含6个子用例），不是7个独立方法失败 |
| `server-fixed-second.log` | 只修fixture并续接相关/新增范围，4项38.290秒OK |
| `child-first.log` / `child-both-first.log` | 直接子行保存反例先后1失败、3失败；负数/送审后改价实际未被阻止，事务回滚 |
| `child-fixed.log` | 最小子行保护后，3项28.415秒OK（子行拒绝、父工单合法/冻结、计时确认历史） |
| `child-entry-boundaries.log` | 同一方法新增插入、改关联、清空计价边界，1项11.041秒OK；不计为新方法 |
| `settings-history.log` | 新增当前公司币种/精度变化历史保护，1项17.173秒OK；受控修改后回滚并清默认值缓存，原设置核对一致 |
| `affected-regression.log` | 因计算入口/预览发生变化，原计算3项、旧预览1项、范围结果查询1项，共5项18.687秒OK |
| `ui-final.log` / `ui-regression.log` | 新UI契约6/6、原刷新失败回归1项通过；JS语法及产品git diff --check通过 |

本轮10个新增测试方法在上述多批中最终各有通过证据；没有一次“10项全套”运行，也未重跑旧B08权限组合/停启/三笔/并发整组。`ui-intermediate.log`保留测试正则把50.0000误判成工资0.00的失败，收窄金额断言后通过；`ui-final-check.log`和`ui-regression-check.log`是一次多余重复，未增加覆盖或计数。

四舍五入样例在受控数据库注入0.005价格后核对金额0.01；它不是允许审批后改价的操作证据。设置变化测试同样是隔离事务注入，不是公司配置页面验收。测试确认旧单价快照、缺失/0、负数/非有限/过精度、计件更正80→60且原笔80保留、旧指纹拒绝及越权无事实。函数层伪造参数被拒绝不等于已经验证真实HTTP未知参数处理。

各批源码以当时捕获的manifest为准：`runtime-source.json`对应4项续接及5项回归，`tests-first-source.json`对应首次缺参失败；未捕获完整中间补丁摘要的批次明确不补写最终摘要，最终manifest也不冒充每一批当时源码。最终产品Job Card哈希与后续成功批次相同；子行控制器修补后的哈希单列于清单。

主要实际命令（在项目根目录，按各次仅选相关方法执行，不要求重跑）：

```sh
docker exec xgd-b08-check env/bin/python /b01/b08_metrics_tests.py <上述对应方法名>
node .development/checks/b08_metrics_ui_test.mjs
node .development/checks/b08_ui_refresh_test.mjs
docker exec xgd-b08-check env/bin/python /b01/check_source.py /b01/b08-metrics-source-manifest.json
docker exec xgd-b08-ui env/bin/python /b01/check_source.py /b01/b08-metrics-source-manifest.json
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b08-metrics-source-manifest.json
```

原始命令/输出留本地；精确方法名、计数及日志哈希见[结果摘要](acceptance-summary.json)。独立代码审查发现的子行P1已按反例修复，定向复审无新阻断；复审没有替代测试。

## 真实浏览器与独立HTTP

复用Playwright CLI及本机18090专用中文合成站，未启用客户审批或外部通知。新增4张合成工单、1个窄角色配置账号，既有账号/单据保留。两张工单经原生审批后用于报工，另外两张保留草稿。样例日期是预设合成输入，不能称客户生产事实。

- 普通报工操作员：09–11时、良8不良2，计时单价10、标准10，预览20.00 CNY、实际效率5、达标50%；点击确认、重开依据均一致（`ui-hourly-preview`、`ui-hourly-saved`日志/截图）。
- 计件：同数量预览80.00；将良品改6后预览60.00及40%，恢复8后80.00/50%；点击确认、重开80.00。见`ui-piece.log`和`ui-piece-saved-stable.png`。这一步真实页面新增两笔生效报工。
- 旧报工重开显示“历史未记录”，未套当前配置，见`ui-legacy.log`。
- 独立配置会话经原生工序行界面填写计时/单价10/标准10，保存再重开值和CNY一致。初次保存被行编辑浮层遮挡，Esc关闭后成功；首次下拉英文，执行原生`bench --site xgd-b08-http.localhost clear-cache`后实际刷新为“计时/计件”。没有为缓存问题改产品代码。见[配置UI摘要](config-ui.json)。
- 同一配置会话cookie及合法CSRF单独执行HTTP子行改价为-1：403/PermissionError，命中具体计价保护，重读值及父子修改时间未变。见[HTTP摘要](config-http.json)。它单独标为HTTP，不冒充页面动作。

原生日期格式仍为DD-MM-YYYY；开发站socket.io轮询404存在，但本轮同步保存、预览、确认、重开实际通过。实时通知、手机/弱网/PDA/触屏、现场人工10秒均未验证。自动化已知道输入，不作人工操作效率结论。

## 数据保留与收口边界

- 源测试站11张旧业务表与上一包基线的数量/哈希一致，剔除范围仅为已记录的新schema列，见`source-retention.json`。测试runner同时核对规则/时段/员工/User Permission在每批回滚后不变；未启用源测试站Work Order Workflow。
- 专用UI站对开工前全部11表逐行、按捕获列进行哈希比较：无丢失、无改写；库存3表无新增。新增工单4、Job Card8、工时行2及对应审批/版本/评论均保留。见[保留摘要](ui-retention-summary.json)。该范围不是全数据库、用户表或客户数据审计。
- 源码/任务卡/可公开证据按白名单同步；原始日志、截图、实际运行单据、凭据不发布。一次本地排查误打印合成账号口令到工具输出，未写入公开文档；发布扫描包括该已知值，不据此宣称全局凭据安全审计。
- 只关闭本轮B08价格来源/预计工资/效率的已绑定子项；B08/B09整卡、完整G1/G2/G3、现场验收、Z01/CASE-11干净环境启动/配置/备份恢复/独立接手仍未完成。OpenSpec不归档，无客户部署或远程CI通过结论。后台周期未恢复。

公开产品提交[`d90f568b6894f44c4adee5310a1d4fe4f5115ec4`](https://github.com/jinjin1205/work-order-approval/commit/d90f568b6894f44c4adee5310a1d4fe4f5115ec4)已推送；重新克隆main核对311个跟踪文件、310份内容哈希和25份源码，缺失/多余/哈希不一致均0，见[远程回执](../../发布/2026-10-28-d90f568-remote.json)。发布前白名单/已知凭据/原始数据排除检查通过，产品diff及非补丁文档空白检查通过。OpenSpec最终普通validate为valid=true，仍保留引用模式0任务警告；未归档。此后仅回填本包状态，最终文档SHA及精确提交CI查询在最终回复/本地回执中报告，不循环提交。
