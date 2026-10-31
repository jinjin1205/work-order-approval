> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# A02明细建议与字段补全：本轮记录

2026-10-31。**确定性候选和页面流程已实现并检查；旧数据保持门槛未通过，本包及A02整卡仍部分完成。** C06待定，未调用真实模型/语音，不把配置候选称为模型识别。

## 范围与版本

- 原A02/CASE-09和`evidence/R07/card-binding.md`最后A02段为唯一范围。复用A01边界、B05～B07预览/确认及B14原生默认配置，不新建任务清单、不重跑未变化的已验项。
- 实际ERPNext15.124.1、Frappe15.124.0；维护分支`codex/xgd-maintenance`，基底`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`。
- 仅4个原文件增量：`manufacturing/production_ai.py`、`test_production_ai.py`、原`doctype/work_order/work_order.py/.js`。无新增字段/DocType/锁/默认算法/确认入口或模型平台。
- [最终源码清单](source-manifest.json)53文件含未跟踪源码、29Python，两容器匹配并编译通过。累计tracked diff SHA256：`da34b87ae13a6e8753d173d448ef04c0118dc92add599e774c450e15efcbeac8`；A02完整4文件增量SHA256：`26195a4a9fb63d85b0abc36ff71a3553feb08bca79e243762bca3ea763eea706`。tracked diff不含未跟踪文件，不能单独表示候选。
- AST只读核对A01四个原函数、原明细/授权/确认四个函数未变；原BOM失效预览与重复确认保护直接引用[B05已验记录](../B05/explicit-details-20261029/run-record.md)，不重跑。原fingerprint计算未改，source在其后追加。

## 本轮实际结果

| 项目 | 实际结果 |
|---|---|
| 字段候选 | 只允许BOM、原料/在制/成品仓库及交期5个原生字段；对象参数仅编号，不接受筛选字典/任意字段/SQL |
| 依据 | BOM取当前产品默认或已选有效BOM；在制/成品仓库取原生WorkOrder默认规则，未复制优先级；原料仓仅在全部BOM用料行来源相同且非空时建议。每项给值、来源对象版本和理由 |
| 无依据与权限 | Company/Item实际read，BOM显式read/可选默认谓词，Warehouse.read及同公司/启用/非组过滤；select不冒充read，单张分享仅授权该对象。缺配置、多/空来源、不可读或失效候选保持人工补齐，不返回假值 |
| 交期/历史 | 无本单确认的交期保持空并提示本人填写；未查询历史样本，明确history_used=False，没有“同类N单”或虚构0样本 |
| 只读与草稿边界 | 只读reader实际HTTP403；候选接口不写库。弹窗默认不勾选；实际忽略后本地三个空字段未变、明细仍0/0。接受只填仍为空的字段，不自动保存、展开或审批 |
| 本人修改/保存 | 真实普通发起人勾选BOM/来源仓/成品仓后走原保存；再用原输入框把成品仓改为另一个获准仓库并保存，仍0任务0用料 |
| 明细来源与确认 | 实际预览显示本工单及BOM的更新时间、3任务各计划10、1用料需求5；预览时仍0/0。只点击一次原确认，保存3任务/1用料，工单仍草稿，无报工或库存事实 |
| 保持检查 | 回滚测试35表保持；页面环境37表中36表原行保持，旧User有1行hash变化。完整保持未通过，详见下文，不得写成37表全通过 |

新增9种方法分批取得通过结果，**没有单次9/9的结论**。未执行A01原7项或旧B05～B19整批测试，也未运行ERPNext全量测试。

## 实际命令和结果

复用A01运行器，只选择新增A02类/方法：

```sh
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a01_boundary_tests.py erpnext.manufacturing.test_production_ai.TestProductionOrderSuggestions
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a01_boundary_tests.py erpnext.manufacturing.test_production_ai.TestProductionOrderSuggestions.test_multiple_or_empty_bom_sources_and_real_product_mismatch_stay_manual
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a01_boundary_tests.py erpnext.manufacturing.test_production_ai.TestProductionOrderSuggestions.test_native_wip_default_is_offered_without_persisting_an_order
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a02_suggestions_fixture.py prepare
python3 .development/checks/a02_suggestions_http.py prepare-order
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a02_suggestions_fixture.py audit
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a02_suggestions_fixture.py observe
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/a02_source_check.py
docker exec -w /home/frappe/frappe-bench xgd-b08-ui env/bin/python /b01/a02_source_check.py
node --check .development/repos/erpnext/erpnext/manufacturing/doctype/work_order/work_order.js
git -C .development/repos/erpnext diff --check
```

