> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R03｜核验动作与运行记录

记录时间：2026-10-26 17:34 CST（Asia/Shanghai）。**静态筛选结束；暂不进入运行。CASE-01～07 的真实业务执行次数为0，没有“通过”结果。** 决策依据见 [fit-matrix](fit-matrix.md)；本文件不把下载源码、读取POM或静态分析称为运行验收。

## 1. 环境、输入与边界

| 项 | 实际记录 |
|---|---|
| 工作目录 | `.` |
| 宿主 | `Darwin 27.0.0 arm64` |
| 工具 | `git version 2.54.0 (Apple Git-157)`；`Python 3.9.6`；GitHub connector；系统curl |
| 后端版本 | `8a40bfe241178c00394cc8011b6bfee1b3a12655`，选定文件只读，不是完整后端本地checkout |
| PC版本 | `9c73ecf89cc00a23b470e14e6148f393dec65276`，Git浅克隆实际HEAD验证一致 |
| 业务输入 | [R02 fixture-spec v1](../R02/fixture-spec.md)、[expected-results v1](../R02/expected-results.md)；主链计划10、三工序各10、材料需求5等均为期望，不是本候选实际结果 |
| 初始化 | 未安装依赖、未创建数据库、未导入SQL、未建立样例账号/物料/单据。实际业务ID与请求凭证未生成 |
| 服务 | 本R03没有启动Docker或候选服务，没有执行Maven/npm构建或业务HTTP请求。共享环境核查由主任务统一记录，本记录不据此推断客户环境 |
| 输出 | 仅新增本目录 `fit-matrix.md` 与 `run-record.md`；未改公共TODO、R01、R02、产品源码、全局配置或Downloads原件 |

## 2. 动作与实际结果

### A. 沿用R01，补必要源码

- 读取AGENTS、R03任务卡、决策范围、开发TODO、R01 t3rik证据、R02输入/判据。R01固定后端提交、顶层许可、App未开源、构建声明、已知启动脚本差异直接沿用。
- GitHub connector读取固定提交递归树，用于定位必要文件；本轮没有重审全库。指定文件按固定提交URL读取，正文行号用于fit-matrix的S01～S12。
- 预期：找到能证明真实动作的控制器、服务、Mapper和表结构。实际：定位工单保存即生成BOM、审批执行报工、原报工改删、线边转仓与自动BOM消耗、数量两位存储、权限及历史路线待适配路径。结论层级均为源码静态核查。
- 选定文件可取得不等于构建通过；没有推断整库测试覆盖、前后端部署匹配或业务结果。

### B. Gitee固定PC源码取得

先尝试不同于R01网页405的Git协议入口；不是反复请求同一网页。

```sh
GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c core.askPass= ls-remote https://gitee.com/wangsanping/t3rik-erp-ui.git HEAD refs/heads/main refs/heads/master
```

1. 沙箱内正常代理首次输出：`Failed to connect to 127.0.0.1 port 10808 ... Couldn't connect to server`，exit128。
2. 仅当前命令清除代理再试输出：`Could not resolve host: gitee.com`，exit128；没有修改全局代理/Git配置。这两次只说明该执行环境网络未通，不能据此判断仓库不可取得。
3. 按用户已授权R03范围，以`require_escalated`对原始只读命令重试成功，exit0：

```text
9c73ecf89cc00a23b470e14e6148f393dec65276 HEAD
9c73ecf89cc00a23b470e14e6148f393dec65276 refs/heads/main
```

接着浅克隆固定main（此时已核其与目标SHA一致）：

```sh
GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c core.askPass= clone --depth 1 --single-branch --branch main https://gitee.com/wangsanping/t3rik-erp-ui.git /private/tmp/r03-t3rik-ui-20261026
git -C /private/tmp/r03-t3rik-ui-20261026 rev-parse HEAD
git -C /private/tmp/r03-t3rik-ui-20261026 status --porcelain
```

实际：clone exit0，HEAD为目标SHA，status无输出。预期的PC源码取得达成。目录保留，未安装或运行，未删除。

读取 `LICENSE`、`package.json`、`src/api/mes/pro/feedback.js`、`src/views/mes/pro/feedback/index.vue` 以及必要退料/入库页面。实际发现：

- LICENSE为Apache-2.0，package.json L6为MIT；依赖含Vue2.6.12、Element UI2.15.6、Vue CLI4.4.6与试用甘特组件。没有自行判定双许可或分发兼容。
- 报工API路径与后端静态对应；PC提交设APPROVING，审批通过调用执行。
- `git ls-tree -r HEAD --name-only` 过滤 `package-lock.json|yarn.lock|pnpm-lock.yaml` 无匹配（rg exit1），未获得锁文件。
- `package.json`实际dev脚本为 `NODE_OPTIONS=--openssl-legacy-provider vue-cli-service serve`，build:prod同样设置该参数后build；这些是读到的入口，**本轮未执行**，不能拿engines宽松范围证明当前Node兼容。

