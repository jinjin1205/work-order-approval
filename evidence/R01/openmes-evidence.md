> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R01｜OpenMES 来源、开放范围与运行入口核查

核查日期：2026-10-26。执行范围：公开文件、仓库树、发布与标签元数据的只读核查；未克隆完整仓库、未安装依赖、未构建、未启动、未执行测试。本文件不等于 R04 适配验收。

## 1. 版本锁定

| 项目 | 已核实值／依据 |
|---|---|
| 仓库 | [Mes-Open/OpenMes](https://github.com/Mes-Open/OpenMes) |
| 固定提交 | `b952915bddb2120737f10a730a1e45b1d162c47e`；[commit API](https://api.github.com/repos/Mes-Open/OpenMes/commits/b952915bddb2120737f10a730a1e45b1d162c47e) 返回提交时间 2026-10-14T20:28:27Z、标题 Release 0.27.0 |
| 正式发布 | [v0.27.0](https://github.com/Mes-Open/OpenMes/releases/tag/v0.27.0)，发布元数据：2026-10-14T20:40:13Z，draft=false、prerelease=false |
| 标签剥离 | [refs/tags/v0.27.0](https://api.github.com/repos/Mes-Open/OpenMes/git/ref/tags/v0.27.0) 指向注释标签对象 `f75163e5050f9eaac0bbc0a5fc993a8bb3d06c99`；[标签对象](https://api.github.com/repos/Mes-Open/OpenMes/git/tags/f75163e5050f9eaac0bbc0a5fc993a8bb3d06c99) 的 object.type=commit，object.sha 为上述固定提交 |
| 本次取得 | 下表所列文件内容／片段和该提交的目录树。不是完整源码包、镜像或已安装系统 |
| 检查方式 | GitHub connector `github_fetch` 读取 commits/releases/git ref/tag/tree；`github_fetch_file` 在固定提交读取文件。仓库树返回 truncated=false |

标签对象 SHA、文件 blob SHA 与仓库 commit SHA 已分开记录。后续运行沿用固定 commit；不要直接按 main 或 latest 启动后仍引用本证据。

## 2. 可获得范围

| 部分 | 文件／文档证据 | 本次结论与限制 |
|---|---|---|
| 核心后端 | [backend/composer.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/composer.json)、仓库树中的 `backend/app`、`backend/routes`、`backend/database` | 公开同仓，已读 manifest 与部署入口；业务可用性未验证 |
| PC 网页 | [工单列表源码片段](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/resources/js/Pages/admin/work-orders/Index.jsx#L1)、[backend/package.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/package.json) | 前端在同仓 `backend/resources`；React/Inertia 与 Blade 等既有页面并存，不需另取得私有 PC 前端 |
| 操作工网页／PWA | [Workstation.jsx](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/resources/js/Pages/operator/Workstation.jsx#L1)、[README](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/README.md#L344) | 操作工页面同仓；README 描述平板/PWA。手机尺寸、中文、扫码、弱网实际可用性未验证，不承诺离线 |
| 原生手机项目 | [mobile/package.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/mobile/package.json)；同仓树含 `mobile/api`、`mobile/app` 等 | Expo/React Native 源码公开同仓，manifest 含 web/ios/android 脚本；当前确认范围是手机网页，暂不引入原生打包链 |
| 本地前端依赖 | [packages/ui/package.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/packages/ui/package.json)、[packages/module/package.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/packages/module/package.json) | 网页通过 file:../packages 引用；同仓可定位，不能只复制 backend 后假定构建齐全 |
| 扩展与商业模块 | [modules/README.md](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/modules/README.md)、[backend/modules/README.md](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/modules/README.md)、[LICENSING.md](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/LICENSING.md) | 顶层 modules 说明独立仓库／另供商业模块；当前树顶层 modules 只有 README。backend/modules 有 ExampleHooks、ExampleShowcase、OrderPinger 示例。未取得商业模块源码或商业许可 |
| 本项目首版 AI 三项 | 本次 README、核心依赖 manifest、树路径定向检索 | 未定位可直接交付 AI-1/2/3 的证据；标“未验证”，不能把自动排产、普通预览或模块安装入口当成本项目 AI |

## 3. 许可资料与待项

这是许可事实登记，不是全依赖兼容性或法律合规认证。

- [LICENSE](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/LICENSE#L1) 是 GNU AGPL v3 正文；[LICENSING.md](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/LICENSING.md#L6) 将核心定义为 AGPL-3.0。后端 manifest 更明确写 `AGPL-3.0-only`。
- LICENSING 要求模块位于 modules 层且带指定 AFL 声明，不能仅凭目录名推断 AFL；其同时说明模块与核心要保持真正独立作品边界。没有审定任何商业／另仓模块的许可。
- `packages/ui` 声明 AGPL-3.0；`packages/module` 声明 AGPL-3.0-only；`mobile` 声明 AGPL-3.0-or-later。
- **元数据不一致：**[根 package.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/package.json) 声明 ISC，但顶层 LICENSE／LICENSING 和后端声明 AGPL。不能用根 npm 字段将整仓认定为 ISC。若分发根工具包或模块，需按实际文件和依赖清单处理此不一致。
- 本次读到的 [ExampleHooks 文件头](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/modules/ExampleHooks/Providers/ExampleHooksServiceProvider.php#L1) 未见所需 AFL 声明；只核文件头，不声称已审查全部示例文件。
- [Dockerfile](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/Dockerfile#L37) 在 x86_64 构建时下载 ionCube Loader；arm64 注释说明跳过。该下载物不是 AGPL 源码仓库内容，其再分发许可／可再现版本未核实。当前项目无需编码商业模块，不把它列为必需产品功能；构建是否保留需后续按实际范围处理。
- 交付资料需保留：对应源码版本、原 LICENSE／LICENSING 与实际使用的 AFL 文本（若适用）、第三方版权及许可、修改说明与构建材料。具体分发清单在选定底座和实际依赖之后完成，不能以本表替代。

**直接 PHP 依赖（固定 composer.lock 中元数据，不代表逐包全文审定）：**

| 名称 | 锁定版本 | 锁文件声明 |
|---|---|---|
| laravel/framework | v12.64.0 | MIT |
| laravel/octane | v2.17.4 | MIT |
| laravel/reverb | v1.10.2 | MIT |
| laravel/sanctum | v4.3.1 | MIT |
| inertiajs/inertia-laravel | v3.1.0 | MIT |
| spatie/laravel-permission | 7.1.0 | MIT |
| spiral/roadrunner-cli / roadrunner-http | v2.7.2 / v3.6.0 | MIT |
| barryvdh/laravel-dompdf / maatwebsite/excel | v3.1.2 / 3.1.69 | MIT |
| endroid/qr-code | 5.1.0 | MIT |
| picqer/php-barcode-generator | v3.2.4 | LGPL-3.0-or-later |
| aldas/modbus-tcp-client | 3.6.0 | Apache-2.0；设备采集不在本项目首版范围 |

来源：[composer.lock](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/composer.lock)。其余直接依赖已读元数据；传递依赖、容器系统包和实际交付物的完整许可清单未验证。

**网页直接依赖：**[package-lock.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/package-lock.json) 锁定 React/React DOM 19.2.6、Inertia React 3.3.0、Alpine 3.15.8、Chart.js 4.5.1，以上条目声明 MIT；lucide-react 1.28.0 声明 ISC。本地 @openmes/ui、@openmes/module 需按各自 manifest 许可处理。此处为关键清单，不声称已完成软件物料清单或漏洞审计。

## 4. 可复用运行入口

以下只登记真实文件中的入口，**本轮均未运行**。R04 如决定继续，先绑定隔离环境、固定提交和实际变量。

| 项目 | 已读入口 | 注意点 |
|---|---|---|
| 部署 | [README 安装段](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/README.md#L244)：Docker、Compose、Git；install.sh／install.ps1 或 docker compose up -d --build | 仅记录入口，安装脚本正文未在本次执行；不能照搬 README 克隆默认分支的步骤后冒称版本固定 |
| 运行栈 | [Dockerfile](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/Dockerfile)：php:8.3-fpm-alpine，Composer，npm ci/build，RoadRunner 2025.1.14；[Compose](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/docker-compose.yml) 使用 postgres:17-alpine、caddy:2-alpine | Composer manifest require PHP ^8.2、platform=8.3.31；构建镜像为8.3系列。Node 由 apk 装入，无单独精确 Node 镜像版本 |
| 服务数量 | [Compose](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/docker-compose.yml#L1) 默认 postgres/backend/reverb/caddy；设备连接服务与单独队列服务受 profiles 控制 | README “2 containers” 已不对应该 Compose，不能据此估部署成本。默认不增加本项目未要求的设备连接 |
| 首次迁移 | [docker-entrypoint.sh](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/docker-entrypoint.sh#L86)：主应用调用 artisan migrate --force、db:seed；sidecar 跳过迁移 | 首次启动会写数据库，后续必须使用隔离样例数据库；本轮未触发 |
| 后端测试 | [composer.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/composer.json)：composer test 调 config:clear 与 artisan test；[phpunit.xml](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/phpunit.xml) 指向 tests/Unit、tests/Feature | 默认配置 SQLite :memory:，不能据其将来成功推出 PostgreSQL 行锁／并发成功 |
| 网页测试 | [backend/package.json](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/backend/package.json) 的 npm test = vitest run；根有 playwright.config.ts | 根 package.json 的 npm test 是报错占位，不作为有效测试入口；未运行任何测试 |
| 备份 | [admin-guide](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/docs/admin-guide.md#L556) 给出 pg_dump 示例并要求备份数据库与 .env | 账号／库名须用实际配置；未执行。Compose 还有 backend_storage 持久卷，附件与配置应纳入实际恢复范围 |
| 恢复／升级 | [production-flow-deployment](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/docs/production-flow-deployment.md#L8) 说明停写、验证备份、迁移、匹配应用版本恢复及核对备份后的生产 | 已读文档中没有完整可直接复用的恢复操作脚本；完整恢复和一致性未验证，不将 migrate rollback 当作全量恢复 |

**部署冻结缺口：**应用 commit 已固定；PHP/PostgreSQL/Caddy 镜像标签仍是系列标签，Composer 使用 latest，ionCube 下载 URL 未固定内容摘要。R04 运行时需记录实际镜像 digest、架构、解析后版本和构建输出；这不要求现在替上游重写部署系统。

**资料冲突：**[docs/development.md](https://github.com/Mes-Open/OpenMes/blob/b952915bddb2120737f10a730a1e45b1d162c47e/docs/development.md#L34) 写 PostgreSQL 14+，README 写17+，Compose 固定17系列。候选核验优先照实际 Compose 的17系列记录；14版本兼容性未验证。README 仍列 Livewire4，但 composer.json 当前直接依赖没有 livewire；不凭介绍认定它是当前必需安装依赖。

## 5. 已读文件版本索引

下列是 **Git blob SHA**，不是仓库提交；全部来自本页固定 commit。

| 文件 | blob SHA |
|---|---|
| README.md | 8ed3b7bda69879b80456ad9d7b0a09945495ff1d |
| LICENSE | be3f7b28e564e7dd05eaf59d64adba1a4065ac0e |
| LICENSING.md | 8308dea30f4bfec43236a78f9d3a28d7fc8e6861 |
| backend/composer.json | 045781578da3c2b8c37414c707581c8209a0455f |
| backend/composer.lock | 5aa54f02faae51d25c65e9bf6b0152c195ee49a4 |
| backend/package.json | b706db714438c72007c2237113da6970eefefc52 |
| backend/package-lock.json | a5d4b89e5a2af44bce201883635720cb7c2dc255 |
| package.json | 40b02004decf2f5e01941bdbf6a3b4cc1b168cc1 |
| mobile/package.json | 0eb589601f6f49ed38f7e792a39f2e1213fa8e3d |
| packages/ui/package.json | a2ff9e6da818321f28e5a689b56a8209f07904ae |
| packages/module/package.json | fd6d1a94da1affce72cf820ca3802530afd55a8e |
| docker-compose.yml | 90bbbbb7a0b20e011361d7b5be6349798a28b5cf |
| backend/Dockerfile | 7b389b16a97a21b9c3035966689df23a41d45be2 |
| backend/docker-entrypoint.sh | aa5ede26e6823ea216f0f9402c3aa7681abd71e1 |
| backend/phpunit.xml | afae90f4841c1e42a1fbf3a67cc1b32580cd8648 |
| docs/admin-guide.md | e7bb71011537f4f39a56fb9385b33c9390d78141 |
| docs/development.md | e1e9cf412c7d3a49b1721fb05cb6727b61d3951f |
| docs/production-flow-deployment.md | a91736bae7184ab7a6ee5c58abedd927bba1b23d |
| modules/README.md | 26662219b43cc26e90619e9b02db81394e23e14d |

## 6. R01 判断

核心、PC网页、操作工网页及本地构建包可以定位到同一个公开固定提交，足够进入 R04 的限量适配判断。商业模块、首版 AI 完整能力、许可元数据冲突、ionCube 再分发与完整恢复仍有明确缺口。既有数量／原记录更正问题沿用任务卡的静态证据，不重复深审。本结论不选定底座，也不表示任何业务样例通过。

