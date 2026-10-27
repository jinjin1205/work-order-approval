> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R01｜t3rik-erp 来源与开放范围证据

核查日期：2026-10-26（Asia/Shanghai）。范围：公开资料与指定版本源码静态阅读。未克隆完整仓库、安装依赖、导入数据库、运行服务或执行业务样例；不构成 R03 结果。

## 1. 固定来源与取得程度

| 对象 | 版本／来源 | 本轮实际取得 | 限制 |
|---|---|---|---|
| 后端 | `WangSanPing/t3rik-erp`，commit `8a40bfe241178c00394cc8011b6bfee1b3a12655` | GitHub API 提交元数据、完整路径树及下表选定文件内容 | 仅这些文件已阅读；没有完整源码本地副本或构建产物 |
| PC 前端 | [Gitee wangsanping/t3rik-erp-ui](https://gitee.com/wangsanping/t3rik-erp-ui) | 仓库展示页及其许可证展示；页面指向提交 `9c73ecf89cc00a23b470e14e6148f393dec65276` | 提交正文、固定版本 LICENSE、package.json 读取失败；该 SHA 仅为页面所指提交，**尚未验证固定源码及前后端匹配** |
| App／移动网页前端 | 后端 README 中的 `t3rik-app` | 仅 README 的范围说明 | README 明确暂未开源；没有取得源码，不能计入复用资产 |

后端提交身份由 [GitHub commit API](https://api.github.com/repos/WangSanPing/t3rik-erp/commits/8a40bfe241178c00394cc8011b6bfee1b3a12655) 确认，提交时间 `2026-01-09T03:25:35Z`，消息为更新 README；提交树 `78c53c245f076114f4b8016b849ee1e0c37e5380`。不据此声称它是当前最新版本。

GitHub [递归路径树](https://api.github.com/repos/WangSanPing/t3rik-erp/git/trees/8a40bfe241178c00394cc8011b6bfee1b3a12655?recursive=1) 返回 1591 个条目，`truncated=false`。文件 blob SHA 与仓库 commit 分列如下。

| 已读文件 | 文件 blob SHA |
|---|---|
| [README.md](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/README.md) | `b00974a34c26be9c3194311e6298511f19066286` |
| [LICENSE](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/LICENSE) | `2da4f2c7ca667ae3f437a38c7a7498f8da7d7daf` |
| [pom.xml](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/pom.xml) | `c65fa7993bdbbf3ed58f7a6110a0a67efb27e6cb` |
| [t3rik-erp/pom.xml](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/t3rik-erp/pom.xml) | `843f5ede7220b35a0edaecfbd63495f920f62420` |
| [t3rik-common/pom.xml](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/t3rik-common/pom.xml) | `0d41db0eca8cbcdea7eac1481e556b4dab49ad09` |
| [t3rik-report/pom.xml](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/t3rik-report/pom.xml) | `dc18a6759f25e8b8b96aa26d0e00c79a52c04468` |
| [release.sh](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/release.sh) | `e894aef96a01a24ee64f2dd6a46e466cd1bbc95a` |
| [ERPApplication.java](https://github.com/WangSanPing/t3rik-erp/blob/8a40bfe241178c00394cc8011b6bfee1b3a12655/t3rik-erp/src/main/java/com/t3rik/ERPApplication.java) | `165883ceaffc988172bd18317de314d21c2f750c` |

## 2. 开放范围

| 部分 | 证据与判断 |
|---|---|
| 生产／库存后端 | `t3rik-mes` 在固定提交路径树及 Maven 模块中；之前已读报工、领退料等业务证据沿用，具体适配留 R03 |
| 账号／权限／公共组件 | `t3rik-system`、`t3rik-framework`、`t3rik-common` 在同一仓库；开放源码存在不等于已满足我们的权限验收 |
| PC 页面 | 独立 Gitee 仓库；不能用后端 Apache 许可自动代替前端固定版本的核查 |
| 手机／平板 | `t3rik-mobile` 是后端模块。演示与未开源 `t3rik-app` 不能作为已有手机网页源码 |
| AI 首版三项 | 本轮 README／POM 和路径名筛选没有取得可对应三项需求的 AI 实现证据；**未验证**，不写成已具备，也不据此断言全库没有 AI |
| 报表及外围 | 启动模块直接依赖 `t3rik-report`、`jimureport-spring-boot3-starter-fastjson2` 和 `jimubi-spring-boot3-starter`；还包含 HRM、打印等模块。它们是现有依赖，不自动扩入交付范围 |
| 商业／私有部分 | App 暂未开源已明确；未取得一份完整商业模块边界表。第三方报表组件是否具备所需分发许可须按实际版本核实，不能推断免费或已获授权 |

## 3. 许可与依赖清单

后端顶层 LICENSE 是 Apache-2.0，附有 `Copyright [2024] [t3rik]`。入口文件保留 `@author t3rik`；本轮不是逐文件版权审计。README 标明源自苦糖果 MES／若依，来源归属应保留；未核全量上游文件与传递依赖。

Gitee PC 仓库展示页标注 Apache-2.0 并展示许可证正文，但它是动态页面证据；固定提交的许可证仍未取得。不将这一状态写成“前端许可核验全部通过”。

| 必要或当前实际引用的依赖 | 固定清单中的版本依据 | 许可资料状态 |
|---|---|---|
| Spring Boot 依赖管理 | 根 POM：`spring-boot-dependencies:3.3.13` | [Maven Central 发布 POM](https://central.sonatype.com/artifact/org.springframework.boot/spring-boot-dependencies/3.3.13) 声明 Apache-2.0；这不覆盖全部受管理依赖 |
| Kotlin | 根 POM：`2.0.0` | 本轮仅取得依赖声明，实际分发文件许可待核 |
| MyBatis Plus / Druid / Redisson | 根 POM：Starter `3.5.5` / `1.2.23` / `3.40.1` | 本轮仅取得依赖声明，完整解析版本与许可待核 |
| MySQL Connector/J | 启动 POM 引用 `com.mysql:mysql-connector-j`，未显式指定版本 | Spring Boot 发布 POM 管理 `mysql.version=8.3.0`；实际依赖解析及驱动分发许可未验证 |
| JimuReport | 根／启动／报表 POM：`jimureport-spring-boot3-starter-fastjson2:1.9.4` | [Maven Central 该版本页面](https://central.sonatype.com/artifact/org.jeecgframework.jimureport/jimureport-spring-boot3-starter-fastjson2/1.9.4) 可读；元数据显示 Apache-2.0，但展示 POM 继承 Spring 父项、未单列组件许可证，**不能据此认定组件源码／二进制许可已完整核实** |
| JimuBI | 根／启动／报表 POM：`jimubi-spring-boot3-starter:1.9.4` | 精确版本的发布 POM 与许可读取失败；未确认可交付源码范围或商业授权条件 |
| Jimu NoSQL | 根 POM 管理 `jimureport-nosql-starter:1.9.4.1` | 这是依赖管理条目；本轮未证明运行时实际引入，不算已安装依赖 |
| PC npm 依赖、MySQL／Redis 服务 | README 指明 PC 为 Vue2；MySQL8 与 Redis 为环境要求 | PC package.json 未取得；服务发行版未选。精确版本、锁文件和许可资料待实际候选核验 |

交付前应随实际采用部分留存：来源和提交、LICENSE、已有版权／归属声明、适用 NOTICE、修改说明、实际构建依赖清单及其许可；本轮没有生成完整 SBOM，也没有给出法律兼容结论。未采用组件不为完善清单而无限追查。

## 4. 可复用入口与已知差异

| 项目 | 已核入口 | 结论与下一步边界 |
|---|---|---|
| 后端初始化 | README 指向 `doc` SQL；路径树有 `doc/20250415-init.sql`（10,248,263 bytes，blob `9f27d9ef6f17410f2946117cda74938bdae8fc79`） | 仅确认文件存在，未下载／审阅整份 SQL，更未导入；不得将演示数据当成本项目样例 |
| 数据迁移 | 路径树另有 `doc/sys_config_jasypt.sql` | 尚未取得版本化升级流程；初始化 SQL 不等于迁移与恢复方案 |
| 后端启动 | README 为 JDK17＋Maven＋Kotlin；`t3rik-erp/.../ERPApplication.java` 存在 | README 功能表仍写 Spring Boot 3.0.6，实际根 POM 为 3.3.13；以固定构建声明核验，不能照抄旧介绍 |
| 配置 | 路径树有 `t3rik-erp/src/main/resources/application.yml` 及 dev/pro/t3rik 配置；README 说明修改 MySQL、Redis 地址 | 未复制配置值或凭证；实际可用配置与依赖服务仍待 R03 隔离检查 |
| 发布脚本 | `release.sh` 有 start/stop/restart/status | 脚本写 `t3rik-admin.jar`，启动模块 POM 的最终名称是 `t3rik-erp`（jar）；存在静态不一致，运行效果未验证。本轮不修脚本 |
| PC 开发入口 | README 说明 Node16.13+、Vue2/Webpack，`npm install`、`npm run dev` | 仅为上游写法，前端 package.json 未读，不能当作已确认可执行命令 |
| 测试 | 启动 POM 声明 Spring Boot test/JUnit，根 POM 管理 Kotlin test | 完整路径树未发现 `src/test`、`tests` 或 Java/Kotlin `*Test` 文件；不能因此声称有可复用业务测试覆盖，更没有测试通过结果 |
| 备份／恢复 | 本轮 README、脚本与路径树未找到专门备份恢复入口 | 未验证。不得拿 `doc/清理常用表.sql` 当恢复脚本，也未执行清理 |

## 5. 读取失败与停止条件

- GitHub connector 能读取后端固定提交与指定文件；不支持 Gitee，因此 PC 来源改用网页读取。
- Gitee 仓库页可读；[提交页](https://gitee.com/wangsanping/t3rik-erp-ui/commit/9c73ecf89cc00a23b470e14e6148f393dec65276) 返回 cache miss，`blob/main/package.json` 返回 405；固定 SHA 的 raw LICENSE/package.json 也不可读取。停止重试，记录为**本次工具未取得**，不能推断仓库私有或永久不可下载。
- Maven POM 直链读取失败；Sonatype 可读 Spring Boot 与 JimuReport 的对应版本页面，JimuBI 1.9.4 页面未取得。未把其他版本许可证套到本版本。

R01 可据以上信息形成比较清单。若 R03 继续候选，先解决 PC 固定源码取得、前后端匹配和报表依赖许可／可构建性，再决定是否值得运行。手机源码缺口明确，但最小改造量和节省成本仍未验证。本轮不追索私仓，也不为了补齐候选先写产品代码。
