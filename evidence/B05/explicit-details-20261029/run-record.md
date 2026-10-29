> 公开归档副本（2026-10-29）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B05/B06/B07空明细与人工确认生成：限定包结果

## 做什么、边界与版本

用户2026-10-29明确授权：从最新TODO的R07补绑开始，绑定后按原B05/B06/B07开发并验收。实际只改原Work Order控制器/表单/测试3份产品文件；新增本包检查脚本、文档及必要发布清单接入，不新增元数据/依赖，不改BOM算法、Job Card、库存账或Frappe。完整状态收尾、任务编辑/复制、领退结构锁、手机/现场、G1/G2/G3及Z01不在本包，不重跑不变已验子包。

- 开工公开main：`4925f5bf14d94338ef4b305a41c63c1dd54a915d`；固定ERPNext上游`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，Frappe v15.124.0；维护分支`codex/xgd-maintenance`，保留原25份累计源码/e15fba。
- 最终累计补丁SHA-256：`5823ca570ba376fd8af67d386dd2898c987cd56f3655686c9f9a6b9256aa356e`。本包三文件差异为`bounded-change.patch`，累计源码补丁为`implementation.patch`；[最终33项清单](source-manifest.json)与测试/网页实际文件均匹配。
- 复用现有维护checkout，不新建会丢累计未提交补丁的worktree。OpenSpec/Playwright及现有依赖复用；本包独立change引用原卡，不另建任务编号或第二套验收清单。

## 绑定与实现

[原R07本包绑定](../../R07/card-binding.md#2026-10-29-b05b06b07空明细与人工确认生成绑定)先写真实触发、函数/参数、允许文件、输入/命令/判据后实施。原CASE-01需求未增加；五项目原固定来源/许可边界沿R03～R06，实际只复用ERPNext/Frappe，不重选/重装/复制其他项目代码。

1. `WorkOrder.validate`不再给审批工单空表补用料，`reset_use_multi_level_bom`也不自动展开；原非审批行为保持。表单BOM/数量/多层开关不自动调用生成。
2. 新增同模块只读`preview_production_order_details(work_order, expected_modified)`与`confirm_production_order_details(work_order, expected_modified, fingerprint)`。read/write、本人发起/当前角色、公司/班组、草稿/退回和BOM read在后端检查；确认锁父工单后重读。
3. 计划复用`set_work_order_operations`、原工序规范化和`set_required_items`；来源/输出指纹在确认时重算。原save事务生效；相同已存计划直接返回、不再次save，已有不同计划拒绝覆盖。空明细不得送审，批准前没有可执行Job Card或库存事实。
4. 现有计划改变数量/BOM/展开开关/仓库等依据拒绝；本人需先核对并清空草稿明细再改依据、重新预览确认。此选择保留旧计划不被静默覆盖，代价是调整时多一步人工核对，不声称完整草稿调整功能已完成。
5. 中文原生表单按钮和预览对话框显示工序/数量/用料/库存单位；先保存后预览，取消不写入，确认后重开可核。

## 真实命令和结果

运行均使用原`xgd-test.localhost`与保留的`xgd-b08-check`，新测试复用原审批fixture及事务回滚；不递归装载Payment Gateway。下面日志原件仅本地留存，公开结果见[摘要](acceptance-summary.json)。

| 阶段 | 命令／方法 | 实际结果及限制 |
|---|---|---|
| 最小夹具 | `docker exec xgd-b08-check env/bin/python /b01/b05_details_tests.py TestWorkOrderExplicitDetails.test_empty_draft_stays_empty` | 首次在Nos整数量纲装0.5报错；非产品失败，原件red-empty.log保留。改成独立小数单位/原料，不改共享设置 |
| 实施前红色 | `docker exec xgd-b08-check env/bin/python /b01/b05_details_tests.py` | 5项36.606秒，5失败/0错误；空工单实际用料1而非0，预览/确认入口缺失，旧11表保持 |
| 第一版绿 | 同一runner默认本类 | 5项31.400秒通过；不覆盖后续审查缺口 |
| 第一版受影响原回归 | runner指定`TestWorkOrderApproval.test_normal_two_stage_workflow`和`TestWorkOrderRequiredQuantity.test_quantity_fixture_runnable` | 2项6.334秒通过；未跑Q05、旧B08/I03～I06或全量上游测试 |
| 审查反例 | runner指定新增4方法，日志review-red.log；夹具修正后只重跑多层开关/无序号两项 | 已复现自动生成(3/1≠0/0)、旧计划改量未拒绝、单工序/无序号重试冲突。首次无序号用None触发DB非空约束、开关未翻转默认值，均保留并改用原生默认0/真实翻转；不把夹具错误当产品失败 |
| 最终绿与受影响原回归 | `docker exec xgd-b08-check env/bin/python /b01/b05_details_tests.py TestWorkOrderExplicitDetails TestWorkOrderApproval.test_normal_two_stage_workflow TestWorkOrderRequiredQuantity.test_quantity_fixture_runnable` | **同次11项63.418秒通过，0失败/0错误，旧11表回滚一致**。9个本包新方法＋2个原回归；final-with-revocation.log及摘要可核 |
| 运行源码 | 两容器各执行`env/bin/python /b01/check_source.py /b01/b05-details-source-manifest.json` | 各33项文件匹配，模块路径正确；测试容器首核只差未用于Python测试的work_order.js，补同步后仅复核身份，无重复业务测试 |
| 网页数据保留 | `docker exec xgd-b08-check env/bin/python /b01/b05_details_ui_preserve.py` | 原21表捕获行/列差异0；新浏览器工单1，3工序/1行需求5，Job Card/Stock Entry均0，仍草稿 |

受控故障在原save完成后抛错，观察已写3工序后显式savepoint回滚、再恢复确认；这是实际DB受控回滚，不冒充HTTP进程崩溃或完整G3。

## 普通发起人中文PC实际验收

使用已安装Playwright CLI 0.1.22、独立`b05-details`会话、原本机18090专用合成站。新建一个独立普通发起人、一个只读资料角色与独立BOM/产品/小数原料；不改变旧账户/共享岗位，不重放旧工单。截图/浏览器原件/凭据仅在`.development/private/b05-details-20261029/`。

- 页面按详情/生产物料/配置原标签实际填写班组、产品、BOM、数量和仓库；保存并重开，0任务/0用料。
- 点击“预览任务和用料”实际显示3工序、每道计划10、用料5及库存单位；关闭对话框，明细仍0/0且未产生脏状态。
- 在最终源码服务上重新预览并点击“确认生成任务和用料”，页面回读3/1、需求5；重开明细ID不变。
- 再由页面预览/确认，明细ID及工单modified均不变，证明本次没有再次save或追加；切换到实际工序面板等待原生切换完成，三行可见，截图保留。
- 中间真实问题保留：新合成角色缺Project链接元数据权限，后仅给该新角色Project select，不授read；首次自动化在仓库Link异步校验完成前点击保存，原生必填拒绝，值就绪后同一表单成功。不是产品修补或旧数据重建。截图首次过早捕获标签过渡态，另保留正确面板截图。
- 原专用开发服务器没有socket.io服务，浏览器控制台保留其404及原依赖提示；没有以这些提示改造无关服务。完整生产服务、实时通知及其他页面不在验收范围。

## 审查、保存与停止

一次独立只读审阅发现3个Important、Critical 0；[审查记录](review-notes.md)已保留。三项均以本包反例复现后修补，最终同次11项通过；未重派第二轮审查。范围外整卡/库存/G3/交付继续开放，不据此豁免本包数量或权限保护。

本机Docker最初普通权限不可见socket、普通启动失败；使用本机权限启动已有Docker成功，仅启动本项目既有DB/Redis/测试/专用网页。未重建站点或镜像、未重装依赖、未迁移元数据、未恢复后台周期；原开发/客户站点未启用审批。本包容器按3文件同步并核实际33文件，不声称固定镜像本身包含新补丁。

公开只保存本包源码/测试定义、原卡/OpenSpec及脱敏结果/源码哈希，原始日志、截图、凭据/DB均留本地。发布辅助脚本只接入本包最新清单/补丁及安全摘要，旧测试回执继续绑定各自历史补丁，不把旧结果写成新源码通过。最终推送/回读SHA在交付回复报告，不循环回填自身最终提交。

本包所需实现、测试、普通中文PC及数据/源码核对已经满足；仅关闭对应有限子项。B05/B06/B07整卡均部分完成，G1/G2/G3、现场、手机、完整库存/结构锁、真实AI和Z01仍开放，用户未授权的后续范围不自动开始。

收尾补齐每卡明确要求的撤权场景：同一发起人经原生User Permission撤公司授权后，旧预览的查询/确认均拒绝且明细仍0/0；恢复授权后同一方法继续正例/跨班组/冻结分支。该断言只补原scope方法，未改产品；最终9新＋2原回归仍为11个方法，`final-with-revocation.log`同次11项63.418秒通过。此前11项63.433秒结果、当时源码清单/补丁保留为before-revocation历史，不混称同版本。

公开归档静态核验：240处本地链接/锚点断链0，34个唯一卡号；旧34份测试回执逐项不变；公开430文件/429内容哈希及25份产品源码一致，已知凭据/原始运行数据匹配0。原ERPNext源码`git diff --check`及Python AST、JS语法通过。首次暂存空白检查把新增.patch文件必需的上下文空格/制表符当作格式错误；保留补丁原文，只排除本包两份补丁文本，其余暂存文件空白检查通过。该格式检查不是产品或业务失败，不为此改补丁/源码或重跑业务。
