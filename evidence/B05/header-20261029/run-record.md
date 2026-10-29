> 公开归档副本（2026-10-29）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B05字段、编号与缺资料提示有限包

## 结果和边界

按用户明确授权先补[原R07字段绑定](../../R07/card-binding.md#2026-10-29-b05字段编号与缺资料提示绑定)，再开发验收。只复用原Work Order字段/编号/日期工具和原预检，改3份原文件，无新元数据/依赖/编号器/路线平台。原34张卡不新增，只关本包子项；B05整卡仍部分完成。

- 原产品/公司/计划量/交期/计划开始/仓库等字段及MFG-WO-.YYYY.-编号直接复用；两个新号不同、保存重开同号，原主键约束拒绝同号插入。不承诺连续无断号，不改客户编号规则。
- 草稿交期可空并明确提醒；可信送审须填合法交期；交期早于计划开始只提醒可能逾期并保留原值。相同校验只供新建/有权本人草稿保存/送审消费；其他审批动作和原报工派生分支不倒追旧批准单，未重跑其旧批次。
- 原BOM预检保留权限/有效性/算法，只拆清缺工序与缺用料；前端只看当前表单值提示缺产品/BOM/交期和下一步，不另读未知资料或声称未知BOM无路线。

## 版本与环境

开工公开main实际pull为Already up to date，HEAD=e18aba7548d7d3805ddfd2729388ff94257a1b04；25份维护源码与其公开锁一致。固定ERPNext15.124.1 / 4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e、Frappe15.124.0，原checkout及全部25份累计成果保留。本包只改原work_order.py/.js/test_work_order.py；主批次累计patch=0ca3cf406d65cea5e10feafb10af277b098c08210f955ffb84143ef761c4f5c0；最终校正规则后的patch=382c6d2f0498fc0747599e4e0eab1920375484c0c267395f9b3df3967b1f35b9，主批次清单单独保留。

工具复核OpenSpec1.15.0、Playwright CLI0.1.22及原项目配置/技能存在；未安装/升级/初始化。复用xgd-b08-check、xgd-test.localhost、18090专用合成网页。只docker cp三文件、必要noreload重启及目标Work Order缓存刷新；未build/建站/reload-doc。测试和网页各33项指定文件实际匹配；不是全镜像审计，镜像tag不代表含此源码，新机器仍按锁构建和Z01验收。开发/客户审批和后台周期本轮未操作。

## 实际测试

| 动作 | 实际结果 |
|---|---|
| 初次runner尝试 | 辅助文件因写入脚本编码错误未写出，进程exit2、未运行任何方法；原red-before.log保留，不计产品失败 |
| 原源码红色 | `docker exec xgd-b08-check env/bin/python /b01/b05_header_tests.py TestWorkOrderHeader.test_00_fixture_runnable TestWorkOrderHeader.test_native_numbers_unique_persisted_and_duplicate_rejected TestWorkOrderHeader.test_draft_without_delivery_saves_but_review_is_blocked TestWorkOrderHeader.test_invalid_delivery_and_date_order_rejected TestWorkOrderHeader.test_missing_bom_and_route_are_specific_without_details`：5方法32.912秒，fixture和原生编号通过；缺交期送审未拒、零日期被接受、非法日期落SQL错误、缺路线消息不具体；初版还把早交期允许保存误设为失败，收口校正后不再把此原生行为当缺陷；合计5失败子项/1错误，非6个独立方法。原11表回滚一致 |
| 局部修补及必要原回归 | `docker exec xgd-b08-check env/bin/python /b01/b05_header_tests.py TestWorkOrderHeader TestWorkOrderApproval.test_normal_two_stage_workflow TestWorkOrderExplicitDetails.test_preview_confirm_replay`：8新＋2直接受影响原方法同批10项59.569秒，0失败/错误；原15表回滚一致（原11＋4张BOM表） |
| 原数量输入结果复用 | B04[input/save记录](../../B04/input-ui/run-record.md)已有Work Order计划量服务端输入矩阵，原before_validate仍调用同一validate_quantity_input，本包未改规则/数量输入，未重跑；不把旧BOM页面结果写成Work Order数量页面通过，不声称网页拒原始第七位 |
| 静态及源身份 | Python编译、Node --check、维护git diff --check通过；两容器`env/bin/python /b01/check_source.py /b01/b05-header-source-manifest.json`指定33文件一致 |

新增方法含编号重复、交期暂空/送审/重开/冻结、非法及倒序日期、缺BOM/路线/用料、无权及撤班组授权。缺用料仅受控清空本方法新建BOM的用料及展开行，模拟不完整来源；最终15表回滚，不删除旧业务数据。原审批fixture明确补交期并让原helper透传；显式生成fixture亦补交期，以适配新的送审条件，不表示这些类的全部旧方法已重跑。

## 真实中文PC

使用本包新普通发起人，复用原只读资料角色，不改旧岗位/配置。只新增用户1、无BOM物料1、准备好3工序/1用料但无交期草稿1；此草稿是触达交期送审门槛的受控前提，不重复验旧生成。另一张通过页面新建。

1. 打开准备草稿看到交期提醒，点击原“操作→送审→是”，真实POST417，提示送审前填预计交付日期，状态/记录未变。填2026-11-05保存，编号和原计划行ID保持，再正常送审200，重开待审核且交期保持。
2. 新建页选无BOM产品显示具体缺BOM提示；换已有无路线产品及其BOM后，不填交期可保存草稿。预览真实417，提示“BOM未维护工序路线，请先补齐BOM工序后再预览”；重开同号/同修改时间，任务/用料仍0。未点击确认生成，不重放旧报工/计时/结束。
3. [先前回读](ui-preserve.json)：原23表捕获行/列差异0；仅本包新单2（待审核1、无路线草稿1），不同原生号，Job Card/时间行/Stock Entry/Stock Ledger新增均0。

私有步骤为b05-header会话的login/show/prepared-send-fixed/new-prerequisites/resume-prerequisites脚本，原始CLI输出和截图仅本地保留。截图实际查看，不能仅凭API或内存模拟代替以上页面步骤。

### 已保留的页面停点与处理

- 首次新会话仍加载旧表单代码：函数typeof为undefined、磁盘33项已新、页面无交期提示。只清该合成站Work Order DocType缓存并完整载入后，新提示实际出现，无业务源码再改。已把这一实证同步检查补入AGENTS原验证规则。
- 首个送审脚本遗漏原“是”确认，无HTTP请求；补脚本后在同单继续，不把等待超时写成业务失败。
- 新建脚本Tab误触可选Sales Order搜索，已发生请求返回Invalid Method 404并弹窗挡保存；该用户的Sales Order read/select均false、DocType实际存在，不能说是缺模块，也未证明404完全由权限造成。关闭该弹窗后只续接同一未保存草稿，保存/预览/重开通过；不加销售权限、不扩HTTP允许范围、不重建样例。此可选搜索未通过，不据此宣称全部原生字段查询可用，不自动扩成本包任务。
- 原合成网页socket.io轮询404仍在，本包功能点击通过，不外推实时提醒或现场体验。

## 收口与未验

一次独立代码审查无发现，见review-notes.md。OpenSpec只引用原B05/R07，CLI no-tasks/blocked反映无第二清单，不表示业务失败或通过；用户和原AGENTS明确沿原34卡执行，实际步骤/结果在原卡。必要限定验收满足后只归档此change。

B05整卡、其余状态/未覆盖入口、B07全局BOM/路线历史锁、B04网页原始输入精度、全G1/G2/G3、手机/现场、Z01干净启动/备份恢复/独立接手仍未完成。GitHub CI结果未验证。本包源码/卡/可公开证据按既有授权白名单推送，公开完成以实际远端回执为准，不把本机保存当推送。


### 收口规则校正与最终验证

原生只硬校验计划结束/开始，期望交期可表示逾期安排；本包初版把交期早于计划开始硬拦截，缺少原需求依据。保留初版方案和测试证据，最终仅改此一分支为风险提示、保留原交期；非法日期、缺交期送审、原计划先后及权限/冻结均保留。原10项59.569秒绑定intermediate-suite-source.json，不冒称全部运行于最终源码。

新增`test_overdue_delivery_is_preserved_with_warning`先出现预期成功却被拒的红灯，1项6.187秒错误、15表回滚一致；红时整包中间hash未额外捕获，不强贴原10项的整体源码。修后只复验`test_invalid_delivery_and_date_order_rejected`与该新方法，2项15.321秒通过，15表一致，绑定最终source-manifest.json；11个不同方法分批验证，不宣称单次全量12项。

同一新无路线草稿填2026-10-28（计划开始2026-10-29），真实保存200、服务端风险提示实际可见；重开保留2026-10-28，编号/明细不变。未新增样例或执行事实。[最终回读](ui-preserve-final.json)仍原23表差异0，新单2、作业卡/计时/库存新增0；先前空交期保存/重开结果仍是当时实际证据，不与此次合法改期后的最终值混同。原审查者仅定向复核改动分支和说明，无权限或数据完整性问题，不重读全分支或重跑测试。

本包delta/main严格校验和Purpose/新增需求一致性校验通过，已同步主规范并归档到`openspec/changes/archive/2026-10-29-work-order-header-20261029/`；只归档已验有限包，原两项活动变更保留。公开提交/远端回读以实际回执为准。