### C. 初始化数量结构，只读不导入

```sh
curl -L --fail --max-time 40 --silent --show-error 'https://raw.githubusercontent.com/WangSanPing/t3rik-erp/8a40bfe241178c00394cc8011b6bfee1b3a12655/doc/20250415-init.sql' --output /private/tmp/r03-t3rik-init-20261026.sql
```

实际exit0。Python只读取选定CREATE TABLE块的数量/单位/主键定义，未执行SQL，未输出INSERT演示数据；按Git blob算法核对：

```text
bytes 10248263
git_blob_sha 9f27d9ef6f17410f2946117cda74938bdae8fc79
md_product_bom.quantity double(12,4)
pro_workorder_bom.quantity double(14,2)
pro_feedback.quantity_feedback / quantity_qualified / quantity_unquanlified double(14,2)
wm_issue_line.quantity_issued / wm_rt_issue_line.quantity_rt double(12,2)
wm_material_stock.quantity_onhand / wm_transaction.transaction_quantity double(12,2)
```

预期：定位实际存储定义，避免只凭Java BigDecimal认定精度。实际：固定文件身份与R01一致，存在R02四位需求/领退料和六位单耗输入的结构冲突。**未实际写数据库，不报告任何Q01～Q05/U01实测值**。SQL临时文件保留，没有作为本项目数据初始化。

### D. Jimu精确发布POM

R01网页工具未取得的精确Maven POM，本轮网页读取仍不可访问；随后用普通curl在已授权只读提升环境读取成功，没有安装依赖：

```sh
curl -L --fail --max-time 25 --silent --show-error 'https://repo.maven.apache.org/maven2/org/jeecgframework/jimureport/jimubi-spring-boot3-starter/1.9.4/jimubi-spring-boot3-starter-1.9.4.pom'
curl -L --fail --max-time 25 --silent --show-error 'https://repo.maven.apache.org/maven2/org/jeecgframework/jimureport/jimureport-spring-boot3-starter-fastjson2/1.9.4/jimureport-spring-boot3-starter-fastjson2-1.9.4.pom'
```

两次实际exit0。JimuBI精确POM输出`groupId=org.jeecgframework.jimureport`、`artifactId=jimubi-spring-boot3-starter`、`version=1.9.4`；licenses名称为“功能可以免费用”、URL为`http://jimureport.com/vip`，并声明JimuReport starter-fastjson2 1.8.1依赖。JimuReport精确POM为1.9.4，父项spring-boot-starter-parent3.1.5，没有组件独立licenses节点。

另有公开官方仓库网页检索，但它对应不同版本且描述不一致，未用来替代1.9.4许可结论。GitHub connector的tags端点被工具允许列表拒绝（400），不是仓库不存在。至此停止追查：尚未取得实际采用版本完整源码/二进制再分发条款及依赖解析结果，不出具授权/兼容结论，也不自动购买授权。

## 3. 必要源码清单

以下文件均来自后端固定commit `8a40bfe241178c00394cc8011b6bfee1b3a12655`。blob SHA仅用于文件身份，不当作仓库提交。具体行号和业务解释在fit-matrix；没有因文件存在就宣称支持。

