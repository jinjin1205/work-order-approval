# B01 独立中文开发环境

**2026-10-28今日暂停与下次续接：**先读[TODO最新暂停入口](../docs/开发TODO.md)和[暂停与保存记录](../evidence/维护/2026-10-28-暂停与保存.md)。明天由用户手动发起续接，后台任务`b19`保持`PAUSED`，不自动恢复或新建明日任务。已删除25个有完整远端副本的临时核验克隆（136.40 MiB）；构建缓存、镜像和数据库保留；维护源码、发布主仓、现有站点/数据、原始证据和样例继续保留，不为暂停重建数据库。

**2026-10-28最新验证：I05提交丢响应、I06更正中途回滚。**[本包记录](../evidence/B08/recovery-20261028/run-record.md)及[公开回执](../evidence/发布/2026-10-28-83aaf4e-remote.json)已有限收口。I05一次确认POST后，独立新DB连接观察提交可见，代理下行0字节断连，再凭原键一次GET查回同卡/快照；仅新增1事实/1时间行，HTTP站20表旧行保留。I06真实DB受控故障在旧卡cancel、新卡insert后命中，显式savepoint回滚恢复，再同键10→8；1项测试12.142秒，runner共12.409324秒，源站20表最终恢复。无产品修改、build、重启或旧回归重跑，25份维护源码及33份运行清单保持原补丁。I06不等于HTTP自动回滚，两样例未验证非零成本；整卡、G1/G2/G3、现场/手机和Z01不关闭，已通过且未变化的样例不重放。

**GitHub拉取与本机环境：**公开归档已保存25份完整修改源码、`source/source-lock.json`固定上游锁、`tools/prepare_source.py`、文档和可公开证据。`git pull`只更新归档仓受跟踪文件，不自动覆盖被忽略的`.development/repos/erpnext`维护checkout，也不更新容器或数据库。本机下次续接复用现有数据、核对源码差异后按原卡同步；新clone可用恢复脚本准备固定源码，但目标目录已存在时脚本会停止，不能拿它覆盖旧修改。新机器仍需私有配置/数据备份及Z01对应验证，准备源码成功不等于干净环境或独立接手通过。

本次另补充归档项目技能（含`references`及`.openspec-target`）、发布辅助脚本和许可证，供审阅与复用定义；提交/回读状态以暂停记录为准。发布脚本依赖本地原始证据与凭据排除清单，不承诺新clone直接发布，也不随归档上传本机数据或凭据。工具/技能已可用时直接复用，不重复安装或初始化。

**2026-10-28前一验证：B08-04/B09不同请求并发余量。**沿原I03/I04，两名窄角色用户、独立HTTP连接、不同键，在两个新任务分别验证余2各报2仅一笔成功、余2各报1两笔成功。两场景实际各运行一次，4次确认3成功1明确冲突，20表旧行/捕获列保持。没有产品源码改动、镜像重建或服务重启，当前源码仍为下述history-paths补丁；[实际命令及限制](../evidence/B08/distinct-concurrency-20261028/run-record.md)保留完整G1/G2/G3、现场和Z01边界。

**2026-10-28当前源码：B08-06/B09原记录旁路。**本轮仅改原Work Order Operation控制器及原Job Card测试两个文件：工序行存在已生效或已取消Job Card引用时，禁止直接保存改写/改挂或删除，不依赖是否填写计价配置。累计源码仍为25份（17份上游派生、8份新增）；当前[运行记录](../evidence/B08/history-paths-20261028/run-record.md)及[补丁](../evidence/B08/history-paths-20261028/implementation.patch)单独留证。

5个新增测试方法分批取得通过结果：首批修后3项通过、1项草稿夹具顺序错误；只调整删除顺序后的草稿正例1项9.731秒通过，取消态唯一引用1项10.351秒通过。取消态样例由受控服务器上下文调用原生cancel建立，不表示开放客户端独立取消。真实删除/改挂红色失败及夹具失败保留；没有一次全量suite通过结论。独立实际HTTP共13个不同写入请求：7个历史/状态拒绝、6个无事实草稿正例通过，写入未重复；各批脚本停止及修正保留，最终旧11张业务表和5张安全配置表的原行/捕获列未变。完整G2/G3、父删除/复制、后台、现场和Z01未验范围保持。

本轮没有元数据变化，无新增reload-doc要求；在已加载前包元数据的专用站上同步新源码并重启Web，测试、构建及网页各33项运行文件与清单一致。不能把旧容器或原站点未迁移的元数据当作本轮运行环境。以下计价包成果和首次部署要求按原批次保留，不重复执行已完成迁移。

**2026-10-28前包：B08计价与效率。**工单发起人在草稿/退回的原工序行填写计价方式、工资单价和标准效率，币种来自公司默认币种，随送审冻结。普通报工预览、确认及重开复用C13公式和服务器来源快照；预计工资不是工资结算，旧记录无依据不回填。直接子行保存绕过价格校验/冻结的实证问题已修补，范围只限新增计价来源。该批分批测试、真实中文PC证据见[计价包记录](../evidence/B08/metrics-20261028/run-record.md)和[当时补丁](../evidence/B08/metrics-20261028/implementation.patch)。该批测试与网页容器各33项运行文件与清单一致；这不代表完整镜像或客户环境验收。

