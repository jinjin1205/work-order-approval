> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R01｜ERPNext 来源、范围与部署入口

核查：2026-10-26，截止 09:13 UTC（17:13 北京时间）。方式：GitHub 连接器读取发布记录、标签引用、目录和指定文件；未克隆全库、未安装依赖、未启动应用、未执行测试。下文是资料与静态源码事实，不能据此认定满足业务规则或生产可用。

## 1. 固定评估版本

| 组件 | 本次固定版本／仓库提交 SHA | 解析依据与选择理由 |
|---|---|---|
| ERPNext | `v15.124.1` → `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e` | [正式发布](https://github.com/frappe/erpnext/releases/tag/v15.124.1)，2026-10-22 发布，draft=false、prerelease=false；[标签引用](https://api.github.com/repos/frappe/erpnext/git/ref/tags/v15.124.1) 的 object.type=commit。此次 `releases/latest` 返回该版本；仅据此选作比较基线，不宣称覆盖所有版本系列。 |
| Frappe 框架 | `v15.124.0` → `f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab` | [正式发布](https://github.com/frappe/frappe/releases/tag/v15.124.0)，2026-10-22；[标签引用](https://api.github.com/repos/frappe/frappe/git/ref/tags/v15.124.0)。ERPNext 的依赖要求为 `>=15.111.0,<16.0.0`，该版本在声明范围内；实际组合运行未验证。 |
| 官方容器配置 | `main` 读取时 → `2e6c8573a2af9882df705ce4247a26eb69c4f597` | [固定提交](https://github.com/frappe/frappe_docker/commit/2e6c8573a2af9882df705ce4247a26eb69c4f597)，提交时间 2026-10-25。它是部署资料基线，不是已经与上述版本构建成功的镜像。 |
| Bench CLI | `v5.31.1` → `660bc2898500dc33828056c1228e5a1d538573b1` | [正式发布](https://github.com/frappe/bench/releases/tag/v5.31.1)，2026-10-23；[标签引用](https://api.github.com/repos/frappe/bench/git/ref/tags/v5.31.1)。作为需核验的工具版本登记；与上述组合的运行兼容性未验证。 |

**关键限制：**Frappe 的 `releases/latest` 本次返回 v16.53.0，超出本次 ERPNext 的依赖上限，不能直接配套。固定容器源码的自定义构建默认 `FRAPPE_BRANCH=version-16`、Python 3.14、Node 24，且 `pip3 install frappe-bench` 未锁版本。R05 若运行，必须记录实际构建参数或镜像 digest，并核对其中 ERPNext/Frappe/Bench 的版本；不能将“固定容器仓库提交”等同于“固定全部运行依赖”。不因本记录而现在修改容器配置。

来源：[ERPNext pyproject](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/pyproject.toml)、[容器构建文件](https://github.com/frappe/frappe_docker/blob/2e6c8573a2af9882df705ce4247a26eb69c4f597/images/custom/Containerfile)。此前基于 `develop` 的业务发现只保留为线索，R05 涉及该行为时核对本次固定版本，不直接照搬结论。

## 2. 开放范围与已取得程度

| 范围 | 已读证据 | 本轮可以认定／不能认定 |
|---|---|---|
| 业务后端 | [ERPNext README](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/README.md)、[Job Card 文件头](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/job_card/job_card.py#L1) | 制造、库存属于公开 ERPNext 仓库；已取得选定文件内容，未取得完整本地 checkout，未验证闭环。 |
| PC 界面／框架 | [Frappe README](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/README.md)、[前端依赖](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/package.json) | 服务端与集成客户端框架公开；前端依赖也必须纳入实际构建清单，不把 ERPNext 单仓当独立可运行系统。 |
| 手机网页 | [同框架 mobile.scss](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/public/scss/desk/mobile.scss#L12) 有小屏媒体查询 | 有公开的小屏适配源码，不需据此假设存在必需的私有手机前端；实际报工、扫码、领退料可用性及操作成本未验证。未声称原生 App 已取得。 |
| 首版三项 AI | 本轮限定文件未提供三项能力的实现证据 | **未验证**，不能记作已复用；也不能仅因未在 README 看到就断言整个生态没有。R05/后续 AI 卡按实际需求评估。 |
| 商业服务与额外 App | README 同时列 Frappe Cloud 与自部署入口；Compose 注释说明默认镜像仅含 frappe 和 erpnext | 自部署入口可读；未购买商业支持，未取得额外 App。未发现本次已读核心入口要求必须购买私有模块，但这不是全生态授权或依赖完备结论。 |

## 3. 许可与主要依赖资料

| 对象 | 已核事实 | 交付时须保留／待补 |
|---|---|---|
| ERPNext 代码 | [license.txt](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/license.txt) 为 GPL v3；[package.json](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/package.json) 声明 GPL-3.0；Job Card 文件头指向 license.txt | 保留许可、Frappe 与贡献者版权和改动来源，依据最终交付形式整理对应源码。用户接受源码开放不等于已完成所有分发义务。 |
| ERPNext 文档／品牌 | README 声明文档 CC-BY-SA-3.0，并单列商标政策入口 | 如复用文档或品牌，分别核其要求；本轮不复制品牌设计，不出具商标许可结论。 |
| Frappe 框架 | [LICENSE](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/LICENSE) 为 MIT，版权 Frappe Technologies | 保留版权与许可文本。 |
| frappe_docker | [LICENSE](https://github.com/frappe/frappe_docker/blob/2e6c8573a2af9882df705ce4247a26eb69c4f597/LICENSE) 为 MIT | 保留来源、版本、版权与许可文本；镜像内部依赖另算。 |
| Bench | [LICENSE](https://github.com/frappe/bench/blob/660bc2898500dc33828056c1228e5a1d538573b1/LICENSE) 为 GPL v3；[pyproject](https://github.com/frappe/bench/blob/660bc2898500dc33828056c1228e5a1d538573b1/pyproject.toml) 明确 GPL-3.0-only | 作为部署工具单列，不能随容器仓库一概写成 MIT。 |
| 第三方依赖 | ERPNext pyproject：pycountry、Unidecode、barcodenumber、rapidfuzz、holidays 等；前端 onscan.js。Frappe pyproject：数据库驱动、Redis/RQ、Web/PDF 等；存在固定 Git 提交的 PyPika/Gunicorn；前端包含 Bootstrap、jQuery、Vue、扫码、表格、图表等 | 已读主清单，尚未安装解析全部传递依赖，未完成逐包许可核验。不得出具“全部许可兼容”或“无安全风险”结论。 |
| 第三方声明 | [attributions.md](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/attributions.md) 列 MIT 组件、OFL 字体、GeoIP 等，文件自述最后更新 2022-07-04 | 可复用该声明入口，但它不是当前完整 SBOM。R05 产生实际依赖集合后，仅补交付涉及部分；Z01 随包核对。 |

Frappe [pyproject](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/pyproject.toml) 声明 Python `>=3.10,<3.15`；package.json 声明 Node `>=18`。这些是版本范围，不是对任意组合的运行认证。Bench pyproject 要求 Python `>=3.10`。客户资源、网络和架构适配仍依赖 C06 实际资料。

## 4. 可沿用的运行与验证入口

| 事项 | 精确入口／所见事实 | 执行边界 |
|---|---|---|
| 容器启动 | [README](https://github.com/frappe/frappe_docker/blob/2e6c8573a2af9882df705ce4247a26eb69c4f597/README.md) 要求 Docker、Compose v2、git；`compose.yaml` 为基础部署配置，`pwd.yml` 是短时演示且不能安装自定义 App | 演示启动不能当客户部署方案。现有配置版本默认值与本次 15 系不同，R05 先绑定配置再运行。 |
| 服务与架构 | [compose.yaml](https://github.com/frappe/frappe_docker/blob/2e6c8573a2af9882df705ce4247a26eb69c4f597/compose.yaml)：backend/frontend/websocket/queue/scheduler、sites 卷；多个服务写 `platform: linux/amd64`，数据库/Redis 地址外部提供 | 必须配对应数据库/Redis override；不可认为该单文件包办全部服务。本机与客户架构未核实，不能声称 ARM/Mac 已兼容。 |
| ARM 资料 | [ARM64 文档](https://github.com/frappe/frappe_docker/blob/2e6c8573a2af9882df705ce4247a26eb69c4f597/docs/01-getting-started/03-arm64.md) 有 arm64 构建说明，但示例为 ERPNext v16.19.1，且含 latest 建议 | 只当入口，不能照抄为本次固定版本。 |
| 建站／迁移 | [site operations](https://github.com/frappe/frappe_docker/blob/2e6c8573a2af9882df705ce4247a26eb69c4f597/docs/04-operations/01-site-operations.md)；固定 Frappe [site.py#L679](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/commands/site.py#L679) 定义 `migrate`，运行补丁、同步 schema、重建文件/翻译 | 源码入口已定位；未建站、迁移。文档仍有旧版链接，实际运行以所锁版本 CLI 为准。 |
| 备份／恢复 | Frappe [site.py#L825](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/commands/site.py#L825) 的 backup 支持文件与配置；[restore#L160](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/commands/site.py#L160) 支持数据库及公共/私有文件 | 可复用，不另写备份系统。真实备份与恢复核对未执行；不能只备数据库便宣称附件与配置已恢复。 |
| 单测 | Frappe [utils.py#L757](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/commands/utils.py#L757) 定义 `run-tests`，可按 app/doctype/module/test 限定 | 后续针对本项目所需范围选测试，不因入口存在声称通过。 |
| 上游 CI 参考 | ERPNext [.github/workflows/server-tests-mariadb.yml](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/.github/workflows/server-tests-mariadb.yml) 调用 `bench --site test_site run-parallel-tests --app erpnext`；配置专用 runner/镜像，镜像名含 py3.11-node18 | 仅为现有测试入口，未读此次提交 CI 运行结果；不能原样照搬其专用环境。README 的 server-tests.yml 链接在该固定版本返回 404，已按目录找到实际文件。 |

### 关键文件身份（均为文件 blob SHA，不是仓库提交）

| 仓库／文件 | blob SHA |
|---|---|
| erpnext/pyproject.toml | `07b27ddec032a017241cc918cd2efb02568bdf27` |
| erpnext/license.txt | `f288702d2fa16d3cdf0035b15a9fcbc552cd88e7` |
| erpnext/package.json | `509fe275e05d49b0e67cd1a259c29f9a521184dd` |
| frappe/pyproject.toml | `5c5904f3e5ac5c0ac766f296db3c6efe5abba960` |
| frappe/LICENSE | `6919960f8ba9c6ea72a8a0b07d6e98b4b46c7531` |
| frappe/attributions.md | `611b9b1d9a409ded0f6038c3fce94e542fe16e4c` |
| frappe/frappe/commands/site.py | `985250c62b5db062e2b21c8d78d9c92821f5d86d` |
| frappe_docker/compose.yaml | `6d82ee8f4489347d301ec4e47991e7e7dde77bfe` |
| frappe_docker/images/custom/Containerfile | `730f343d5a20a6dcc5cafcbd377508975af1790e` |
| frappe_docker/LICENSE | `c4e7b3dc6f56a3ca6718b9c00abecc073a7cf57a` |
| bench/pyproject.toml | `c3a9b5d02f91a9b5aee0cdb55b9e210af7277495` |
| bench/LICENSE | `ef7e7efc09c9d471c391f05b9567966928085840` |

**R01 结论：**已形成可比较的公开来源、版本、主要许可与运行入口资料。尚未解决的是实际构建/依赖锁、运行验证、全部交付依赖许可、首版 AI 三项适配、手机操作及业务规则符合度；分别留给 R05 和获准的后续卡。无本轮运行通过结果。
