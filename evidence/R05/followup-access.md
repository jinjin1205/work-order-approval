> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R05 补证：普通权限、并发与原事实保护

2026-10-26。**本轮有限补证已执行；没有修改产品代码，也不代表完整 CASE-04/05/07 或 R05 整卡通过。** 准备记录在前，实际结果在后。主要差异：白名单辅助接口泄露受限工序子行；默认制造角色可写库存草稿、可删除已取消作业卡；同卡合法双增量未同时保留；不同卡并发出现一次死锁，随后一次显式恢复成功。

## 范围与版本

- R05 卡；R02 fixture/expected-results v1 的 CASE-04 I01/I03/I04、CASE-05 普通改删保护、CASE-07 有限普通角色/对象权限。
- 既有隔离站点 `r05.localhost`；官方 ARM64 镜像固定 `sha256:4160d3c77aafb41c7770aad3daa67254a13f8750765ee83d632434ed564a4834`。ERPNext 15.124.1 / Frappe 15.124.0 的环境身份沿用主记录。
- 只新增 `R05F-A` 合成样例、测试用户与原生 User Permission，不改产品代码、不修改已有证据或既有合成业务事实。
- 探针源码：[access_setup.py](../../.evaluation/r05-erpnext/probes/access_setup.py)、[access_http.py](../../.evaluation/r05-erpnext/probes/access_http.py)。凭证写 `sites/r05f-access-secrets.json`，权限 0600，禁止进入本证据目录或输出到日志。

## 已实际读取的原生入口

准备阶段用 `docker compose ... run --rm --no-deps -T bench bash -lc 'sed ...'` 只读镜像文件，未连接数据库。实际写入发生在下述单独授权、顺序执行阶段。

| 原生位置 | 静态观察与含义 |
|---|---|
| `frappe/api/v1.py` 的 `document_list/read_doc/update_doc/delete_doc` | 列表经过 `frappe.client.get_list`；单条 GET 检查 read；PUT 加载 `for_update=True` 后 save；DELETE 走 `frappe.delete_doc`。普通账户将实际调用这些入口。 |
| `frappe/client.py` 的 `get_list/submit/cancel` | 列表使用有权限约束的 `get_list`；提交与取消沿 Document 原生状态及权限入口。 |
| `frappe/model/document.py:400–420,852–886,1163–1177` | save 检查 write；最新版本检查读取待保存文档并持行锁，比对 modified。保护文档版本不等于业务请求身份和结果找回。 |
| `erpnext/manufacturing/doctype/job_card/job_card.py:515–562,1117–1125` | `make_time_log` 获取 Job Card 后调用 `add_time_log`，最终 save 检查写权限；complete 更新未结束时间行，start 追加时间行，没有已读到的请求标识字段。 |
| 同文件 `get_operation_details`（紧随 make_time_log） | 白名单辅助方法直接 `get_all("Work Order Operation")`，本函数没有 read 检查。拟用真实无角色/无对象权限请求核验，静态发现不能代替运行结论。 |
| `job_card.json`、`stock_entry.json` permissions | Manufacturing User 对 Job Card 有 read/write/submit/cancel/delete/amend，并也具备 Stock Entry 写/提交等权限；不能直接当本项目“只报工、不能过账”的最小操作工角色。 |
| `frappe/model/delete_doc.py:120–184` | 删除检查权限和非 submitted 状态，取消单可继续进入链接检查、删除及 Deleted Document 留存路径；后者不能当原业务记录仍存在。 |

## 审查后的执行设计

