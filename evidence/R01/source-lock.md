> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R01 源码版本登记

核查日期：2026-10-26（北京时间）。本卡结果是**候选来源、版本和缺口清单**，不是完整源码下载、构建成功或运行环境冻结。

## 本次比较基线

| 候选/组件 | 固定版本与仓库 commit | 取得程度 |
|---|---|---|
| t3rik 后端 | [WangSanPing/t3rik-erp](https://github.com/WangSanPing/t3rik-erp/commit/8a40bfe241178c00394cc8011b6bfee1b3a12655)：`8a40bfe241178c00394cc8011b6bfee1b3a12655` | 提交、目录树、选定源码/依赖声明已读 |
| t3rik PC | [Gitee wangsanping/t3rik-erp-ui](https://gitee.com/wangsanping/t3rik-erp-ui)；页面所指 `9c73ecf89cc00a23b470e14e6148f393dec65276` | **未完成固定源码核验**；仅仓库页可读，固定文件读取失败，不作为已锁定可用组件 |
| OpenMES 核心/网页 | [Mes-Open/OpenMes v0.27.0](https://github.com/Mes-Open/OpenMes/releases/tag/v0.27.0)：`b952915bddb2120737f10a730a1e45b1d162c47e` | release、注释标签剥离、目录树、选定源码/锁文件已读 |
| ERPNext | [frappe/erpnext v15.124.1](https://github.com/frappe/erpnext/releases/tag/v15.124.1)：`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e` | 正式发布/标签及选定文件已读 |
| ERPNext 所需框架 | [frappe/frappe v15.124.0](https://github.com/frappe/frappe/releases/tag/v15.124.0)：`f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab` | 在ERPNext声明的 `>=15.111.0,<16.0.0` 范围内；组合运行未验证 |
| ERPNext 容器资料 | [frappe/frappe_docker](https://github.com/frappe/frappe_docker/commit/2e6c8573a2af9882df705ce4247a26eb69c4f597)：`2e6c8573a2af9882df705ce4247a26eb69c4f597` | 仅配置/文档基线，默认16系不等于与上述15系匹配 |
| ERPNext 部署CLI | [frappe/bench v5.31.1](https://github.com/frappe/bench/releases/tag/v5.31.1)：`660bc2898500dc33828056c1228e5a1d538573b1` | 工具发布/源码固定；实际安装、解析与组合运行未验证 |

固定提交不意味着最新、最安全或已维护合格。此次没有完整克隆、下载镜像或安装任一候选。选定文件的 blob SHA、来源与读取限制分别见 [t3rik证据](t3rik-evidence.md)、[OpenMES证据](openmes-evidence.md)、[ERPNext证据](erpnext-evidence.md)。文件 blob、注释标签对象与仓库提交已分开，不混用。

ERPNext之前按 develop 取得的业务发现保留为线索；以后执行对应行为时须核本次固定15系版本。t3rik/OpenMES基线未变，已有报工精度/更正的静态发现直接引用，不重复整库审核。

## 部署和验证入口对照

| 候选 | 环境和已有入口 | 进入运行前的具体缺口 |
|---|---|---|
| t3rik | JDK17、Maven/Kotlin、MySQL8、Redis；启动模块`t3rik-erp`；doc初始化SQL；PC另仓 | PC固定源码和前后端匹配未核；POM为Spring Boot3.3.13，README仍写3.0.6；release脚本jar名不符；没有已确认业务测试/升级/恢复入口；Jimu依赖许可缺口 |
| OpenMES | Docker/Compose；PHP8.3系列、PostgreSQL17系列；同仓前端构建；默认4服务；composer test、backend npm test、迁移入口已定位 | 镜像/下载物尚非全量固定；ionCube及许可元数据差异；默认PHP测试用SQLite不能证明PostgreSQL并发；备份资料有，完整恢复未验证 |
| ERPNext | Docker/Compose或Bench；ERPNext＋Frappe＋数据库/Redis/队列；原生run-tests、migrate、backup/restore入口已定位 | Docker默认16系与选定15系不匹配；需实际锁构建参数/镜像/Bench；架构/数据库/客户网络未验证；演示配置不能替代正式部署 |

精确文件、来源链接与限制在三个证据文件第4节。所有入口本轮均未执行。第三方服务发行版、容器摘要与实际解析依赖在相应 R03～R05 运行记录中补齐，不能拿本卡声称环境已完全可复现。

## R01 结束判断

已形成三个候选可比较的来源/开放范围/许可事实/部署入口清单；缺失PC源码、私有模块和未核依赖已明示，满足R01“不能取得关键部分则记录限制”的结束条件。R01资料整理完成；候选适配、全量依赖许可核验、安装运行及底座选择未完成。

本轮不执行 R03～R05、不追索私仓、不为补齐候选提前写功能。后续仅在继续候选时补它的必要缺口；不安装五套系统，不因此扩成完整开源生态审计。
