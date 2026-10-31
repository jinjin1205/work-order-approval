> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B15 原生计划来源与Project软引用限定包

2026-10-31，用户明确激活原B15；维护分支`codex/xgd-maintenance`，基底`4e0dce9`。原卡/R07为唯一范围，无新增字段/MRP/排产/子装配能力。

- 3原文件增量：Production Plan控制器/页面、Work Order来源保护；计划提交后逐行预览、人工确认生成空草稿，来源不可伪造/移除，Project仅在既有可编辑空草稿调整/解绑。原B05明细及审批入口复用。
- `docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b15_plan_tests.py <具体方法>`：6个不同业务方法分批通过，另1最小fixture；取消同源修订真实红测后修补并复验2项。24表回滚保持，首批fixture及旧版本比较错误保留。
- Playwright CLI普通用户真实预览/确认、补仓库、删除未编辑空行后保存、Project解绑重开、同计划行重试仍同空草稿；不把过程中必填/空行拒绝记为通过，也不猜空行成因。
- `python3 .development/checks/b15_plan_concurrency_http.py`原并发旧快照404保留；改原get_doc当前读取后新样例两重叠HTTP均成功，仅1张创建/1次复用。权限HTTP修正测试密码准备后，撤角色仅保留单张read的两入口均403；原401未算权限通过。
- 最终39表旧行missing/changed均0，4行对应4张空草稿，无报工/库存、新Custom Field为0。两容器45文件/23Python匹配编译，JS/diff检查退出0。

纯只读者预览按钮仍可见但服务端拒绝，保留Minor。完整岗位页面矩阵、浏览器取消修订、完整并发、独立接手及Z01未验证；B13/B14旧缺口保留。整卡部分完成，原日志/运行数据仅本地，本次收尾未重跑业务。
