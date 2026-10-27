> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B19 实际HTTP与内部提交批量审批

2026-10-27。来源：最新任务卡、R07审批绑定V01/V02/V03/V05及用户已授权持续推进。产品基线为已发布5fd5bb5，合并补丁9dc8ad795d4c7d4ac84130dfad522e4f0abbeb587e3215653f7bf9ff9c5635a2。本批先准备最小可运行样例，未先改产品代码。

## 样例隔离绑定

Ruling: HTTP与bulk_workflow_approval会真实提交，沿原回滚fixture不能证明跨请求行为。用原生BackupGenerator和installer._new_site(source_sql=...)复制既有合成测试库到专用本地xgd-b19-http.localhost（新库xgd_b19_http）；沿用原Docker镜像、数据库服务、依赖和fixture。此新名字仅隔离本批持久化测试，不部署客户、不重新递归初始化依赖、不安装模块。拒绝覆盖已有站点、数据库或同名数据库用户；不force恢复、不清库。原测试/开发站点不激活Workflow，原有记录保留。代价：增加一个本地测试副本，保留到用户决定清理，不自动删除。

原生new_backup会清理历史备份，因此只复用BackupGenerator.get_backup，专用新路径，避免触及既有备份。SQL及配置/凭据只存本地private目录；不上传。基线/收口按11类业务表计数及内容哈希比较，不能外推整库每张表均不变。

准备脚本：.development/checks/b19_http_site.py。固定源xgd-test.localhost，固定目标xgd-b19-http.localhost，专用loopback端口18088。准备后先核旧库未变、目标源码与基线一致、合成普通账号身份和最小fixture，再按真实HTTP推进，不能mock commit/rollback或用顺序方法调用替代HTTP。

范围：真实身份、专用审批动作、通用Resource/submit/bulk_update/原生bulk_workflow_approval（少于20单同步路径）、未批准任务/计时/库存与间接关联、旧版本及正常审批后执行。大批量队列、完整并发、附件、批准后完整变更、手机和G1/G2/G3不据本批通过。所有新业务记录只在HTTP专用副本保留。

## 真实准备失败与限定修正

1. `clone.log`：首次 `_new_site` 调用未先 `frappe.init(new_site=True)`，目标创建前停止。确认目标不存在后，补原生初始化；显式复用已生成备份，不重备份或覆盖旧库。`clone-fixed.log`显示新站点建立、11张业务表恢复一致。
2. `setup.log`：复用fixture的 `setUp` 导入 `test_workstation`，其顶层 `make_test_records("Workstation")` 触发递归依赖初始化，遇重复Project失败。补上已有原生 `frappe.flags.skip_test_records=True`，且在导入测试模块前设置；没有修改原生依赖或安装模块。`copy-after-setup-error.log`核对这次失败后副本11张业务表未变、没有Workflow或私密fixture文件。其他表不据此宣称全库不变。`setup-fixed.log`确认6个账号及最小样例真实提交成功。这是测试准备错误，不计产品缺陷。
3. 首个计时HTTP请求得到417“未领料”，而非预期403审批拒绝。原stock fixture给第一任务配置了物料，触发原生 `validate_transfer_qty` 更早的校验。选用同一旧工单下已存在、无物料行的第二任务；只补本地fixture引用，不改数据库或放宽业务规则。从 `deny-tail` 续接，不重跑先前成功入口。修正后计时实际返回403“尚未完成审核和签批”。原失败响应保留。

Ruling: 同一专用副本保留上述失败后继续；源库与客户数据不动，不用重建库掩盖错误。原生已读字段 `_seen` 单独核对，不以忽略整张表掩盖业务变化：将唯一工单的该字段还原为原值后，11表原始哈希全部一致。

## 执行及结果

命令在项目根目录执行。凭据由原本地配置/私密fixture读取，不写入命令或公开文件。专用服务仅监听 `127.0.0.1:18088`，没有启动worker、scheduler或外部通知。

