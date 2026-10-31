> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B11 退料生成与净领料：执行记录

2026-10-31。本包实现与限定验收完成，代码1eb562a已推送回读，精确SHA无CI配置/触发；B11整卡仍部分，完整G3及客户库存审批未验。下一步沿原B12先补R07，不重复本包。

## 范围与版本

唯一任务为原B11四条，先读并补R07 quantity-return.md；不复制计划。开工公开main=origin/main `517027e71e2f808d40c6fd47cfe00521503cd0a5`，维护codex/xgd-maintenance，ERPNext15.124.1上游4e0dce9、Frappe15.124.0 f1cf50。最终累计补丁`906010f517f003af5311be474ec0927184690d392c31cd5a864b0581455f4e51`，3个本轮源码/测试文件、33个累计维护文件；测试和网页容器41文件匹配、22 Python编译通过。

复用已安装OpenSpec1.15.0、Playwright CLI0.1.22、Superpowers；按现有执行/验证/独立审查流程完成。仅修改work_order.py原生成器、stock_entry.py原分配/校验/锁入口及test_stock_entry.py，不新增字段/DocType、不改Frappe、库存账/估价核心、财务、AI或新页面按钮。B10 fixture仅参数化前缀/场景/草稿开关，默认不变；原审计/并发辅助复用。

## 实际实现与验收

- 原生生成器校验工单read、库存单create及执行准入，带公司和against_stock_entry/ste_detail；库存单位读取原transfer_qty，按物料/WIP及原行共同限额。领10退2再次生成8；实际耗7后只生成1。仓内另有库存也不能抬高本单可退量。零余额、历史缺引用均明确提示。
- 原生部分/多次退料、重复提交、跨已批准工单、错误原单、缺引用、拆行超额、交易单位一次换算、无权与撤权均有分批通过证据。源单有退料/耗料依赖的取消被拒绝；受控过账后期异常回滚，无部分库存或汇总残留。
- 退料与耗料读取同一原生事实余额；parent-before-entry锁移至原StockEntry.check_if_latest父类调用前，取消只从保存原单取工单，版本/权限/原单完整性检查保留。真实反向锁序红测QueryDeadlockError已留存；新草稿绿测先等父锁，再正常拒绝有依赖的取消、完成合法退料，无重试。
- 双追踪物料两笔各领2、第一来源耗1：两种原生批序号模式均生成[1,2]、分别关联原行并实际提交，累计领4/退3/耗1/WIP0。按实际剩余序列与批共同分配，旧字段模式明确填写所选序列，不自动重复选取。
- 3条已确认报工（含子行）和原领料整份文档，在新退料提交及取消前后完全一致；旧23表事务回滚保持。持久样例31表开工前旧行均未改/删，新增样例不混入旧行基线。

### 普通仓管PC与实际库存

Playwright CLI真实登录新普通仓管；已登录身份调用make_stock_return_entry生成草稿（接口证据），原生Stock Entry页面改数量2、保存、提交、取消（页面证据）。没有把此调用说成进行中Work Order上已有按钮。

| 动作 | 来源仓量/值 | WIP量/值 | 累计领/退/净领/实耗 | 退单状态 |
|---|---|---|---|---|
| 草稿保存 | 10/30 | 10/30 | 10/0/10/0 | 0，无流水 |
| 提交退2 | 12/36 | 8/24 | 10/2/8/0 | 1，2流水 |
| 原生取消 | 10/30 | 10/30 | 10/0/10/0 | 2，4正反流水，原单保留 |

私有浏览器日志/截图、前后DB审计留本机；公开只存无单据编号摘要。隔离站socket.io 404及moment日期警告保留，未修也未宣称控制台无错误；不影响上述已回读事实，不代表实时通知服务通过。

### 真实竞争

- 退退：原首次5+5被测试脚本同时保存全局设置干扰，B报TimestampMismatchError，此次不算数量并发通过；保留原单。新增两张各2草稿争剩3，一成一额度拒绝，累计退9/净1，失败单无流水。
- 退耗：已退2后，退5与耗5争剩8，退5生效、耗5余额拒绝，领10/退7/耗0/净3，3条前置报工仍在。
- 原领料取消先完成与退5竞争：取消先持工单锁，退料等待，随后原单失效而拒绝；领0/退0、来源20/WIP0，取消保留逆向流水。
- 另一锁交错：锁红测实见取消持原单→退持工单→死锁；修后取消先持工单，退等待。取消因现存退料依赖/库存不足正常拒绝，合法退1生效。红/绿结果并列保留，不覆盖历史。

前两类初次观察到原生Stock Entry锁等待，第三及锁修复观察到Work Order等待；不杜撰全部等待都发生在父锁。所有业务提交为独立真实DB连接，REPEATABLE-READ，控制器只设测试调度门，不替换业务规则。