| 文件 | blob SHA |
|---|---|
| `t3rik-mes/src/main/java/com/t3rik/mes/pro/controller/ProFeedbackController.java` | `daaefa21161d430bde59533f98177f43f5b1a909` |
| `t3rik-mes/src/main/java/com/t3rik/mes/pro/service/impl/ProFeedbackServiceImpl.java` | `bbef68d07252a6d5c1077eaf6fa126887959491c` |
| `t3rik-mes/src/main/java/com/t3rik/mes/pro/controller/ProWorkorderController.java` | `3ef10fb9554206948e40dbe89043b1636fcb4a49` |
| `t3rik-mes/src/main/java/com/t3rik/mes/pro/controller/ProTaskController.java` | `e7b52c864c9e94fd18f4225db35781f56057dfd1` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/controller/WmIssueHeaderController.java` | `058427c2e3018e22177cfb32bab04e95f0bd8a2b` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/controller/WmRtIssueController.java` | `d4b2fac4cbb028d9e45e9f0fa05bac83a4e1ba97` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/controller/WmRtIssueLineController.java` | `9d8e4490aa0dca92ff8bd82c889924998e15b06f` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/service/impl/WmProductProduceServiceImpl.java` | `01631ff5518241aacf066019be2327924f90721e` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/service/impl/WmIssueHeaderServiceImpl.java` | `71785590577c8748c5cb1ae00a32db2c6fc3aa34` |
| `t3rik-mes/src/main/java/com/t3rik/mes/pro/service/impl/ProTaskServiceImpl.java` | `5016d91e2bbc0d2026369e8b4bc12a01cfd42669` |
| `t3rik-mes/src/main/java/com/t3rik/mes/pro/domain/ProFeedback.java` | `ebe1111c75b07697d2fed320b5cfb7a7eb1839d8` |
| `t3rik-mes/src/main/java/com/t3rik/mes/md/domain/MdProductBom.java` | `0d8b642704177ec3bfadfc0989f4ae8a26def6d6` |
| `t3rik-mes/src/main/resources/mapper/pro/ProFeedbackMapper.xml` | `efb98ded34dd03c1a3f8d8ccb1516b6c1d49382e` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/service/impl/StorageCoreServiceImpl.java` | `6df1cc3e05bf51efb8dd569f948b1e2ca0122d58` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/service/impl/WmItemConsumeServiceImpl.java` | `9d424ed6e5cfffd34467caaa4eba00fddecb30b1` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/service/impl/WmTransactionServiceImpl.java` | `2a686a08fb3d7555d6488959867849b90a8a6a62` |
| `t3rik-mes/src/main/java/com/t3rik/mes/wm/controller/WmProductRecptController.java` | `786d005f4f95a9339b262fa00df20b3ab0b2484c` |
| `t3rik-framework/src/main/java/com/t3rik/framework/interceptor/RepeatSubmitInterceptor.java` | `733fffa3f4db041bf02bedf183c33b2deae936c9` |
| `t3rik-mes/src/main/java/com/t3rik/mes/pro/service/impl/ProRouteProcessServiceImpl.java` | `10357a1b7c7d8245d2a0763002b0f6c9cf29c97b` |
| `t3rik-mes/src/main/resources/mapper/pro/ProTaskMapper.xml` | `a104b97e3d3d075f636620eae29dfa3745583821` |
| `t3rik-mes/src/main/resources/mapper/pro/ProRouteProductBomMapper.xml` | `cb553e98e5efda42231129621d4cbcf90e8668c1` |
| `t3rik-framework/src/main/java/com/t3rik/framework/config/SecurityConfig.java` | `798affb05f457fd4dfe2f0ea394d5f0b0691f5e8` |

PC固定commit来源：[Gitee树](https://gitee.com/wangsanping/t3rik-erp-ui/tree/9c73ecf89cc00a23b470e14e6148f393dec65276)。本轮读取的PC路径为：

- `LICENSE`、`package.json`
- `src/api/mes/pro/feedback.js`
- `src/views/mes/pro/feedback/index.vue`
- `src/views/mes/wm/rtissue/line.vue`
- `src/views/mes/wm/productrecpt/index.vue`

## 4. 运行样例登记

| CASE | 输入来源 | 本候选实际执行 | 结果状态／停止原因 |
|---|---|---|---|
| 01 主链 | R02主链输入 | 无 | 未验证；工单生成、生效与产出语义已有静态差异 |
| 02 精度成本统计 | R02 Q/U/V/M | 无 | 未验证；初始化字段有明确精度冲突，成本等仍缺实现证据 |
| 03 工时 | R02 T01～T11 | 无 | 未验证；未取得对应实际工时计算入口 |
| 04 重复并发故障 | R02 I01～I06 | 无 | 未验证；存在需适配的执行/库存保护路径，未制造网络故障 |
| 05 冲销 | R02更正10→8 | 无 | 未验证；改删不满足追加冲销，未为样例新增功能 |
| 06 领退耗 | R02领10退2及失败分支 | 无 | 未验证；现有转仓可复用候选，自动理论消耗与事实边界需改造 |
| 07 权限状态历史 | R02角色及路线v1/v2 | 无 | 未验证；未创建全权管理员替代角色测试，未接AI |

没有将未运行写成“功能不支持”。“静态差异”指已读代码与固定需求的冲突；“未验证”指尚缺运行/完整路径证据。对复用比例、性能、手机操作、恢复、跨机器部署、真实车间适用性均不作结论。

## 5. 收口

保留有条件候选，暂不占用本轮运行名额；静态证据已足够比较其改造负担，继续启动服务不会消除精度、审批、冲销与实耗语义差异。下一次只有选型需要、相关实现/输入变化或新的明确验证范围时，再绑定实际隔离环境与R02业务ID执行相应路径。没有推进R06选型决定或B/A/Z实现。