1. 原生 User Permission 按 Work Order 配置 ALL、DEPT、PERSON、对照 B；用户 a/b/outside 为 Manufacturing User、stock 为 Stock User、none 无业务角色。ALL/DEPT/PERSON 只是合成标签，按对象显式授权能否通过将实测；部门归属或人员指派的自动映射不在本轮实现，仍未验证。
2. 普通账户实际 GET、列表、PUT、DELETE 和 make_time_log；保存成功/拒绝原始响应。另核 get_operation_details 是否泄露受限工序子行。普通权限结论绝不使用管理员 `get_all` 代替。
3. 三个独立并发样例：原生生效卡 8 ＋同工单待提交卡 2；a/b 对同待提交卡各报 2 时并发 submit，各报 1 时先并发 save、回读后再按原生 UI 流程 submit（保存会自动算损耗，避免把直接 submit 的“数量 1／批量 2／损耗 0”无效输入误当并发失败）。另建 SPLIT1：生效卡 8 ＋两张各批量 1 的新卡，a/b 分别并发提交，以观察两笔各自合法增量。线程屏障同时发真实 HTTP，记录独立请求标签、发送/响应时间、两个区间重叠毫秒、返回及新请求回读的明细/汇总。保留原生自动损耗规则，区分其语义与本项目两笔报工。
4. 独立 retry 样例：原生计时 start 一次、同 complete 请求两次，再同 submit 请求两次；记录每阶段文档与生效量。标签不被冒称原生业务幂等键。
5. 独立 DELETE 样例：普通账户尝试修改/删除 submitted10，再普通 cancel、删除 cancelled，并回读；已保留提交前与取消后快照。只作用于本轮专属新夹具。
6. UI 专属样例另建，添加最小合成 Employee、与 a 关联并预分配到 UI 作业卡；时间行仍为空，留给主代理浏览器操作。已读 `job_card.js:296–405`：Start Job 无员工时弹选择框，已分配则直接调用计时入口；Complete Job 传完成时间及数量。Employee 原生钩子会给 a 添加 Employee 角色，报告记录实际角色；该角色不能被省略成“仅 Manufacturing User”。

没有执行提交后丢响应或提交前故障注入，本轮 I05/I06 **未验证**；没有导出、AI取数、全部权限面或跨卡超报结论。

## 准备检查

- `ast.parse` 两份探针通过，仅证明 Python 语法可解析。
- 首次 `python3 -m py_compile` 被宿主默认缓存目录写权限拒绝，未执行业务代码；改为不写缓存的语法解析。没有把语法检查称为业务通过。
- 交接前核对：7份有效JSON可解析且无探针异常字段，3份探针语法可解析；三组请求区间均真实重叠；12个本页本地链接可定位；用测试凭证值作本地比对，专属原始证据/日志未发现密码或API key/secret。业务拒绝、死锁和首次只读保存失败仍按实际保留。

## 实际执行与环境

- Setup：2026-10-26 10:47:50～10:47:57 UTC（北京时间 18:47:50～18:47:57）；原生夹具与账号提交成功，制造设置恢复检查为 true。完整初始化（仅本地保留；见 publication/evidence-index.json）、日志（仅本地保留；见 publication/evidence-index.json）。
- 普通 HTTP：10:48:32～10:49:28 UTC；access 56 次、concurrency 53 次、retry 27 次、delete 17 次请求（含只读回读），四节均没有探针执行异常。业务接口拒绝与死锁原样保留，不能因脚本无异常就视为业务通过。
- 10:51 左右补一次 SPLIT1 显式恢复，单独记录 12 次请求（含前后回读），不覆盖原并发结果。恢复证据（仅本地保留；见 publication/evidence-index.json）。
- 站点保留原配置；新连接只读确认时区 `America/New_York`、数量精度3、Banker's Rounding。本次时间行为本机生成的合成墙上时间，未改为 R02 固定 Asia/Shanghai 日期，**不用于 CASE-03 工时判定**。并发证据使用带 UTC 偏移的发送/响应时间及同一客户端单调时钟，区间可比较。
- 实际命令：`docker compose -f .evaluation/r05-erpnext/compose.json run --rm --no-deps -T bench bench --site r05.localhost console`，控制台执行 `exec(open('/eval/access_setup.py').read(), {})`；随后宿主 `python3 .evaluation/r05-erpnext/probes/access_http.py --setup evidence/R05/followup/access-setup.json --secrets .evaluation/r05-erpnext/access-secrets.json --section <access|concurrency|retry|delete|recovery> --output evidence/R05/followup/<独占结果>.json`。Web 入口为仅本机 `http://127.0.0.1:18085`，Host 为 r05.localhost。
- 密码/API key/secret 只保存在站点及 `.evaluation/r05-erpnext/access-secrets.json` 的0600文件，不进入本报告或原始证据。