本包服务端新增场景及5项受影响原回归分批通过，UI受控6项通过；真实中文PC已核小时20.00/实际效率5/达标50%，计件数量改变时80.00→60.00→80.00，确认后重开读到保存依据，旧笔显示历史未记录。发起人原生工序表填写、保存、重开及中文计时/计件选项另有页面证据。首次夹具失败和子行漏洞红色样例保留，不累计为一次全量suite通过；现场、手机、G1/G2/G3及Z01仍未通过。

首次加载计价包元数据的授权本地站，须用对应新源码环境执行原生元数据加载和缓存清理；已有相同元数据的站点不因本轮history-paths补丁重复迁移。以下是首次部署步骤模板，不是客户验收命令或本次新执行记录：

```sh
bench --site <已授权站点> reload-doc manufacturing doctype work_order_operation
bench --site <已授权站点> reload-doc manufacturing doctype job_card
bench --site <已授权站点> clear-cache
```

随后重新加载页面，核对工序计价字段和计时/计件中文下拉。合成fixture只用于隔离验收，不是客户初始化；客户岗位、公司、班组、员工、审批和数据准备仍须显式映射并完成Z01。下文按原日期保留历史环境与命令，不能作为本包当前源码清单。

**2026-10-27 B04最新补充：**本地`xgd-dev.localhost`和`xgd-test.localhost`已通过原生System Settings保存Float默认6位，中文与原舍入方式不变。只影响没有显式字段精度的原生Float；Currency仍按原规则，既有库存事实不重算。原3位配置的入库0.123456→0.123已复现，6位后该样例正确；多层BOM和材料损耗的原生失败已由本批局部源码修补，隔离8项通过；仍不能视为完整精度验收。`xgd-b19-http.localhost`本批未改配置或重跑。本批最终源码为`checks/b04-precision-delivery-source-manifest.json`共21文件，运行对应已修改源码镜像，见[数量证据](../evidence/B04/precision-loss/run-record.md)。BOM行新字段仅在测试站导入；开发站/18088专用站尚未迁新字段或重启到本批源码，勿直接把新镜像当旧网页运行版本。以下旧状态按对应日期阅读。

原生精度配置使用现有脚本，默认只读；限定上述两个本地站点，不能用作客户部署工具：

```sh
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/configure_quantity_precision.py xgd-test.localhost
# 需要应用到新建且已完成B01的本地站时，显式加 --apply；现有已配置站点不必反复保存。
```

**2026-10-27续接提示：**当前已进入B19局部验证，固定底座不变。HTTP测试另用 `xgd-b19-http.localhost` 合成副本和本机18088，原开发/测试站点不激活审批；本批完成后专用Web已停，副本与证据保留，不重复建库。准备/运行入口及失败修正见[B19 HTTP记录](../evidence/B19/http/run-record.md)。批准后变更本批使用原隔离测试站点，证据见[B19变更记录](../evidence/B19/approved-changes/run-record.md)。当前源码清单为 `checks/b19-changes-source-manifest.json`，以下B01/B02/B10命令与状态保留为对应阶段记录，不能当成最新源码清单。

仅用于本机开发与合成验收，不是客户生产部署包。固定ERPNext15.124.1/Frappe15.124.0，源码维护分支`codex/xgd-maintenance`。B01阶段未改业务代码；当前已进入B02辅助读取与B10单位子项，Frappe仍保持原版。

- 开发网页：`http://127.0.0.1:18086`，站点`xgd-dev.localhost`。
- 自动测试：`xgd-test.localhost`，与开发站点不同数据库；原生测试可能建自身测试公司。
- Compose项目`xgd-dev`，独立卷/网络，R05站点/数据卷保持不动。
- 普通登录账号：`b01.operator@example.invalid`；仅环境登录验证角色，不代表生产岗位权限已完成。密码只保存在本目录`.env`的`B01_OPERATOR_PASSWORD`；管理员密码按开发/测试分开。该文件0600，禁止提交/打印/复制到报告。
- 原生中文/上海时区/CNY；数量向导默认值仍为3位/银行家舍入，B04另行处理，不能拿本环境声称数量达标。

## 常用操作

在项目根目录执行：

```sh
docker compose -f .development/compose.json up -d --wait db redis-cache redis-queue
docker compose -f .development/compose.json up -d web
docker compose -f .development/compose.json ps -a
docker compose -f .development/compose.json stop web db redis-cache redis-queue
```

网页`stop_signal: SIGINT`使用原生开发服务器的正常退出处理；首次默认SIGTERM退出137，调整后退出0，记录见B01。

