> 公开归档副本（2026-10-28）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B08 续接包运行记录（2026-10-28）

## 开工范围与通过条件

**做什么：**按[原 B08 下一包详细执行卡](../../../docs/任务卡/02-生产与物料闭环.md#2026-10-28-下一包详细执行卡沿原编号尚未运行)，补 B08-02 权限组合、B08-05 停用/重启快照及 B08-07 普通岗位中文入口计量；真实失败才在原绑定文件内最小修补。

**不做什么：**不重跑未变化三笔/同键防重及 B04/B14/B19 已验依赖，不放开整单 write、不改 Frappe 框架，不扩工资结算、新 AI、库存逆向平台或客户部署；不恢复后台周期。

**怎样算通过：**仅以原卡新增样例、共同通过条件和停止条件判定；保留正常与关键失败的版本、输入、实际命令/页面动作、输出和限制。拒绝写入须零部分保存，成功须普通岗位完成并重读。页面、受控测试和人工现场分别报告；10 秒未达或缺验收人仍标未验证/未达，不能自动降低标准。全部独立自动化项已有明确结果即停止本包；B08/B09 整卡、G1/G2/G3、Z01/CASE-11 不随本包关闭。

需求、方案和任务权威仅为原卡与 [R07 事实/并发](../../R07/report-concurrency.md)、[权限](../../R07/permissions.md)、[时段](../../R07/time-config-binding.md)；本记录保存证据，不另设任务清单。

## 开工基线与复用

- 主执行代理本轮已核对交付基线 `afe5eb8` 与 `.development/repos/erpnext` 的 `codex/xgd-maintenance` 工作副本：24 个累计修改文件完全一致；累计补丁保留为本目录 `baseline.patch`。这些是已有维护内容，不视为本包新增或丢失改动。
- 继续原维护 checkout，不另建 worktree：新工作树不会自动包含这 24 个累计修改，现副本已核对且为原维护路径；保留原文件与运行数据，不 reset、不向 Frappe 上游推送。
- 主执行代理已启动既有 Docker 隔离容器并核对 32 项运行源码清单一致。以上为开工时的环境/源码核查，原始输出留本次会话；并非新业务测试通过。正式执行新测试前须核对包含本次测试修改的实际运行源码。
- 本包开工时新业务测试尚未执行。旧结果仍按[2026-10-27 批次](../implementation/run-record.md)和其源码版本引用，不追加为今日通过。

## OpenSpec 最小接入（实际执行）

本轮复用 OpenSpec 1.15.0、Playwright CLI 0.1.22 和已有 Superpowers；根配置、6 个 OpenSpec 项目技能及 Playwright CLI 项目技能已由主执行代理补齐。此次记录仅使用 OpenSpec CLI，未运行浏览器或业务测试。

使用[change `b08-followup-20261028`](../../../openspec/changes/b08-followup-20261028/proposal.md)和默认 `spec-driven`。没有需求变更，`.openspec.yaml` 设 `skip_specs: true`，不重复规格；`tasks.md` 只链接原卡。

| 实际命令 | 实际结果与限制 |
|---|---|
| `openspec schemas`；`openspec list --json`；`openspec context --json`；`openspec list --specs --json` | 仅默认 `spec-driven`；root 为本项目；创建前 changes/specs 均空 |
| `openspec new change b08-followup-20261028 --json` | 成功创建 change 与元数据 |
| `openspec instructions proposal/design/tasks --change b08-followup-20261028 --json`（按各 artifact 分别执行） | 读取模板、依赖和输出路径，再写 proposal/design/tasks 引用文件 |
| `openspec status --change b08-followup-20261028 --json` | `isPlanningComplete: true`；proposal/design/tasks 为 done，specs 为 skipped；只证明规划文件存在 |
| `openspec instructions apply --change b08-followup-20261028 --json` | `state: blocked`、0 个 tasks：默认解析器不读取外部链接中的复选框，不能直接跟踪原卡 |
| `openspec validate b08-followup-20261028 --json` | `valid: true`，INFO 接受 skip_specs，WARNING 0 个可解析任务；此警告保留，不为消警告复制原卡 |

本项目按用户要求采用引用模式，原卡是执行进度权威。工具的规划完成/0 任务不代表本包完成，默认 archive 也不能据此判断原卡未完成项；本 change 未归档。

## 新测试与页面证据

按[原 R07 本包命令绑定](../../R07/report-concurrency.md#2026-10-28-b08-续接包命令绑定)执行。主执行代理已为原 `TestProductionReportConfirmation` fixture 增加审批前 scope 参数，并在原测试文件实现 `TestProductionReportFollowup` 的 6 项权限方法和 1 项停用/重启快照方法；方法名和完整命令在 R07 记录，不另建验收清单。

实际 runner `.development/checks/b08_followup_tests.py` 固定隔离站 `xgd-test.localhost`，映射为容器中的 `/b01/b08_followup_tests.py`。本包 tests-first-source-manifest.json（仅本地保留；见 publication/evidence-index.json） 与 data-before.json（仅本地保留；见 publication/evidence-index.json）已保存；首次 6 项权限测试通过 `docker exec xgd-b08-check env/bin/python /b01/b08_followup_tests.py <6个已绑定方法名>` 发起，输出至 permissions-first.log（仅本地保留；见 publication/evidence-index.json）。本节登记时尚未判读首次测试结果，后续记录实际退出码/输出；第 7 项停用规则测试待权限阶段后执行，中文页面和人工现场仍未验证。此处不是通过声明，也不重放已消耗的旧 HTTP fixture。

## B08-02 首轮与最小修补

首轮6项69.461秒，3项通过/3项ERROR（permissions-first.log）。DEPT同部门、员工状态/无绑定/异公司、原生重复有效Employee约束通过。两项ALL测试因第三工序前置未完成，被原生OperationSequenceError拒绝；这是fixture顺序问题，不能当权限失败。改为批准前配置首工序ALL，并把PERSON他人拒绝与ALL他人成功分为两项，未放松生产顺序。

另一项真实失败：Employee部门变更后，新DEPT报工正确拒绝，但本人仍有Job Card及父工单当前read时，get_production_report_result错误复用写scope而拒绝历史结果。依据permissions.md关于写scope/历史可见分离，仅将该结果接口的_report_task替为_report_context(history=True)。保留本人请求、生产报工角色、显式公司/班组、父单和Job Card read、当前有效Employee检查；不授整单write。复测尚在执行，不预报通过。

B08-02修后4项43.964秒OK；另将员工状态样例补为“先有历史再变化”，该项及原跨用户结果读取回归2项21.945秒OK。没有重跑未变三笔和同键防重。

B08-05首轮11.448秒在fixture前置失败：原测试站已有全工序规则PTR-00001，故不得假定空配置。按原卡在测试回滚事务中通过原生save暂时停用这些候选，再测新规则停用/重启；没有删除/永久修改旧配置。随后1项10.495秒OK：25200→停用无匹配28800→重启25200，停用/重启两种陈旧指纹均拒绝且无部分保存，新记录版本与指纹可核，两个旧快照字节保持。runner确认旧规则/时段/Employee/User Permission四表逐行不变。

## 实际HTTP与中文PC

新增独立合成用户及工单，未重放旧HTTP批。同一API token的13次真实HTTP均符合预期：DEPT同部门预览/确认200；员工换部门后旧页面预览/新确认403，本人旧结果200；撤最后公司或班组授权后三个接口403；恢复后旧结果200。三组拒绝前后卡/行/工单/库存计数状态哈希一致，最终仅1笔良1。只修改本轮新用户的配置，finally恢复，旧账号/样例不变。命令 `python3 .development/checks/b08_followup_http.py`，结果见[HTTP摘要](http-results.json)；不代表全HTTP、完整并发或提交中途故障通过。

Playwright CLI 0.1.22 / Chrome 156.0.8078.48，普通生产报工角色在原B08专用站完成新增工单：剩余10/不良0；开始时刻来自本次合成样例准备时实际时钟，核对后保留页面结束默认值。从已就绪列表进入目标、打开报工、输入开始时间、预览并确认，共4次指针点击/1个手输字段。总时长3.211秒；输入与预览1.210秒；就绪至成功1.134秒（含截图0.291秒）；确认动作至成功0.843秒。一次run-code内执行，模型/工具间等待0，字符间40ms。自动化预先知道目标及输入，不含人工阅读/思考，不能作为现场人员10秒验收。旧18.015秒样例原样保留，两个样例输入和工具不同，不推算性能提升比例。

实际重开弹窗：累计良10/不良0/剩余0、计划10。从历史链接打开Job Card并查看确认依据，显示有效169秒、未匹配规则、B04-time-v1/Asia/Shanghai，没有按当前配置重算。原始动作、截图及业务时间值仅本地保留。本包未改UI或接入计时，没有伪造默认开始时间；脚本单击确认仅用于本次已授权合成验收，产品仍由人确认。

限制：专用开发Web未启动socket.io服务，浏览器记录8条socket.io 404/连接错误；本轮同步报工/重开成功，实时通知不算已验。日期控件沿保留站点DD-MM-YYYY显示，本包未改全局配置，不能据此称完整中文/日期默认值交付通过。手机、人工现场、完整B08/B09、G1/G2/G3与Z01继续保留。

## 一次独立代码审查

只审相对afe5eb8的followup-only.patch，未把历史累计补丁当新代码。未发现新增Critical/Important/Minor。审查只读、未运行测试，不代替上述实际HTTP/页面结果。

未判范围及处理：真实token撤权随后由13次请求补证；既有历史列表仍按写scope筛选，本轮只修请求键找回，未改变列表；完整G1/G2/G3/Z01和最终公开保存另按原门槛处理。不扩大本包做列表重构，不再次审查循环。

## 版本、保留核对与发布边界

最终镜像按原Dockerfile构建成功（final-build.log），新镜像、原测试容器、专用网页分别核对32个源码文件一致（built-source/runtime-final-source/web-final-source）。网页计量时产品文件已更新；仅测试定义后补同步，不影响页面产品逻辑。一次旧清单预检查因仍指向原b08-source-manifest而失败（ui-source-precheck.log）；最终改用新清单核对通过，未将该旧清单失败当产品缺陷。

源测试站原11表前后哈希一致，Workflow仍0；B08专用合成站原11表所有旧行逐条未变，新增2张工单和各自报工/计划/审计保留，库存表无新增。它不是全库审计。规则测试另核四张规则/员工/授权表回滚后完整一致。

最终累计补丁/source-manifest归本轮；首轮和修后4项各有当时源码清单。2项历史回归的中间整补丁哈希未单独留档，公开回执明确null；所测产品job_card.py与最终哈希一致，最终仅增加规则测试fixture隔离，不伪称该批精确整补丁已捕获。历史14+3+1批次保持原哈希。

公开仅代码、测试定义、原卡/OpenSpec引用、脱敏方法/计数/状态/版本与哈希；本机登录、API密钥、数据库、样例单据、原始响应/日志/截图均保留本地。生成的工具技能在本机可用，交接沿初始化命令按需复用/补齐，不额外复制第三方插件实现。后台周期未恢复。

发布检查实际通过：白名单289文件、24份源码逐字一致，已知凭据/模式/原始运行JSON匹配均0，Python语法通过。首次把新增证据`.patch`当普通文件执行`git diff --cached --check`，其统一补丁上下文前缀触发空白告警；提交仍已生成。随后执行`git diff --check HEAD^ HEAD -- . ':!*.patch'`，实际源码与文档检查退出0，无产品改动用于消除此格式告警。

产品提交`d4d73f07c872fa05a1789618b534e6ab6ab44d3a`已推送至公开仓库main。`python3 .publication/verify_b08.py`实际重新克隆远端：远端ref与本地SHA一致，289个跟踪文件、288项内容哈希及manifest自身一致，24份源码与维护副本一致，缺失/多余/哈希不一致均0；见[回执](../../发布/2026-10-28-d4d73f0-remote.json)。本次仅回填原卡过程项、TODO/R07及此记录，另作最终文档提交；最终文档SHA与CI实查只在最终回复及本地回执，不反复回填，不称业务整卡或客户交付完成。