## 普通角色与对象权限实际结果

全部原始 HTTP 输入、响应与身份（仅本地保留；见 publication/evidence-index.json）。a 为 Manufacturing User＋关联员工自动得到的 Employee；b/outside 为 Manufacturing User；stock 为 Stock User；none 无业务角色。身份接口均200并返回对应测试用户；没有使用管理员API代替普通权限检查。

| 范围 | 实际结果 | 判定与限制 |
|---|---|---|
| ALL / DEPT / PERSON / B 的 Job Card GET 与列表 | a 可读 ALL/DEPT/PERSON；b 可读 ALL/DEPT；outside 可读 ALL/B；其余单条403。列表各自只返回相应集合。none 四个单条与列表均403。 | **该显式对象授权子集通过**。原生 User Permission 可用；只是手工 Work Order 白名单，未证明部门/指派动态策略已经实现。 |
| Job Card 普通写/删与 make_time_log | a 写DEPT与开始计时均200；a写B、outside写DEPT、none写DEPT均403；三个无权删除均403；a对B及none对DEPT的计时均403。 | 受测入口拒绝无权对象；DEPT仅新增本轮授权计时草稿，B回读无时间行。 |
| Stock User 同类对象 | stock读DEPT已提交Stock Entry、写其草稿均200；对B读/写均403；none均403。 | 原生库存角色＋对象权限子集可配置使用；没有仓库范围/实际过账授权结论。 |
| 默认 Manufacturing User 库存权限 | a读DEPT库存单、写DEPT库存草稿均200。 | **不能直接作为本项目只报工操作工**；需配置最小角色收窄。该运行只证明库存草稿写，实际库存过账未测。 |
| 白名单 `get_operation_details` | a调用无权B，以及none调用DEPT，均200并返回对应受限 Work Order Operation 的 `name` 和 `idx`，与授权正例相同。 | **有限泄露已复现**。资源GET拒绝并不覆盖此辅助方法；本轮只测该方法，不声称完整权限审计。 |

## 真实并发与重试

并发原始请求/区间/持久化回读（仅本地保留；见 publication/evidence-index.json）。每组起点均为工单计划10、原生已提交卡8；两个独立账户通过线程屏障发请求。下面的重叠是客户端请求在途区间，不声称精确的数据库锁持有区间。

| 分支 / 请求标识 | 区间重叠 | 实际响应和回读 | 相对 R02 判据 |
|---|---:|---|---|
| CONC2-a / CONC2-b：同一待提交卡2，各填2并发submit | 140.726 ms | 200 / 417 TimestampMismatchError；净新增2，有效10，损耗0，工序Completed。 | **本次 I03 同卡限额结果通过**；冲突来自同文档版本，不能外推跨卡限额或请求级幂等。 |
| CONC1-a / CONC1-b：同一待提交卡2，各填1并发save，再submit当前版本 | 48.210 ms | 200 / 417 TimestampMismatchError；只保留一笔1；普通后续submit后有效9、自动损耗1、工序Completed。 | **I04 目标失败**：两笔合法增量没有同时保留；自动损耗也不能冒充确认不良。原生需要处理版本冲突，不能把第二笔当已经成功。 |
| SPLIT1-a / SPLIT1-b：同工单、两张各批量1卡，并发submit | 127.647 ms | 200 / 500 QueryDeadlockError；有效9、损耗0，失败卡仍draft且无时间行。 | **本次并发双生效失败**。这是一次死锁观察，不给发生率或全局稳定性结论。 |