不执行`down -v`或删除卷。站点创建只运行一次，已有站点由脚本明确拒绝覆盖；后续启动不要重建站点。测试仅用于独立测试站点，不对开发或客户库启用测试。

## 首次创建记录

本机已完成以下步骤，**已有站点不要重复执行**。新环境先取得ERPNext `v15.124.1`，核对HEAD为`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，建立`codex/xgd-maintenance`分支。`.env`只在本机创建，分别设置`B01_DB_PASSWORD`、`B01_DEV_ADMIN_PASSWORD`、`B01_TEST_ADMIN_PASSWORD`、`B01_OPERATOR_PASSWORD`、权限0600；不得复制现有凭据到新环境。实际构建、建站、中文向导和测试启用命令：

```sh
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json up -d --wait db redis-cache redis-queue
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/create_site.py xgd-dev.localhost
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/setup_site.py xgd-dev.localhost
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/create_site.py xgd-test.localhost
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/setup_site.py xgd-test.localhost
docker compose -f .development/compose.json run --rm --no-deps -T bench bench --site xgd-test.localhost set-config allow_tests true
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/prepare_test_roots.py
docker compose -f .development/compose.json up -d web
```

`prepare_test_roots.py`初始化时执行，只把自动测试库的六类中文基础分类内部名称对齐上游英文fixture；系统语言仍为中文，开发库不变。它拒绝非预期树结构；已适配的唯一根仅检查，不重复改名。Department无公司根的原简称钩子不适用：先调用原生`validate_rename`，再用原生底层重命名更新链接；这不是部门业务功能修补。异常时回滚。

## 源码绑定与复测

Dockerfile在固定官方镜像上复制独立完整checkout，复用相同版本的依赖与已编译静态资源；B02/B10只改Python控制器及对应测试，没有新增产品依赖或前端资源。后续源文件变更后必须重新构建，现有运行容器不会自动加载宿主改动：

```sh
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json up -d --force-recreate web
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b02-b10-source-manifest.json
```

B01的`checks/source-manifest.json`保留为历史。当前B02/B10使用`checks/b02-b10-source-manifest.json`绑定基线、工作区补丁SHA256及13个受影响/相关文件；按真实checkout生成后再比对运行文件；不能改预期来掩盖未部署的补丁。新增依赖、数据库元数据或打包JS/CSS变化分别沿原生依赖安装/迁移/资源构建步骤，须在所属卡绑定；本Dockerfile本身不替代这些步骤。B01没有为未发生的依赖变化重装依赖。

当前COPY方式适用于同版本、未删除文件的基线；后续若删除/重命名源码，须处理基础镜像旧文件残留并核验，不能只覆盖COPY。网页进程与临时测试容器都要核对实际文件，不能仅凭相同镜像标签判断。

已绑定测试入口（只在测试站点允许测试后）：

```sh
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --doctype "Stock Entry" --test test_warehouse_user --failfast
```

原上游CI存在于源码`.github/workflows/`，本轮只沿用本地Bench测试入口，不触发远程CI。完整workers/websocket/生产反向代理、客户备份恢复/性能及业务功能归后续卡。具体实际结果以[运行记录](../evidence/B01/run-record.md)为准；此说明不是验收通过声明。

新测试站点使用`--doctype`自动准备原生测试依赖；`--module`不能保证这些fixture存在。保留CI=1并同时核对实际测试数与OK/FAILED，不能只看进程退出0；当前镜像无可选xmlrunner，不请求JUnit输出。

**B01原全量fixture基线：未通过，历史结果保留。**六类基础分类名称差异已在测试库适配，最新一次`--doctype`仍在依赖装载阶段报`DocType Payment Gateway not found`；没有仓库权限通过结论。不为单项基线安装额外业务模块。B02/B10已自行建立最小真实fixture；使用`--module`搭配`--skip-test-records --skip-before-tests`仅跳过自动递归装载，保留原生业务入口与校验。不同时传`--case`与`--test`（当前runner组合会报错）。具体命令、通过范围与限制分别见[B02记录](../evidence/B02/run-record.md)、[B10记录](../evidence/B10/run-record.md)，不据此宣称全量上游基线通过。

HTTP证据只用独立测试站点的B02合成账号；凭据位于`private/`、0600、忽略提交和构建。仅源码变化需要复测时，可对同一fixture执行`setup_b02_http.py restore`后重新验证并`revoke`，不重建站点或客户数据；临时18087服务验完即停。


### B04新字段运行前置

本批测试站已执行一次原生元数据导入，后续不重复建站/全量装依赖。对开发站启用本批新源码前，须在已绑定的本地联调任务中执行同一`reload-doc`，核对字段与源码后再启动；客户站另走交付验收。当前只记录测试站实际命令：

```sh
docker compose -f .development/compose.json run --rm --no-deps -T bench bench --site xgd-test.localhost reload-doc manufacturing doctype bom_item
```

原生BOM未保存成本预览尚未联调；最终保存值的损耗已在限定测试验收。完整G1、中文页面、客户端兼容及客户部署均不由本批8项代替。
