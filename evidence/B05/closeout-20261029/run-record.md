> 公开归档副本（2026-10-29）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B05活动计时收尾与人工结束有限包

## 本包结果

按用户授权先补[R07绑定](../../R07/card-binding.md#2026-10-29-b05活动计时收尾与人工结束绑定)，再在原B05开发验收。只完成活动计时、人工结束差额/原因三个余项；B05整卡仍部分完成。原建单、确认生成、B08/I03～I06等未变批次未重跑。

- 真实开放计时按非取消作业卡及原时间行识别，草稿也阻止结束，不依赖列表可见性或状态标签。
- 厂长填写实际时刻收尾既有草稿时段，Stopped也可收尾但不恢复；既有from/数量/工序/原记录保留，native save计算分钟，不submit、不确认产量。已提交开放卡/时段异常拒绝修写。
- 原close入口核当前对象write/read、厂长、本公司、批准状态、版本和必填原因。Closed拒绝重复。原Comment同事务保存中文操作者/时间/原因、各工序计划/良/不良/未清、成品入库及未入库差额，不改实际报工日期或补造合格交付。
- 原标准make_time_log先锁父工单再卡，与本包收尾/结束一致。只证明这条合法链，不扩成通用资源或完整G3。

## 版本与环境

开工公开main实际git pull --ff-only origin main为Already up to date，HEAD为65b0a8a30baff197985b811a2ba7188815e83651。固定上游ERPNext 15.124.1 / 4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e、Frappe15.124.0，原维护checkout及25份累计成果保留。本包只改原work_order.py/.js/test_work_order.py和job_card.py四份；无元数据/依赖变化。最终累计patch为3e9b706c7b293631e86b5a73e662bdc9b048168bd8b9fee2b4f05e098c94d4cf；中间12项源码为f8d440034be7698f3cdd539909dfb618d01f08cc77852eb45ae8a1e472b13cb9，两份清单不混用。

复用原xgd-b08-check及18090专用合成网页/数据库，只按4文件docker cp同步，noreload网页进程必要重启两次；未build、建站、reload-doc或初始化依赖。最终测试/网页各33项指定运行文件与清单匹配，不代表全镜像审计；镜像tag不代表含本补丁，新机器仍按源码锁构建。本轮未操作开发/客户审批或后台周期。

## 实际命令与结果

| 检查 | 命令／动作 | 实际结果与限制 |
|---|---|---|
| 最小fixture/原缺陷 | `docker exec xgd-b08-check env/bin/python /b01/b05_closeout_tests.py TestWorkOrderCloseout.test_00_fixture_runnable TestWorkOrderCloseout.test_open_draft_timer_is_not_ignored_by_legacy_signature` | 2项17.432秒，fixture过，原结束带开放草稿未报错而实际Closed，缺陷测试失败；旧11表回滚一致 |
| 首轮 | `docker exec xgd-b08-check env/bin/python /b01/b05_closeout_tests.py` | 10项82.697秒，9过/1测试脚本KeyError；原返回name误取job_card，纠正脚本，不当作产品失败 |
| 主要限定批次 | `docker exec xgd-b08-check env/bin/python /b01/b05_closeout_tests.py TestWorkOrderCloseout TestWorkOrderApprovalChanges.test_close_endpoint_cannot_resume_stopped_order TestWorkOrderApprovalChanges.test_stop_requires_director_reason_and_viewed_version` | 10新＋2直接受影响原方法，同批12项106.701秒，0失败/错误，旧11表回滚一致；对应中间源码f8d44003 |
| 中文持久化显示 | 给原结束方法补中文原文断言，单独运行`TestWorkOrderCloseout.test_finish_then_close_preserves_gap_reason_and_original_facts` | 先1项9.897秒失败；仅ensure_ascii=False修后1项9.104秒通过，旧11表一致，绑定最终3e9b706c。不冒称13个独立方法或最终全量重测 |
| 页面 | `playwright-cli -s=b05-closeout run-code --filename=<私有步骤文件>`，新普通厂长登录/原状态→人工结束 | 实际2条流程：活动计时9→10点60分钟后仍In Process，良8/不良2/入库0不变，再填原因结束；Stopped计时11→12点后仍Stopped再结束。两单重开Closed、原因可见 |
| 中文显示修后 | 仅新第四张无计时/报工样例，原页面填原因结束重开 | 原Comment中文键/原因/差额可读；截图实际查看。前三张原编码记录保留，不覆盖失败证据 |
| 重叠HTTP | `python3 .development/checks/b05_closeout_race.py` | 第三张新单2请求客户端区间重叠78.016167ms；开始200、结束417活动冲突，仅一次初始成功；再正常收尾/结束，草稿计时量0、正式报工新增0。不是DB锁轨迹、压力、共享工位并发或完整G3 |
| 数据保留 | `docker exec xgd-b08-check env/bin/python /b01/b05_closeout_ui_preserve.py` | 最终旧23表捕获行/列差异0；新单4/计划卡12＋正式报工1，全部Closed/活动0。该报工仍良8不良2、60分钟；原事实日期07→08点保持，计划计时未叠加报工分钟。Stock Entry/Stock Ledger新增0 |
| 源码 | 两容器`env/bin/python /b01/check_source.py /b01/b05-closeout-source-manifest.json` | 最终33指定文件匹配；中间测试批次清单另存，不合并结果 |
| 静态／需求 | Python编译/Node --check/git diff --check；OpenSpec validate --strict | 按实际最终输出收尾，不以规划齐全或no-tasks代替业务结果 |

权限负例包含非厂长、无角色、跨对象指纹、公司授权撤销、陈旧工单/计时、时间倒序/未来/非法、已提交开放事实、重复结束。失败注入在timer save后及close状态更新后的Comment创建处，异常上抛并显式savepoint恢复；属于受控DB回滚，不声称HTTP故障自动回滚。

首个网页fixture误导入上游test_workstation，在测试依赖Project唯一性冲突中失败；native make_test_records默认commit=False，finally rollback，未执行该脚本commit。已改用原Workstation DocType最小样例，不安装/装载无关依赖。第一次持久化回读在中文转义断言失败，原件保留；最终回读独立文件通过，不把失败覆盖成成功。网页已有socket.io轮询404，本包真实点击/保存/重开通过，实时服务与通知未验证，不展开基础设施工作。

## 证据与停止点

本目录`acceptance-summary.json`、`intermediate-suite-source.json`、`source-manifest.json`、两个runtime-source、`ui-preserve-final.json`、`http-race.json`及两个patch可公开；测试stdout、私有样例、凭据、页面全输出和截图仅本地保留，以publication索引的哈希定位，不上传业务运行数据。独立审查见review-notes.md。原34张卡不增加，OpenSpec只引用原B05/R07。

只收口本包；B05字段/编号/缺前置提示等其余条件、B06/B07余项、手机/现场、完整G1/G2/G3、Z01干净启动/备份恢复/独立接手和正式交付仍未完成。GitHub CI结果未验证；本地受控验证与中文PC不代替客户业务验收。


本包OpenSpec已在实际限定验收通过后同步`openspec/specs/production-order-closeout/spec.md`，原Purpose/全部新增需求一致性校验及main/delta严格校验通过，再归档到`openspec/changes/archive/2026-10-29-work-order-closeout-20261029/`。原两项活动变更保留，B05整卡不归档。公开保存按原授权白名单执行，最终提交/远端状态以实际回执为准。