SPLIT1 死锁堆栈经过 `JobCard.set_status → update_status_in_workstation → frappe.db.set_value("Workstation", …)`。按主代理明确要求先查失败卡仍未提交且有效总量9，再使用同一张卡的当前版本、原数量1和新恢复标签 `SPLIT1-b-recovery1` 提交一次：200，最终有效10/损耗0、工序Completed。**这是独立的顺序恢复成功，不是原始并发通过**；没有自动循环或重跑并发。

重复请求原始证据（仅本地保留；见 publication/evidence-index.json）：原生 start 后，同 `complete` 载荷/标签 `R05F-K-01` 两次均200且返回 `{}`；一条时间行保持完成1，仍是draft，工单有效量仍8。第一次完整卡 submit 后有效量9、自动损耗1；相同原始 submit 载荷重试返回417 TimestampMismatchError，量未增加。**数量未重复这部分有证据，但没有业务请求结果找回，不能记 I01 完整通过。** I05丢响应、I06受控提交前失败均未验证；实际死锁回滚只是该分支观察，不能替代故障注入全判据。

## 已生效事实保护与取消后删除

普通用户原始请求（仅本地保留；见 publication/evidence-index.json），只操作本轮独立 `R05F-A-DELETE`／工单 `[本地样例编号已移除]`／卡 `[本地样例编号已移除]`，原始时间行完成10且没有下游制造。

- submitted 时间行完成量改10→8返回417 `UpdateAfterSubmitError`；直接DELETE返回417。回读仍docstatus1、数量10。
- 同一普通a用户 cancel 返回200，回读原卡docstatus2、时间行仍10、有效量0。
- 再普通DELETE返回202，后续普通GET返回404，Job Card列表为空。
- 新连接只读回读（仅本地保留；见 publication/evidence-index.json）确认原Job Card不存在、原时间子行数0；`Deleted Document`保留一份取消态JSON及一条时间行，owner为执行删除的a，restored=0。**审计留存存在，但原业务记录确被删除，因此“取消后原事实不可普通删除”不满足。** 没有实际恢复 Deleted Document，不能声称已验证可恢复。

只读回读首次因控制台相对路径及分散命名空间而保存失败，保留 失败日志（仅本地保留；见 publication/evidence-index.json） 和当时空输出；改用 [绝对路径独立脚本](../../.evaluation/r05-erpnext/probes/access_readback.py) 后成功，未重新执行业务动作。

## 最小适配边界与停止

1. **直接复用／配置：**保留 Resource API、Role/User Permission、Document 状态/版本锁和库存原生入口；以最小岗位角色收窄默认 Manufacturing User 的库存、cancel/delete等授权。对象白名单已有运行依据；部门/人员关系映射仍须后续绑定。
2. **局部改造候选：**对已复现的白名单辅助读取补同对象权限检查；正式报工与已取消原事实的保留规则需覆盖删除入口，不能只依赖 submitted 保护或 Deleted Document。
3. **请求与并发：**保留现有事务/锁，增加业务请求身份及结果找回的最小适配；在正常入口处理可恢复文档冲突/死锁并在重试前查现状。需要核锁顺序和回写边界，不能承诺“加自动重试即可”或新建第二套库存/生产账。
4. **语义差异：**原生全卡完成、自动损耗、时间行草稿不是本项目逐笔人确认报工；有效9＋自动loss1导致Completed已实测，须与明确良/不良、逐笔冲销设计一起评估，不能仅调整显示。

本轮到上述核心差异与证据明确即停止。没有导出、AI、全权限面、跨卡各报2超限、负载压力、成功后断响应、客户部署或手机结论；UI独立夹具由主代理另测。本报告不启动 R06/R07 或任何 B/A/Z 实施卡。