```sh
docker compose -f .development/compose.json run --rm --no-deps -T -v "$PWD/.development/private:/private" bench env/bin/python /b01/b19_http_site.py setup
docker compose -f .development/compose.json run --rm --no-deps -d --name xgd-b19-http -p 127.0.0.1:18088:8000 -e CI=1 bench bench --site xgd-b19-http.localhost serve --port 8000 --noreload
docker exec xgd-b19-http env/bin/python /b01/check_source.py /b01/b19-history-source-manifest.json
python3 .development/checks/b19_http.py fixture --output evidence/B19/http/fixture-http.json
python3 .development/checks/b19_http.py deny --output evidence/B19/http/denied-http.json
python3 .development/checks/b19_http.py deny-tail --output evidence/B19/http/denied-tail-http.json
python3 .development/checks/b19_http.py approval --output evidence/B19/http/approval-http.json
python3 .development/checks/b19_http.py execute --output evidence/B19/http/execute-http.json
python3 .development/checks/b19_http_summary.py
docker stop -s SIGINT xgd-b19-http
```

这些是本次执行记录，非允许重复执行的初始化清单；站点/fixture存在时准备脚本拒绝重复，输出文件使用排他创建。`deny-tail`仅用于本次已记录的失败续接；新样例修正后`deny`自身包含完整检查。后续不重复初始化或运行已完成阶段。

| 记录 | 实际结果 |
|---|---|
| 源码 | HTTP进程容器14个源码/元数据文件与已验manifest一致，补丁仍为本页基线；没有修改产品代码 |
| fixture 7请求 | 六个非管理员账号真实HTTP身份及草稿可读通过 |
| deny 9请求 | 前8请求符合预期；第9请求遇到上述未领料样例前置条件，保留失败 |
| deny-tail 5请求 | 只续接计时、直接/间接库存提交及必要回读；三种写入均403审批门槛拒绝 |
| approval 12请求 | 授权送审、退回改数量再送审、审核和签批成功；跨班组、自批、审核签批同账号403；旧页面417版本冲突 |
| execute 5请求 | 已批准后正常计时和仓管过账成功；读取真实持久化结果 |

合计38个实际HTTP请求；37个状态符合该次预期，另1个是已保留并修正的计时样例前置条件错误。不能写“38项业务测试全部通过”。最终场景断言通过，原始响应/快照保留本地，公开仅[结果摘要](acceptance-summary.json)及原件哈希。

- **原生批量入口：**执行的是真实 `bulk_workflow_approval` 单单同步路径，保留原生内部commit/rollback，没有mock。该入口返回HTTP200，但工单仍草稿；结合全部拒绝请求后的表/事实回读，确认未绕过审批。仅验证被拒后的rollback路径，不声称批量成功提交或20单以上队列已验。
- **拒绝副作用：**除该工单原生已读标记外，11张表哈希与拒绝前一致；目标工单、旧任务、计时、库存数量及单据无业务变化。
- **批准副作用：**数量由发起人在退回状态明确改为11；最终已批准/docstatus=1，生产状态仍Not Started。生成3张零报工、零计时的待执行任务；计时和三类库存表保持批准前原哈希，仓库仍100/0。
- **执行正例：**新增1条开始计时记录、1张docstatus=1的库存转移单；库存100/0→99/1，领料回写1，产量仍0、工单仍Not Started。本批没有正式报工，不据此宣称“首条报工开工”已验。
- **原库保留：**样例准备后及全部HTTP后，两次核对源测试库11张业务表一致、Work Order Workflow仍0；源站点未启用审批。专用副本保留Workflow及合成数据，测试Web进程已正常停止，没有清理数据库或卷。

## 收口及下一步

本批[独立审查](review.md)未发现阻塞问题；只读重算摘要断言及12份原件哈希一致，不重复业务测试。任务统计仍为34张：7完成、5部分、22未完成。

只关闭本页HTTP/同步批量拒绝子项，B19仍部分完成。下一步沿原R07/B19绑定验证批准后依据变更、终止与已有执行的停止规则，再补附件/依据还原及中文网页；不重复本批。G1数量、G2报工原记录与最小岗位、G3完整并发继续保留；未启用开发/客户流程、未接外部提醒、未开展客户验收。

公开保存只含三个测试准备/请求/摘要脚本、任务卡及脱敏摘要/源码元数据；备份、站点配置、六个账号凭据、原始HTTP与单据数据均不上传。实际推送结果另以提交后的远程核对记录为准，不能由本页提前宣称。
