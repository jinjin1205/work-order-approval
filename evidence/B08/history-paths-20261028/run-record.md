> 公开归档副本（2026-10-28）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B08-06/B09 原记录旁路续接（2026-10-28）

**做什么：**沿原卡和R07 `report-concurrency.md`第6/7节，补工序子行删除/改挂、取消态时间子行及通用删除路径的未覆盖证据，保留合法无事实草稿正例；实际失败才在原控制器最小修补。

**不做什么：**不重跑单价/效率、权限组合、停启、三笔及同键并发的未变通过项；不接未完整绑定的图片/报检/自定义字段或导航，不改Frappe、库存/计算、后台周期，不关闭整卡、现场、G1/G2/G3或Z01。

**怎样算通过：**新增路径有普通授权身份正例与历史拒绝、前后记录/关联一致、取消态历史仍保留；实际数据库与HTTP分开记录，通用批量200不能当成功删除。复用既有隔离fixture与站点；合成样例保留，公开白名单及远端回读按实证收口。

## 开工基线

公开HEAD与fetch后的origin/main均`cec110a566304fb49b1eab4e65dad9d42c1e188b`，分叉0/0、发布工作区干净。维护25份累计改动源码逐一与公开source-lock匹配；上游固定`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，ERPNext15.124.1/Frappe15.124.0。见[基线](baseline.json)。没有reset、清理、复制客户数据。

OpenSpec1.15.0、Playwright CLI0.1.22及项目技能/config可用，复用原`b08-followup-20261028`引用变更，未安装/升级/初始化。CLI仍0任务/apply blocked，为原卡引用模式限制；按用户要求原卡为执行权威，不另建清单、不归档。

原`TestProductionReportConfirmation.test_original_parent_and_child_protected`已覆盖submitted原卡save/cancel/delete和时间行save；`test_full_correction_retains_original_rule_and_fact`已覆盖更正后原卡直接删除。本轮不把这些改名重跑。新范围为尚缺的入口/状态/关联组合，不预报安全结论。

## 实际失败、根因与最小修补

反例均在原`xgd-test.localhost`使用新建、最终回滚的原审批/报工fixture。原角色/权限行修改仅限测试事务，没有扩大专用Web旧岗位权限；每批runner另核原规则、时段、员工、User Permission回滚一致。

1. `test_resource_operation_delete_keeps_reported_task`：普通发起人已实际具有子行delete权限，有一笔已生效报工、工序未配工资。直接调用原Resource DELETE处理函数，**删除成功**且工序/历史关联快照变化；1方法10.103秒、2个失败断言，见`first-test.log`及[first源码](first-source.json)/[实际运行](first-runtime-source.json)。不是因无delete权限导致的假拒绝。
2. `test_client_operation_reparent_keeps_reported_task`：同一普通发起人有旧/新工单权限和子行write/submit权限，调用真实`frappe.client.save`把有报工的原工序行改挂另一新草稿，**保存成功**；1方法8.935秒、2个失败断言，见`reparent-first.log`及[当时源码](reparent-first-source.json)/[运行核对](reparent-first-runtime.json)。两次均在fixture清理时实际回滚，未改旧验收单据。

根因由固定Frappe源码与反例共同定位：Job Card的`operation_id`为Data，原生Link删除检查不能保护任务引用；Resource DELETE直接进子行on_trash，不经过父工单保存。client.save也仅保存子行，提交后更新调用before_update_after_submit；原子行仅有before_validate计价保护。原生提交后字段检查不把parent当DocField检查，因此新父单权限不能证明旧任务可改挂。上述7份相关Frappe保存/删除/权限/事务源码与R07快照哈希一致，仅只读复用。

**最小产品修补仅原`work_order_operation.py`：**按持久化工序行`name`查询Job Card `docstatus>0`引用，包含已取消历史；已有历史则拒绝直接保存、提交后更新及删除，分别挂before_validate、before_update_after_submit、on_trash。查询不信任客户端提供的新parent。原父工单派生保存和审批冻结保持原入口，不增加权限豁免、不改价格/计算/库存或Frappe。无历史草稿继续按原权限和原生校验操作。

累计25份源码仍为17份上游派生、8份既有新增，本轮只改原工序控制器及原`test_job_card.py`两份。最终补丁SHA256为`e15fba0d7e7272c8a311c5f272476e76325a690a2ad1dc3dbfc021836effc3f2`；[源码清单](source-manifest.json)、[累计补丁](implementation.patch)、[相对cec110a增量](history-paths-only.patch)。无新字段或DocType，无需新reload-doc或依赖初始化。

## 实际受控测试与审查

新类`TestProductionReportHistoryPaths`只复用已有fixture/helper，不继承旧测试方法；独立runner为`.development/checks/b08_history_paths_tests.py`，仍限定隔离测试站。实际命令按以下方法分批执行：

```sh
docker exec xgd-b08-check env/bin/python /b01/b08_history_paths_tests.py test_resource_operation_delete_keeps_reported_task
docker exec xgd-b08-check env/bin/python /b01/b08_history_paths_tests.py test_client_operation_reparent_keeps_reported_task
# 此次默认类当时只有4方法；不是当前5方法全类复跑。
docker exec xgd-b08-check env/bin/python /b01/b08_history_paths_tests.py
docker exec xgd-b08-check env/bin/python /b01/b08_history_paths_tests.py test_unreported_draft_operations_remain_editable_and_deletable
docker exec xgd-b08-check env/bin/python /b01/b08_history_paths_tests.py test_cancelled_only_operation_reference_stays_protected
```

| 批次 | 实际结果 |
|---|---|
| 首次delete / reparent反例 | 上述各1方法、各2失败断言，保留原始失败 |
| 修后`fixed-tests.log` | 4方法36.400秒：两反例及取消态时间行3方法通过；无事实草稿正例1 ERROR |
| 草稿fixture定向修正`draft-fixed.log` | 1方法9.731秒OK；仅调整删除次序，不改产品 |
| 取消态唯一引用`cancelled-only.log` | 新增1方法10.351秒OK；仅跑新增状态组合 |

草稿ERROR原因：先删首行再删中间行，剩下sequence_id=3，触发原生“首行工序序号必须为1”。改为依次删除末尾第3/2行、保留首行，并定向复跑；这是fixture错误，不将它当产品问题或放宽顺序规则。正例同时通过直接子行save、Resource DELETE、client.delete经父保存，且剩余原首行可查。

取消态时间行通过正常confirm/correct生成原卡docstatus2；Resource DELETE命中原时间行历史保护，client.delete/改parent分别记录原生状态或既有控制器拒绝，前后原卡/时间行/关联/工单派生一致。“仅取消态工序引用”单独以**受控服务器上下文调用原生cancel**生成，断言同任务submitted卡为0、cancelled卡存在，再以普通发起人delete/reparent命中特定历史保护。该受控状态fixture不代表开放客户端独立取消动作；正常外部取消仍沿原限制。

本轮5个新增方法分别有通过证据，未把分批加总成一次5方法全类运行，也未重跑旧价格/权限/时段/防重测试。每批精确源码摘要和日志哈希见[结果摘要](acceptance-summary.json)及各批manifest；不是将所有批次倒填为最终源码。

一次独立定向代码审查未发现新增Critical/Important/Minor缺陷，指出的草稿正例和取消态唯一引用两处证据缺口已分别补齐；产品未因此再改。审查不等于HTTP、后台或整卡验收。

## 运行文件与原有数据

已复用原容器，仅复制本轮两份源文件并重启`xgd-b08-ui`使Python控制器生效；未重建数据库或恢复周期。新镜像build成功。测试容器、Web、新构建镜像的33份指定文件逐一匹配最终清单，见[测试运行](cancelled-only-runtime.json)、[Web](web-source.json)、[构建镜像](built-source.json)；这不等于全镜像审计。实际命令：

```sh
docker exec xgd-b08-check env/bin/python /b01/check_source.py /b01/b08-history-paths-source-manifest.json
docker exec xgd-b08-ui env/bin/python /b01/check_source.py /b01/b08-history-paths-source-manifest.json
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b08-history-paths-source-manifest.json
docker exec xgd-b08-check env/bin/python /b01/b08_metrics_preserve.py
```

最后一条仅复用只读保留脚本，不重跑指标测试。源测试站11张原业务表按此前已记录的新增schema列排除口径，与上一包快照数量/哈希一致；Workflow仍0。见[保留摘要](source-retention-summary.json)，不外推全数据库、客户数据或所有权限配置审计。

本轮无页面布局或浏览器交互代码变化，页面旧通过证据未重跑；独立HTTP不冒充页面或现场验收。

## 独立HTTP与最终保留

复用专用合成Web站，另建1名普通测试用户、1个仅用于本轮的窄测试角色及4张新工单（2已审批、2草稿），正常确认2再更正1形成取消原卡和生效替代卡。原账号、共享岗位与既有权限行未改；有数据的工序未配置计价依据，避免被旧计价校验提前拒绝。预检以真实token核当前身份和两个父对象/子行的原生读写、提交、删除权限，不使用System Manager权限或无效CSRF制造拒绝。角色授权仅用于隔离验收，不是客户配置方案。

[HTTP聚合](http-summary.json)记录**13个不同写入请求：7拒绝、6合法正例，写入请求未重复**；读取/权限预检不计入13个。结果为：

| 实际动作 | 实际结果与证据边界 |
|---|---|
| client.save工序改parent、改operation；Resource DELETE工序；Resource PUT改parent | 各403，命中新工序历史保护；未依赖工资字段 |
| 取消态原时间行Resource DELETE、同步批量delete_items | 分别403、200；都命中原时间行历史保护。批量返回目标仍未删除列表，不把200当成功删除 |
| 取消态原时间行client.delete | 417，原生“无法编辑已取消文档”；明确区别于本轮新增保护 |
| 无历史草稿工序client.save | 200，值保存且归属未变 |
| 新无事实草稿工序Resource DELETE/client.delete | 分别202/200，仅删除本轮第3/2行，保留sequence1和父单 |
| 新空白草稿时间行Resource/client/同步批量delete | 分别202/200/200，3行分别删除，父单和历史原卡保留 |

每个拒绝均前后独立GET读取7个受保护对象，所有返回字段及关联的摘要一致。草稿删除后子行GET均返回403；此状态本身不证明删除成功，另用有权父对象读取和服务器独立只读DB“不存在”核实。最后取消原卡、替代卡及原时间行字段/关联一致。时间行改parent的新状态组合有受控方法证据；本轮HTTP没有把旧时间行PUT再跑一遍。

3批脚本停止完整保留：`http-acceptance.json`最初只解析_server_messages而漏掉原生exception字段；`http-remaining.json`把已删除子行GET误预期404，实际原生权限屏蔽为403；`http-finish.json`对省略null的返回使用下标导致KeyError，尚未发时间行删除。只修脚本并续接未执行动作；已发删除以保存响应和独立DB补核，未重发。另1次本地语法错误发生在请求前，未发送HTTP；最终`http-empty-times.json`完成最后3个正例。这些不是产品新失败，不抹去退出码1，也不将聚合冒充一次全量脚本成功。

HTTP各批开始前未保存当批脚本哈希，聚合明确`per_batch_script_hash_captured=false`。`f31a764…`仅为最后实际批次完成后捕获的文件哈希；最终`4d83d5…`为收口脚本，随后将已单独验证的Resource PUT接入完整路径、调整完整单次运行的内存基线读取。这两处仅AST核查，没有重跑完整`--run`，不能将最终脚本哈希倒填各批次或称完整脚本已验。产品源码始终按上述33文件清单核对。

实际命令、各批退出码及动作见聚合，核心执行为：

```sh
docker exec xgd-b08-check env/bin/python /b01/b08_history_paths_http_fixture.py setup
python3 .development/checks/b08_history_paths_http.py
python3 .development/checks/b08_history_paths_http.py --run --deployment-confirmed
python3 .development/checks/b08_history_paths_http.py --run --deployment-confirmed --remaining
python3 .development/checks/b08_history_paths_http.py --run --deployment-confirmed --finish
python3 .development/checks/b08_history_paths_http.py --run --deployment-confirmed --empty-times
docker exec xgd-b08-check env/bin/python /b01/b08_history_paths_http_fixture.py preserve
```

[最终保留](http-retention-final.json)：专用站11张原业务表共461行、5类原安全配置共860行，已捕获原行/列缺失0、变化0；3张库存表新增0。最终新增合成工单4、Job Card8（包括计划卡和确认/更正卡）、时间行2等保留。本轮仅删除预先白名单里的2个新无事实工序行及3个新空白时间行，不删除旧数据；不外推全库或未捕获字段。原规则与开发/客户Workflow未因本轮启用，后台周期未恢复。

**未测及收口边界：**普通PC页面/手机/弱网/人工现场未新验；同步批量仅单项拒绝与单项合法删除分别执行，没有混合整批原子性或大于10后台队列结论。完整父单删除/复制/重命名、库存逆向、G1/G2/G3、Z01干净环境和独立接手继续保留。只收口此有限原记录旁路包，B08/B09整卡及OpenSpec不关闭/归档。公开白名单保存与远端回读待实际完成补记。

发布前复核：`openspec validate b08-followup-20261028 --json`实际valid=true，仍有引用模式0任务警告，原卡保持权威且不归档；维护源码`git diff --check`通过。一次独立发布材料审查对安全摘要与脚本检查未发现需阻止发布的泄漏或结论越界；最终导出检查和远端回读另记。