## 实际命令、失败与复测

各批真实方法、stdout SHA256、运行秒数、失败/错误数见[test-batches.json](test-batches.json)。21个新增方法和9个直接受影响原方法各自已有通过记录，共30不同方法；这是分批结果，不是一次最终全量通过。中间补丁未捕获则明确null；最后3项绑定最终清单。无关U01/B05～B09未重跑。

测试命令统一为`docker exec -u frappe -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py <回执列出的实际方法或类>`。最后一批实际参数：`erpnext.stock.doctype.stock_entry.test_stock_entry.TestProductionMaterialReturnSerial erpnext.stock.doctype.stock_entry.test_stock_entry.TestProductionMaterialReturn.test_return_and_cancel_preserve_confirmed_reports_and_issue`。

| 批次（本地log） | 项数 | 实际结果 | 秒 | 回滚保持表数 |
|---|---:|---|---:|---:|
| p0 | 1 | OK；失败0/错误0 | 9.261 | 23 |
| return-red | 7 | FAILED；失败6/错误1 | 56.965 | 23 |
| return-green | 8 | FAILED；失败0/错误1 | 73.169 | 23 |
| consumption-red | 5 | FAILED；失败1/错误0 | 50.798 | 23 |
| consumption-green | 2 | OK；失败0/错误0 | 20.220 | 23 |
| shared-native | 6 | FAILED；失败0/错误6 | 0.184 | 15 |
| remaining-checks | 7 | OK；失败0/错误0 | 59.146 | 23 |
| shared-native-fixture | 6 | OK；失败0/错误0 | 4.882 | 15 |
| serial-review-red | 1 | FAILED；失败1/错误0 | 10.155 | 23 |
| review-green | 7 | OK；失败0/错误0 | 62.059 | 23 |
| serial-native-red | 1 | FAILED；失败0/错误1 | 0.748 | 23 |
| serial-native-fixture-red | 1 | FAILED；失败0/错误1 | 0.798 | 23 |
| serial-native-green | 2 | FAILED；失败0/错误1 | 9.310 | 23 |
| serial-native-diagnostic | 1 | FAILED；失败0/错误1 | 1.751 | 23 |
| serial-final-reports | 3 | OK；失败0/错误0 | 17.426 | 23 |

错误归因：早期取消测试沿用旧内存单据，被既有原单保护拒绝；改成真实原生重读再取消。shared-native六项因缺Products前置未运行目标路径，仅补最小Item Group后六项通过。serial-native-red缺from_bom/bom前置；fixture-red真实暴露旧函数过滤在库序列；后续green仍有旧字段模式漏明确序列而重复选择，diagnostic保留失败并定位，最后双模式通过。独立审查发现均已复现、修复并复核，无遗留Important/Critical（仅本范围）。

持久样例命令：`/b01/b11_return_fixture.py prepare`一次；`/b01/b11_return_race.py <race-return/race-return-remaining/race-consume/race-cancel> run`；`/b01/b11_lock_order_race.py <lock-red/lock-green> run`；`/b01/b11_return_fixture.py audit`，均由`docker exec -u frappe -w /home/frappe/frappe-bench xgd-b08-check env/bin/python`执行。两个容器分别执行`/b01/b11_source_check.py`：41文件/22编译通过。无故障自动重试、无旧单重放。

`openspec validate b08-followup-20261028 --strict --json`实际exit1：引用模式0任务warning；按用户要求沿原卡，不复制第二清单，不归档整卡、不写OpenSpec严格通过。

## 仍未做或未验证

进行中工单退料按钮、手机/PDA入口属B13；客户Stock Entry审批未接入，草稿不是待批，不宣称待批量验收。B12成品/不良/制造耗料组合、全跨卡G3及合法替代料完整链、客户现场验收、Z01干净部署/备份恢复/独立接手仍未验证。B11本包达到停止点，后续按原B12补绑，不用这些跨卡事项重复开发B11。

## 公开保存

仅推公开白名单源码、原任务卡/文档和脱敏摘要；原始单据、账号口令、日志、截图与数据库私有。代码[`1eb562a`](https://github.com/jinjin1205/work-order-approval/commit/1eb562a083da7f9d5bccf2109e60794904f49af1)已推main；[新克隆回读](../../发布/2026-10-31-1eb562a-remote.json)646文件/645内容哈希、33累计源码一致，零缺失/额外/哈希差异。[精确SHA CI查询](code-ci.json)0workflow/运行/check/status且无查询错误，未配置/未触发，非通过；无运行链接，[Actions入口](https://github.com/jinjin1205/work-order-approval/actions)。最终文档提交和CI只在最终回复报告，不循环回填。维护源码仓33份累计未提交差异均按源锁公开保存；不向上游推送、不冒充维护仓干净。
