> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B02 辅助读取权限执行记录

2026-10-26，执行者Codex。结论：**本轮三个辅助读取接口子项完成限定验证；B02整卡仍部分完成，G1/G2/G3保留。** 用户授权：先准备能执行的最小样例，再修辅助权限，随后处理B10单位。没有扩展到报工写链、完整岗位或AI。

## 固定对象与复用

- ERPNext v15.124.1，基线`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；Frappe v15.124.0保持原版。复用B01的`.development/repos/erpnext`维护分支`codex/xgd-maintenance`；改动尚未提交/推送，没有远程CI结论。
- 最终B02/B10合并补丁SHA256：`221937fbf2f011d04012aa6e0a602a982d65edb5e9a72b7b53f40060322ec5d3`。[补丁](../B10/combined-implementation.patch)及[13文件清单](../../.development/checks/b02-b10-source-manifest.json)固定本次对象，不覆盖B01历史清单。
- 独立测试站点`xgd-test.localhost`，中文，中国/CNY/上海时区。只用合成用户、角色、工单和草稿Job Card。R05保持停止，客户数据未接入。
- 复用原生Role/Custom DocPerm/User Permission、DocType/逐文档read、筛选解析和测试runner；不造权限引擎、不改Frappe、不安装Payment Gateway。

## 最小样例先可执行

现有`test_job_card.py`内增加`TestJobCardReadPermissions`，通过原生文档/helper创建两张工单、两道工序、两张带时间行的草稿卡。只读用户仅可见第一工单；对照用户没有业务角色。普通测试每项回滚；HTTP样例保留于测试库，最终已撤销测试读者角色。

固定runner的`--case`与`--test`不能组合（会报KeyError），Operation需原生Prompt命名输入；样例据真实接口修正。相关初始失败日志保留。`fixture-pass.log`先确认1项正常样例通过，此时尚未改产品实现。随后`red.log`实际出现跨单、无角色、撤权、日历泄露及缺filters错误，才开始修补。

采用`--skip-test-records --skip-before-tests`仅跳过无关递归fixture/hook；样例仍调用原生业务入口，断言不跳过。B01的Payment Gateway装载失败继续保留，不能把此最小样例可用写成全部上游测试已通过。

## 最终改动

仅`job_card.py`三个helper及同目录测试文件：

| 入口 | 最小改动 | 原生复用与限制 |
|---|---|---|
| `get_operation_details` | 读工序前检查源Work Order read | 保留原查询结果和过滤 |
| `get_operations` | 缺filters返回空；非对象filters给中文校验；读取前查源Work Order read | 保留搜索/分页；复用原解析与权限 |
| `get_job_details` | 原生列表产生候选，再逐文档read核对；原生筛选构造器同时处理用户条件与允许卡名 | 保留原时间聚合/输出、排除及like筛选；select不等于read，不手写权限或SQL转义 |

逐卡read不是重复同一种验证：固定Frappe的列表入口允许select；DocType read又可能由任意一张分享卡满足。实际文档read用于排除未分享的其他卡。额外读取成本未做性能验收。

## 失败反例、复核与最终验证

| 证据 | 实际结果 |
|---|---|
| `red.log`、`input-red.log` | 修前辅助读取越权及缺/非对象filters反例失败 |
| `final-tests.log` | 初轮7项通过；只是阶段结果，不代替最终版本 |
| `review-red.log` | 独立审查后新增2项：select-only和原排除筛选均先失败 |
| `review-filter-green.log` | 逐文档read、select＋单张分享、排除/like筛选2项通过 |
| `percent-red.log` | 合法筛选含`%`和引号时实际触发驱动格式化ValueError |
| `acceptance-tests.log` | **最终10项，0失败，OK，15.656秒**：上述边界全部纳入 |
| `acceptance-http-initial.json`、`acceptance-http-revoked.json` | **最终12＋4次真实HTTP均符合预期**，同一token撤权后身份仍有效、三个helper均403 |
| `acceptance-http-summary.json`、`acceptance-http-after.json` | 前后工单/卡状态、数量、时间行及库存记录数核对；无业务变化 |

独立审查发现三项均在原三个helper边界内修正：select/read混淆、排除筛选回归、内联条件与映射参数混用。最后统一沿用原生`get_filters_cond`构造条件，原查询不再二次参数格式化；审查未留下本轮对象读取子项阻塞项。

HTTP用真实原生token鉴权，含读者/无角色身份确认、授权正例、跨单403、强制查受限卡为空、空工单搜索、同token撤权。请求和响应留存且脱敏；凭据只在忽略构建/提交的`.development/private/`，0600。未更换token，未绕过后端权限。select/分享及筛选兼容由原生测试验证，不冒称也经HTTP逐项覆盖。历史16次与最终16次不叠加成当前32次。

## 可复现命令

在项目根目录、固定checkout下：

```sh
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.job_card.test_job_card --case TestJobCardReadPermissions --skip-test-records --skip-before-tests
```

仅相关源码变化需重跑HTTP时，复用既有合成fixture，不重建站点：

```sh
docker compose -f .development/compose.json run --rm --no-deps -T -v ./.development/private:/private bench env/bin/python /b01/setup_b02_http.py restore
docker compose -f .development/compose.json run --rm --no-deps -d --name xgd-b02-http -p 127.0.0.1:18087:8000 -e CI=1 bench bench --site xgd-test.localhost serve --port 8000 --noreload
python3 .development/checks/b02_http.py --phase initial --output /private/tmp/b02-new-initial.json
docker compose -f .development/compose.json run --rm --no-deps -T -v ./.development/private:/private bench env/bin/python /b01/setup_b02_http.py revoke
python3 .development/checks/b02_http.py --phase revoked --output /private/tmp/b02-new-revoked.json
docker stop --signal SIGINT xgd-b02-http
```

输出文件独占创建，复测须使用新的输出路径。当前临时18087已停止；18086开发网页保留。实际Web与Bench均通过13文件及模块路径核对，见[B10共用环境证据](../B10/run-record.md)。

## 保留事项与停止点

- B02其他制造草稿helper、任务/部门scope、岗位报工写回、导出/AI授权链、定制字段permlevel、Cookie会话、全部CASE-07未通过或未验证；后续归原卡，不在本轮补写。
- 日历原有start/end使用方式、备注SQL别名和大数据性能未改；不把本轮对象权限结果扩成完整日历验收。
- G1数量/损耗、G2逐笔报工及岗位回写、G3并发保持未满足；未有客户验收。
- 达到本轮三个helper子项结束条件，停止继续扩展权限改造。
