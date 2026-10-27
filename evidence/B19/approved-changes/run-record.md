> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B19 批准后变更、终止与停止执行

2026-10-27。用户本轮明确授权按最新任务卡继续V04/V07：先保留真实失败，再局部修补。起点公开提交f8a4fb3268dc49dd9d595843369e843b282345e6，产品补丁9dc8ad795d4c7d4ac84130dfad522e4f0abbeb587e3215653f7bf9ff9c5635a2；ERPNext v15.124.1/Frappe v15.124.0固定不变。

## 本批绑定与决策

- 复用原Work Order生命周期、原生Workflow转换/取消修订、stop_unstop、Stock Entry过账/取消/退料和既有合成fixture；测试在xgd-test.localhost事务内回滚，不碰持久化HTTP副本。新增类TestWorkOrderApprovalChanges在原test_work_order.py，不另造测试系统。
- 先验最小批准样例，然后验证已批准计划日期改写、发起人终止、原生恢复旁路、停止后的合法退料/库存取消。批准后无执行事实取消修订、已有事实保留与关联新单按原V07继续；数量、报工原记录和完整并发门槛不据本批通过。
- 已核原生提交后保存走before_update_after_submit而非普通validate；计划开始/结束日期原字段allow_on_submit=1。原生stop_unstop直接update_status，须实测是否绕过；当前Workflow fixture有终止状态但无对应转换。以上仅静态发现，未先当测试结论。
- 用户本轮已明确确认：批准后取消修订/停止仅生产厂长执行并填原因。批准前终止申请由发起人处理，原因必填，沿C10。未新增岗位或审批层级。

允许改动仍限R07绑定的原控制器、原测试、原生配置/元数据。只解决真实失败，不改Frappe、不新增审批引擎/库存账，不启用开发或客户流程。原生取消有删除待执行任务等副作用，须核事实边界，不能把存在任务等同已经报工。

```sh
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b19-changes-source-manifest.json
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --test test_00_change_fixture_runnable --skip-test-records --skip-before-tests
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --case TestWorkOrderApprovalChanges --skip-test-records --skip-before-tests
```

测试源码版本、失败/修补结果、范围和后续在本页续记。已有完成项只按受影响路径回归；不重新全量初始化、不安装Payment Gateway、不删除历史证据。

## 失败记录与最小修补方案

最小fixture单独1项通过。首批6项：fixture通过，计划日期与恢复旁路2项FAIL，终止转换、停止后退料和库存取消3项ERROR，均记录真实业务调用及堆栈。另无事实取消修订1项在缺少原生转换处失败。不存在的新转换未被假称为已支持。

Ruling: 在同一Work Order控制器补before_update_after_submit与before_cancel，复用现有审批校验，封住生命周期差异；终止/取消配置仍用原生Workflow。停止执行接入现有apply_production_approval的版本、锁、岗位与原因边界，再调用原生stop_unstop；原生通用入口不得绕回。只增加原R07已列出的previous_work_order字段，已有事实关联新单不得冒充amended_from。库存停止校验仅对本审批工单的真实退料/取消放行，数量算法不变。原生结束入口的状态参数不得恢复已停止单，完整结束差额/报工规则仍归B05/G2。

代价/限制：增加本审批工单局部生命周期钩子和一个已绑定关联字段；不是全平台防篡改或完整并发方案。配置仍只在隔离fixture，客户/开发站点不激活。

首次修补16项回归有14项通过、2项测试准备ERROR：原生copy_doc默认复制no_copy且测试模式保留docstatus。仅在测试复制调用期间恢复原生真实请求行为，并传ignore_no_copy=False，finally恢复测试标志；未放宽产品校验。随后发现草稿保存可改挂未停止来源，新增负例实际FAIL后将来源检查覆盖新增/改挂/公司变更；17项回归通过。

