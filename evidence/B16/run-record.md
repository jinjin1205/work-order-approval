> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B16 同源查询、追溯与CSV限定包

2026-10-31统一整理此前本地回执；维护基底`4e0dce9`，原卡/R07为范围。仅复用原生Work Order Consumed Materials、Job Card Summary及原列表/导出，4报表文件和中文资源增量，无新API/字段/BI。

- 7种受控业务方法分批通过，非一次7/7；`docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b16_query_tests.py __main__.TestB16Query.<方法>`，各批24表回滚保持。原get_all范围、交易/库存单位、缺消耗冒0及混入计划卡反例已修；fixture错误及真实红灯保留。
- 原生HTTP及Playwright CLI普通中文PC：材料4行/逐笔报工5行CSV同源，历史生效/取消各1行、原领/退库存来源2行。工单三工序各8良/2不良，成品入库0，不把工序相加冒成品。缺实耗为空并标未记录。
- 混选父对象403、like/%/引号/!=语义检查；撤导出角色后2报告run/export与列表export共5个HTTP403。已下载文件不声称撤回。未改通用查询/权限规则。
- 最终37表旧行无丢失，但1张旧工单_seen新增本轮reader：依据原生getdoc→add_seen及只读构造去除新reader后整行hash精确匹配基线，确认其余字段保持。原保持断言失败保留，不写“37表整行全不变”。这项有字段依据的例外不能用于解释A02未知User差异。
- 两容器49文件/25Python一致并编译，2报表JS语法及diff退出0；未重复原报工/冲销/库存动作。

PreparedReport、异步邮件、历史下载、原普通Job Card模式>20条、完整CASE/G3及Z01未验证，B13～B15缺口保留。整卡部分完成，原始查询/CSV/截图/凭据仅本地，本次保存不算新验收。
