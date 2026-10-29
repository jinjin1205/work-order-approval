> 公开归档副本（2026-10-29）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B05 状态动作与未覆盖入口（2026-10-29）

## 结论与停止点

本轮状态/入口包已实现并完成限定服务器及中文PC验收；先补R07，只修改原Work Order四文件，无新字段、表、API、依赖或状态机。原字段/编号/日期提示、显式生成、计时/人工结束、报工与库存计算按旧证据复用。本包不代表客户验收、完整G1/G2/G3、手机或Z01交付。

**为什么仍显示B05：**原B05把字段、建单预检、生成衔接、状态和历史入口放在同一张大卡，前三轮关闭的是不同子包；旧“下一执行包”和新结果并存，剩余项没有集中列清。本轮已按入口完成对账。原卡仅剩数量原始精度待B04证据回链，不再以笼统“状态/未覆盖入口”重开B05功能包；下一开发入口是原B06。原34卡仍7收口/12部分/15未完成，不把子项完成冒充整卡增加。

## 版本与环境

- 公开基线：`b26633cb871b2cd4667b943493cf787234b8d93e`，开工实际`git pull --ff-only origin main`无更新。
- 维护树：`.development/repos/erpnext`，`codex/xgd-maintenance`，上游HEAD `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；既有25份改动保留，增加既有work_order.json后累计26份，未新增产品文件。
- ERPNext15.124.1/Frappe15.124.0；保留`xgd-b08-check`回滚站及`xgd-b08-ui`合成HTTP站18090，未建站/重装/升级/构建镜像。
- 最终累计补丁SHA256 `a3493e9f94f9ef5a0c37ca468014d88331e5f599bcb2574137f5ec01e9701a5c`；[清单](source-manifest.json)、[累计补丁](implementation.patch)、[四文件限定差异](bounded-change.patch)。测试/网页容器34份清单文件实际匹配；这不是全镜像审计。

## 已核复用与真实修补

继续沿R03～R06五候选结论，直接复用ERPNext/Frappe主底座；没有重选或安装其他系统。

| 实证缺口 | 最小处理与保留边界 |
|---|---|
| 原生复制带计划和实际日期 | 原operations/actual_start_date/actual_end_date加no_copy，复用原生复制；不造复制器 |
| 普通新建可填父/工序实绩或预填计划 | 原新建信任边界复用B04数量校验，拒绝实绩及任务/用料；先空insert，再沿原草稿入口准备计划 |
| 审批单仍暴露服务器禁止的原生停止/恢复；Start/Finish含义混淆 | 审批单去原生停止/恢复，使用原厂长+版本+原因动作；库存按钮标生产领料/成品入库，未操作库存 |
| Stopped无事实单菜单有取消修订，原生却要求先恢复 | 实际HTTP417及仅回滚诊断定位validate_cancel；审批单继续先经过before_cancel的授权/历史保护，再允许无事实取消，非审批分支原样 |
| Workflow只读掩去amend，原生按钮不出现 | 只按原基础create/amend及生产发起角色补可见按钮，调用原frm.amend_doc，不改Frappe、Workflow配置或权限掩码 |
| 原生from_amend忽略no_copy，带旧申请/审核人及3计划/1用料、Cancelled状态 | 仅新项目修订单onload清审批/计划/实绩，设Draft/草稿；保存后由服务器赋当前发起人，源单不变 |

父删继续复用原权限和审批历史保护。无历史且有权的本包新复制草稿可删；有审批历史的已取消新样例页面DELETE实际403，提示保留原记录。未新增平行拦截器或事实账。

## 服务器验证：按批次，不能合称一次最终全量

命令入口：`docker exec xgd-b08-check env/bin/python /b01/b05_entries_tests.py <明确方法...>`；fixture沿原TestWorkOrderApproval/TestProductionReportConfirmation，普通岗位真实DocType/Workflow/报工入口，不mock业务写入。每批finally回滚，并核原15表完整快照一致。

| 批次 | 实际结果 | 源码/记录 |
|---|---|---|
| 初始新四方法 | 4项37.127秒OK | green-first.log；intermediate-suite-source.json，9ba96745 |
| 复制直接影响两原方法 | 2项19.704秒OK | affected-copy.log；affected-copy-source.json，f5fe615b |
| 新工序实绩输入 | 红1方法6子项失败→单项8.800秒OK | red-row-facts.log/green-row-facts.log；row-facts-source.json，d3ba8404 |
| 无执行停止单取消 | 真实页面417/回滚诊断为原生Stopped阻挡；unit最初缺cancel测试许可，补fixture后1项9.642秒OK | red-stopped-cancel.log/green-stopped-cancel-scoped.log；stopped-cancel-source.json，0ada21ae |
| 新建预填计划旁路 | 1项9.005秒真实FAIL | red-new-plan.log，未把原合法一行计划当执行事实 |
| 最终最小fixture | 1项8.789秒OK | final-fixture.log；final-fixture-source.json，ea69880d |
| 最终受影响方法 | 10项103.397秒，9通过、1准备ERROR，整批FAILED | final-affected.log；final-backend-source.json，93534d79 |
| 唯一准备ERROR续验 | 报工后fixture未刷新版本，原保护正确拒绝；只加reload，1项11.483秒OK | final-history-only.log；最终a3493e9f |

最终覆盖11个不同方法：8个本轮方法（含最小fixture）、原正常两级审批、无事实取消修订、剩余需求关联。已通过9项未重跑；没有把FAILED日志写成OK。新建0/0规则改变了fixture创建步骤，因此最终只复验这个有限集合，不运行B04、计时结束、B08或ERPNext旧整批。

**准备/脚本失败保留：**初次测试类插在旧Header类中间，误带旧方法，已SIGINT/事务回滚并恢复类归属，记red-baseline.log；后续限定方法名。文档脚本一次编码错误及错误回执路径发生在产品改动前。UI fixture误选无私有挂载的网页容器，读取fixture前失败；改用原check容器。新0/0规则下原上游helper预填材料使final-server.log 11项均准备ERROR；先显式清空并移计划到insert后，单独P0通过后才运行上述10项。这些都不计业务失败或通过。

## 真实中文PC

Playwright CLI0.1.22、独立Chrome会话`b05-entries`，复用18090。新增普通发起人/厂长2用户、2窄角色，未授System Manager/Manufacturing Manager；新发起人原生amend最初为假，仅在其本包新角色补amend，旧角色/用户/权限不动。普通岗位import及Data Import create均假；不启用管理导入。

1. 新预备单已批准/未开工，页面状态菜单无原生停止/恢复，显示原受控停止和取消修订；库存Start显示生产领料。厂长填原因停止HTTP200，实际日期仍空。
2. 停止后取消首试417，原单仍Stopped；修补原生冲突后，只续接同单取消HTTP200，已取消/Cancelled，数量10、无实际日期，原因和处理记录保留。
3. 普通发起人从只读旧Closed样例点原生“重复项”，新草稿0任务/0用料、无实际日期。量0实际417且中文计划量提示；改10保存200、同号重开仍0/0。无历史的新复制单页面删除200。
4. 已取消新样例有原生amend权限仍无按钮，修后显示“修订”。首次只预览未保存修订单，实见3/1及旧审批，修后原按钮进入空草稿、旧审批清空，保存200并同号重开，关联原取消单、当前发起人由服务器赋值、无旧审核人/实绩。
5. 普通发起人尝试删除已取消的新原单，页面HTTP403，明确“工单已进入审批，原单及历史记录不能改写、删除或改挂”。本轮不删除旧复制源单。

原始脚本/响应/凭据/截图仅在`.development/private/b05-entries-20261029/`。不公开原始业务对象、登录日志或网络头。API结果与页面结果分别记，不将后台成功当页面通过。

**页面脚本续接说明：**停止消息弹窗挡后续点击、关闭按钮匹配到隐藏最小化按钮、原生Duplicate实际译为“重复项”、复制后默认详情页签使数量输入不可见、删除文本匹配到隐藏子表按钮、重开时cur_frm瞬时为空，均按实读DOM续接同一对象，没有另造复制单或重复停止。原生beforeunload使修订脚本初次日志未输出Result，但同一脚本继续完成；最终以修订同号重开独立回读及持久化核对补齐，不把未输出Result当通过。既有socket.io轮询404保留，未称实时推送通过。

## 数据、审查与边界

最终[回读](ui-preserve-final.json)：原23表旧业务字段全部保持；原始整行哈希差异1处，仅旧复制源单_seen增加本轮实际读者。只读副本减去该读者并按原生序列化后与开工哈希完全一致，其余字段零差异。保留阅读审计，未改回或删掉；不称“全部旧行字节零变化”。

新单最终保留2张（已取消原单及空修订单），先前新空复制单已删；3张新待执行作业卡，正式报工0、计时0、库存/台账新增0。原库存及报工事实不重写。2新用户、2新角色；旧用户/角色/权限捕获行一致。

Python编译、Node语法、维护树diff --check及测试/网页34文件实际清单通过。[一次独立审查](review-notes.md)无Critical/Important/Minor。公开保存须以最终远端重新克隆回执为准，本文不预填推送或CI通过。

OpenSpec主规格Purpose与全部ADDED要求已逐字同步，3份主规格strict验证通过；仅`work-order-entries-20261029`已归档至`openspec/changes/archive/2026-10-29-work-order-entries-20261029/`，归档相对链接已修正。引用原卡的no-tasks不当作业务完成依据，原B05仍保留B04回链条件。

未覆盖原范围：B04 Work Order网页原始数量精度、B06任务调整/历史、B07全局结构/历史、B19其余页面/依据、可选销售单404、完整G1/G2/G3、真手机/现场及Z01。上述按原卡归属，不能反向制造无限B05包，也不从本包推出已验结论。