一次独立审查提出P1：跳过领料工单停止后取消部分成品入库，get_status末尾会覆盖Stopped。新增真实样例：同单两笔各2成品入库，停止后取消一笔；实际剩余产量2、状态错误变成In Process（review-red.log）。修补仅在原状态计算末尾保留Stopped/Closed，不改产量/库存数量公式。此修补也保持原生非审批工单的停止/关闭语义，不新增业务模式；完整开工/结束与数量口径仍归原卡。最终复测及有限相关回归结果在下方记录，不将此前17项充当最终版本结果。

## 最终版本与验证范围

最终补丁SHA256：`a6478acc8c02c08b2b2775c273f802a45c0871196c51e5e12c160766f718d25d`。构建后按清单核对实际Bench容器14个文件全部一致（source-final.json）；不是以镜像标签推断。最终TestWorkOrderApprovalChanges共18项、224.690秒、OK（final-results.log）。覆盖工单冻结、终止权限/原因、原生旁路、取消修订重审、库存/计时事实保留、停止后允许退料/取消但拒绝新增执行、来源关联权限/改挂、部分成品取消仍保留停止状态。

本批只进一步修改原work_order.py、test_work_order.py、stock_entry.py；维护分支累计7个源码/测试文件。测试元数据脚本增加原R07已绑定的previous_work_order；无新增依赖、Frappe修改或新事实账。Workflow仅为事务内fixture，未配置为开发/客户可用流程。

受影响回归命令如下，均在同一最终镜像串行运行；完整输出留本地，实际计数与结果写入closeout-check.json，公开副本仅提供计数/哈希：

```sh
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --case TestWorkOrderApproval --skip-test-records --skip-before-tests
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.stock.doctype.stock_entry.test_stock_entry --test test_approved_stock_transfer_allowed --test test_approved_transfer_cancellation_preserved --test test_approved_material_return_preserved --skip-test-records --skip-before-tests
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --test test_skip_transfer_work_order_completed_with_fractional_process_loss --skip-test-records --skip-before-tests
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/b19_prepare.py
```

限制与下一步：这是服务器受控验证，不是本批新动作实际HTTP、中文手机操作或客户验收。下一步先在保留的专用HTTP副本增补新动作样例，核对新镜像/元数据和旧数据保留，再验证真实请求；之后补附件/全部依据还原及必要中文网页。不重建已有副本、不把旧HTTP结果移到新补丁上。活动计时收尾、完整结束差额归B05/G2；G1数量、G2逐笔报工原记录/岗位回写、G3完整并发均未通过。外部提醒/客户部署仍未执行。

发布遵循现有白名单：原始测试单据、库、私密配置和运行日志不上传；公开完整修改源码、原任务卡、方法/失败/结果及哈希。提交前的远程完整性尚待实际push与新克隆核验；推送后的独立回读保存在本地evidence/发布/B19-changes-2026-10-27-remote.json，不为嵌入自身提交SHA制造循环提交。

### 回归与旧数据实际结果

- 同一最终补丁：审批核心17项/113.063秒、库存授权领料/退料/取消3项/29.453秒均OK。
- 原上游状态测试在TestWorkOrder.setUp的批次物料准备处因缺Item Group: Products而ERROR，0.166秒，尚未进入断言（status-native.log）。这个原测试仍未通过，不能改称通过。未补全量fixture或安装额外模块。
- 最小替代是`.development/checks/b19_status_regression.py`：只用内存Work Order和真实get_status，查询实际元数据，未保存单据、未mock业务。保留原11.4/11.2/0.2输入，另验部分产量、Stopped、Closed；4项/1.538秒OK（status-regression.log）。命令：`docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/b19_status_regression.py`。它是状态计算验证，不冒充上游整类或库存过账验收；真实取消库存后状态的写路径由本批18项覆盖。
- 末次只读核对：data-before/data-after的11张原业务表计数和内容哈希一致；原测试站点Work Order流程数量0，旧单审批字段仍为空。新增关联字段仅为测试元数据。持久化HTTP副本和开发/客户站点未改动。
- 本批已达服务器限定子项结束条件；任务卡保持部分完成，后续入口见上节。实际结果、日志哈希与限制见closeout-check.json；不累加此前补丁的历史测试为当前全量通过。
