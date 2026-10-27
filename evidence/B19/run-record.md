> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B19｜最小审批样例与受控核验

日期：2026-10-27，Asia/Shanghai。范围：用户授权的最小样例、原生正常审批、越权/自批、直接提交、旧页面重提、旧单回填；先证据后局部修补。非整卡验收。

## 基线与隔离

- ERPNext `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，Frappe v15.124.0，沿用 `codex/xgd-maintenance`。前置 B02/B10 六文件补丁 SHA256 `221937fbf2f011d04012aa6e0a602a982d65edb5e9a72b7b53f40060322ec5d3` 保留。
- 仅使用既有 `xgd-test.localhost`，恢复 Docker 与原数据库/缓存，无重建站点、清库、客户数据导入、支付依赖安装。开发站点未启用审批。
- 先单独通过原生 Custom Field 准备 R07 已绑定的五字段，避免 Workflow 自动建字段引发 DDL 提交。`metadata-baseline.json` 核对 11 类原业务记录前后数量与内容哈希一致；没有导出原业务内容或凭据。
- 业务样例和 Workflow 在测试事务内创建并回滚，测试不删除既有 Workflow Action；测试开始时若已有 Work Order Workflow 就拒绝继续。
- 真实动作使用合成普通账号，Administrator 仅建环境资料。暂授签批角色创建原生待执行 Job Card 所需权限；不能据此宣称 G2 最小岗位已通过。

## 执行记录（持续更新）

- 首次 fixture 失败：`add_user_permission` 的参数与当前原生签名不符；读取当前签名后修正测试调用。
- 第二次 fixture 失败：原生 `get_latest_stock_qty` 要求 Item read；仅补此读取权限，未用管理员替代业务账号。
- 上述是样例准备问题，不计为审批产品缺陷；原始日志保留在本地，后续结果另记。

## 边界

G1 数量、G2 报工记录及最小岗位、G3 完整并发继续未通过。此次未验证客户现场、手机、外部提醒、完整执行旁路、批准后变更/记录删除保护。B19 保持部分执行，未达到整卡关闭条件。

## 首轮受控结果

- 最小 fixture：1/1 通过（6.167秒），之后才执行原生业务反例。
- 原生 9 项：5 通过、4 失败、0 错误（57.240秒）；失败是直接保存绕过自批、直接提交、审核/签批同人、退回重提后旧页面批准。原生失败源码清单和测试补丁单独保存。
- 首次修补回归：16/16 通过（97.513秒）；`fixed-first-results.log`、`source-fixed-first.json`。此后将手工 SQL 锁加普通重读改为原生 `get_doc(..., for_update=True)`，并把同一 Document 交给原生 Workflow，避免后续普通读取丢失锁读语义；还需最终核验，不把前次结果当最终结果。
- Ruling: 本轮只落地服务器审批核心与隔离样例，流程配置暂放在测试 fixture，不在开发或客户站点激活；原因是完整执行旁路、记录保护及网页接入未验，提前启用会形成不完整业务防线；代价是本轮不能直接用网页验收审批。
- Ruling: 沿用原维护 checkout 和本卡证据台账，不生成并行任务计划或重复全量 fixture；保留现有 B02/B10 补丁及证据，最终检查新增差异是否只涉及 Work Order 两文件。

## 最终结果与实际范围

最终代码：ERPNext基线commit不变，叠加既有B02/B10及本轮补丁；合并补丁SHA256为 `982b8a633e0596d0d8ebf7f5f3bc8d7018310ed910d2a90aec2e6710e3af9c20`。`source-final.json`证明测试容器中13个登记文件与本机清单一致；`source-manifest.json`固定最终清单。不是整个镜像或供应链审计。

- **B19最终17/17通过**（105.647秒，`final-results.log`）；首次16/16、锁读调整后的16/16都是历史中间结果，不能累计。
- **受影响的B10原有单位测试2/2通过**（5.265秒，`unit-regression.log`）。本轮修改了Work Order.validate，所以只复测此相关类；未把历史B02/B10所有结果算为本轮全量回归。
- 独立审查1项Important已按反例失败→修补→最终全组通过处理，见[审查记录](review.md)；无延后的Minor。
- 最终11类旧业务记录数量/哈希与字段准备时一致；现有2张旧工单的审批字段仍为空，持久化Workflow数量0，证明测试流程和状态回填未留在数据库。五个测试元数据字段保留。见`post-final-data-check.json`及[收口检查](closeout-check.json)。
- 本轮相对B02/B10只改 **Work Order控制器及其原有测试文件**。`b19-only.patch`为本轮增量，`combined-implementation.patch`含既有补丁；没有修改Frappe、Job Card或Stock Entry本轮逻辑，没有新建审批引擎或第三方服务。

| 卡内样例 | 真实检查和结果 | 未覆盖部分 |
|---|---|---|
| V01 正常流程 | 普通发起人→班组长→厂长逐级推进，最后docstatus=1；3张原生待执行Job Card均未生效、完成量0；无该单库存单；生产状态Not Started；3名经办人的Comment有时间、动作与依据版本 | 完整依据快照还原、Version/Comment删除保护、客户业务验收 |
| V02 权限/身份 | 跨班组、无角色、发起人自批、审核/签批同人、撤销审核角色、撤销公司授权均拒绝；新单不能伪造审核人 | 其他公司真实样例、全厂查询/待办/导出、最终最小岗位矩阵 |
| V03 直接提交 | 工单普通save改审批状态、直接submit、原生apply_workflow旁路、伪造Document.flags均被控制器阻止 | 真实HTTP/批量调用、手工Job Card/计时/库存提交与间接关联入口 |
| V04 相关分支 | 待审不能改数量或处理人；退回必须有原因；撤回/退回清除旧审核人；修改后重新审核 | 终止、批准后的取消/修订/有事实变更 |
| V05 旧版本 | 10改11后退回重提至同名“待审核”，旧modified批准被TimestampMismatchError拒绝，状态保持待审核 | 两个实际浏览器页面和完整并发竞争；本次是服务器顺序事务反例 |
| V09 旧单回填 | 流程保存及再次保存：旧草稿不批准；旧submitted进入“存量待核”；缺少服务端发起人标记的旧单不能冒充新申请；一套流程 | 部署fixture重复导入、客户旧单批准依据、历史迁移 |
| 审查补充 | 停用Workflow后清空发起人并改数量被拒绝，数据库原身份及数量保留 | 运维直接SQL/超级管理员防篡改承诺不在本轮 |

### 运行入口与复现顺序

仅在已有隔离站点执行；不要在客户数据或正在使用的审批站点复制下列命令。先读本卡及B01环境说明。准备脚本会拒绝已有Work Order Workflow。

1. `docker compose -f .development/compose.json up -d --wait db redis-cache redis-queue`
2. `docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/b19_prepare.py --prepare`：原生Custom Field准备；使用已有测试站点，禁止重新递归初始化。
3. `docker compose -f .development/compose.json build bench`：源码改变后重建；更新清单后通过`check_source.py`核验，不能只看浏览器可打开。
4. `docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b19-source-manifest.json`
5. 最小样例：以下测试命令将`--case TestWorkOrderApproval`替换为`--test test_00_fixture_runnable`（不能同时传case/test）。

```sh
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --case TestWorkOrderApproval --skip-test-records --skip-before-tests
```

6. 相关单位回归：上条命令只将case改为`TestWorkOrderStockUnits`。最后`b19_prepare.py`不带`--prepare`只读，核对前后哈希与无持久化流程。

输入：全部为代码生成的合成账号、两班组、一个公司/仓库、产品+BOM+三工序及两类旧工单；不读取客户样例。组织最小切片比R07完整V02组织矩阵小，未覆盖的公司/车间范围明列保留。测试角色获得Item read、Work Order及Job Card的read/create/write/submit；这只是原生提交需要的受控权限，不等于正式岗位最小权限方案。

### 最小修补与保留防护

1. `apply_production_approval`复用原生Workflow转换、User Permission、单据权限、Comment及原事务；新增参数只为工单、动作、已查看modified和原因。
2. 读取对象权限后使用原生`get_doc(..., for_update=True)`重读，同一Document传原生动作；再次检查改变后的对象边界，明确区分版本保护与完整并发验收。
3. 发起人由服务器确定，审核/签批分人；工单控制器不接受客户端审批flags或字段直改，未启用流程的已审批单仍依据数据库原记录保护。
4. 只用try/finally可靠清理请求内上下文，没有吞异常、默认成功、额外提交或新兼容层。正常异常沿原生事务边界处理；没有据此声称全链路故障注入通过。

### 结束点与下一步

本批指定服务器子项已有真实证据并修补，**B19仍部分完成**。下一步继续B19-V03：对未批准的Job Card创建/计时、库存提交及仅传job_card的间接入口先留反例，再复用同一审批准入做局部修补；不改数量计算、报工事实结构或全局锁序。之后再接原生中文网页和真实HTTP，其他V06～V10按原卡分项处理，不新增平行任务。

本地已保存源码、任务卡、补丁、源码清单与证据。**本轮尚未Git提交/推送**，旧远程归档不含此次R07续接/B19新增。发布授权仍沿AGENTS，但此次范围聚焦B19验证；公开保存时使用原发布白名单流程，只发布脱敏回执与合规源码，不直接复制原始运行日志、站点文件或凭据。
