> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B12 成品入库限定包执行记录

2026-10-31统一整理此前本地回执；本次收尾未重跑业务。原卡/R07为范围依据，ERPNext15.124.1基底`4e0dce9`、维护分支`codex/xgd-maintenance`，无新增字段。

- 复用原生制造入口，分别校验已报良品、显式不良、部分入库余量和取消；未新建库存账或估价机制。18个新增方法、3个受影响原方法分批有通过回执，不称全量测试通过。
- 实际命令：`docker exec -u frappe -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py <TestProductionCompletion具体方法>`；逐批命令、失败及覆盖对应保留在本地`test-commands.json`、`test-coverage.json`。
- 独立连接制造/纠错/取消竞争已执行；取消旧快照真实失败保留，修后当前读取新样例通过。原生重复提交按幂等核对流水不重复。
- 普通仓管Playwright CLI：总量4/损耗2/良品2，再总量6/损耗0/良品6；最终成品8、损耗2、消耗10。逆序取消恢复0/0/0，原报工及31表旧行保持。原生序列号预览只读，确认后才生成对应Bundle。
- 当时两容器41文件/22Python一致并编译；`node --check work_order.js`和限定`git diff --check`退出0。最终累计版本另见[A02源码清单](../A02/source-manifest.json)。

全不良/单批总量不超过剩余不良的原生零成品处理、手机、客户库存审批、完整跨卡G3、Z01未验证，整卡部分完成。旧失败、原始日志/截图/数据仅本地保留；本记录不把本次公开保存当新业务验收。
