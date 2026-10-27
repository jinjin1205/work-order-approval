> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B19 通用批量入口与审批历史保护

日期：2026-10-27。基线为已远程保存的 da8e705，ERPNext 原基线及合并补丁 491dfd65b6115962465172835b85e24e5eea20167c74b8546bb110299f5d7dfd；G1/G2/G3保留。

Ruling: 原生 bulk_workflow_approval 在每单内主动 commit/rollback，原生 HTTP 又有独立连接；不能把上一批未提交 fixture 直接用于这些入口，也不通过 mock commit/rollback 伪造真实 HTTP 通过。本批先执行同卡可独立完成的 frappe.client.bulk_update 和 V08 历史修改/删除子项，复用原 fixture；实际 HTTP 与带内部提交的批量审批仍未验证，不新增站点、不激活开发/客户站点流程。代价：该两类入口仍不能宣称通过，后续须提供保留既有数据的独立持久化样例方案。

允许范围：R07第5节已绑定 Work Order 控制器、原测试文件及 ERPNext hooks 的限定 doc_events；不改 Frappe。测试先通过最小fixture，再记录原生失败；只修实际失败。测试生成的对象与动作同事务回滚，不删除既有单据。审计测试给合成普通岗位额外 Version/Work Order 修改删除权限以验证服务器保护，非正式最小岗位验收。

## 样例与原生结果

- 首次fixture因没有Version失败。固定Frappe Document._save:397在in_test时默认ignore_version；仅在送审动作期间恢复正常审计开关，finally还原。修正后1/1通过（8.209秒）。
- 第一组11项：7通过、3失败、1样例错误（82.616秒）。三失败为Version改写/删除、撤回后删除原工单；评论正例缺create权限，原评论拒绝不能据此视作保护有效。
- 合成岗位补齐Comment普通读/写/建/删权限后，仅重验受影响6项：正常fixture、普通评论、非审批Version/未送审工单正例通过；审批Comment改写/删除/改挂三反例失败（55.045秒）。没有重复已通过的批量保存3项。
- 原生页面update_comment会在确认owner及父单read后save(ignore_permissions=True)，因此还需验证这个真实入口；不依赖基础角色禁止写Comment来冒充审批历史不可改。

- 追加原生评论编辑/Version改挂：2/2预期拒绝失败（17.415秒），没有用源码推断冒充运行结果。
- 最小修补：原Work Order文件新增一个历史保护函数，原ERPNext hooks只绑定Work Order.on_trash与Comment/Version的validate/on_trash；检查原/新父单，已进入审批的原单及历史不能改写、删除或改挂。新记录追加、未送审草稿和其他业务记录沿用原权限，Frappe未改动。
- 已明确保留：附件实际文件保护、全部审批依据还原、批准后取消/修订/已有事实改需求、真实HTTP、内部commit批量审批、G1/G2/G3及整卡验收。未通过这些子项不影响已有的局部失败修补，但不能据本批关闭B19。

## 最终运行结果

- 当前14项全部通过（110.727秒，fixed-results.log），覆盖原生批量保存3项、审计样例1项、历史破坏8项及正常追加/非审批记录2项。历史不同轮次不累计。
- 原正常两级审批路径1/1通过（7.185秒，approval-regression.log）；因新增Comment/Version hooks才复测该路径，未重跑无关数量/库存/完整并发测试。
- 镜像14项源码/元数据哈希与最终清单一致；11类原业务记录数量/内容哈希与本批开始相同，旧工单审批字段仍空，持久化Workflow为0。见closeout-check.json、source-manifest.json；原始日志/数据快照只留本机。
- 当前为受控原生方法和数据库测试，不是真实HTTP或手机验收。普通岗位在测试内被额外授予相关原生编辑/删除权限；未把这些权限配置作为正式岗位设计。

复现命令：仅在既有隔离站点、无Work Order Workflow时使用；不重新初始化依赖。先构建并以 `/b01/b19-history-source-manifest.json` 运行已有 check_source.py；fixture用 `--test test_00_history_fixture_runnable`，本组用 `--case TestWorkOrderApprovalHistory`，不得同时传case/test。

```sh
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --case TestWorkOrderApprovalHistory --skip-test-records --skip-before-tests
```

后续继续原B19：真实HTTP及内部commit批量审批须先解决持久化最小样例与旧数据保留，再运行；批准后变更、附件保护及完整依据还原仍待验。不将本批Comment/Version保护冒充报工原记录或全部历史保护通过。

公开归档沿既有白名单，本批新增原hooks文件后共7个完整修改源码/测试文件，保留前批补丁；只上传脱敏结果与复现定义，原始日志、测试记录和密钥不上传。远程保存须提交后实际回读，回执另记，不以本段文字当成功证据。

独立审查未发现新增缺陷，未据此增加重测。未判断项与处理见[审查记录](review.md)。后台周期已更新为读取最新卡推进，不再重复上一批执行门槛。