| 受限原始记录 | 实际结果 |
|---|---|
| `suggestions-red.log` | 缺候选连接、缺预览source共2失败，15.267s，35表保持 |
| `reference-types-red.log` | 1方法的3个字典引用输入未被拒，7.518s；后只在入口补明确编号校验 |
| `suggestions-final.log` | 初始6种A02方法6/6，54.062s，35表保持 |
| `review-filters.log` | 整批2方法有1个fixture错误，不能标整批通过；其中仓库不可读/停用/组/跨公司过滤方法已记录ok，35表保持，该方法未重跑 |
| `review-multiple-sources-fixed.log` | 修正新产品工厂的本公司仓库参数后，仅续跑先前阻断方法，1/1，8.414s；多/空来源和真实异产品BOM拒绝，35表保持 |
| `native-wip-default.log` | 仅新增原生在制仓默认正例，1/1，8.090s，配置在回滚站内，不改持久站；35表保持 |
| `prerequisite.log` | 新工单空明细、3项有据候选、只读403及单次HTTP耗时 |
| `ignore-ui.log` / `manual-edit.log` | 真实忽略无改动；实际输入修改后原保存成功，明细0/0 |
| `preview-plan.log` / `confirmed-plan.json` | 来源版本可见，原确认仅生成3计划任务和1用料需求5；未产生执行事实 |
| `final-observation.json` | 3任务/1用料，报工0/库存0；old_rows_unchanged=False，旧User1行变化，其余36表保持 |
| `xgd-b08-*-delivery-source.log` | 最终53文件/29Python匹配及编译通过，Node与diff检查退出0 |

原始输入、回执、截图、账号与失败日志仅留`.development/private/a02-suggestions-20261031/`，不直接公开凭据或运行数据。实际浏览器用本轮ego-browser空间5，已关闭；没有安装/升级工具。

## 保持门槛未通过

原`audit`断言真实失败：先前A01合成报工账号的User行hash变化，其余36类表捕获的原行均missing=0/changed=0。不是“全部旧记录保持”。

原基线只有行hash，没有字段原值，无法据此确认具体字段和原因；**字段差异、原因均未验证**。没有猜成登录时间等变化，没有恢复旧User、覆盖原基线或放宽原断言。只读`observe`明确返回False并采集其余结果，不能代替保持通过。原始失败保留，A02整体验收/整卡不关闭；后续不得靠重复正常测试抹掉此差异。

## 审查、工具失败与测量限制

- 一次最终只读审查未定位产品逻辑缺陷，P2为本轮新过滤分支缺证据。只补上述新增真实方法，不增加产品防护或第二次派审查；没有Minor产品建议。
- 新增测试的产品工厂漏传仓库，原生拒绝外公司默认仓；只修fixture并续接未运行部分，保留首次错误。
- 浏览器首次等待全部checkbox因多匹配失败，直接读取已经打开的弹窗，没有重发请求。应用建议脚本的即时断言未通过且未保存当时中间值，具体原因未验证；随后只读表单及原保存回执显示建议值正确保存。保留失败，不将该命令写成通过；人工改值和最终原确认另有实际回执。
- 单次候选HTTP **69.459ms**；明细预览已有浏览器ResourceTiming **149.1ms**。自动化点击到观察可见耗时 **3236ms**，包含工具动作/等待，不能当纯服务器耗时。仅消费既有资源时间，没有重发测性能；**人工2秒体验及SLA未验证**，不因接口较快而宣称达标。

## 保留项和保存状态

- C06待定，真实模型/语音、真实模型候选正确性、费用和真实AI端到端耗时未验证。未知费用不记0；本包仅配置候选和确定性明细。
- B19实发、B18真实现场、真机、此前B14/B15等未验证项及完整G1/G2/G3、Z01保持原状态。没有启用客户流程或做客户部署。
- 原33份AGENTS/TODO/决策/任务卡/OpenSpec文件hash未变；没有改任务勾选、更新TODO/交接、commit/push/PR。本轮无提交SHA或CI结果，公开checkout未同步。
