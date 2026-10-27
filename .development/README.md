# B01 独立中文开发环境

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
