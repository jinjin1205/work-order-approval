> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B01 独立中文环境执行记录

2026-10-26。用户明确授权执行B01。本轮仅开发环境、源码绑定、中文初始化与必要验证；不实施B02/B10产品修补，不访问客户数据，不修改R05库。

## 执行状态

**环境子项完成；原生测试基线未通过，B01整卡保持部分完成。**工作区原本不是Git仓库，无附加worktree；按原卡在`.development/repos/erpnext`取得完整固定源码，不创建空业务仓库或重复工作树。沿用原证据目录作为执行台账，不新增技能专用计划副本。

## 已核环境与前置

- 本机Docker为Linux/aarch64，8 CPU、约3.82 GiB；固定ERPNext、MariaDB、Redis镜像已缓存。
- R05四项服务本轮开工时均exited；仅作为历史模板，不启动、不改其数据卷。
- R07的G1/G2/G3是后续技术适配/验收门槛；不阻塞B01。25张未完成卡不是25项技术故障。
- 目标：`.development`新Compose项目`xgd-dev`，两个独立用途站点，简体中文/上海时区/CNY。测试使用自带隔离fixture。

## 偏离与判断

- 本轮是配置与环境交付，使用原生验证入口及正常/失败操作，不为配置写镜像实现的测试或制造业务补丁。
- 源码绑定先证明固定checkout实际被运行；之后B02/B10改动再核变化文件与反例，不能将本次基线成功当未来补丁通过。

- 初始化首次调用在bench根目录进入Frappe，日志相对路径误指向`/home/frappe/logs/database.log`，连接数据库前失败。按原CLI工作目录约定改为先进入sites后init；只改B01初始化脚本，保留`dev-setup.log`原失败。

- 基线首次`--module ... --test test_warehouse_user`执行1项后报缺`_Test Warehouse 1 - _TC`；CLI在非CI环境竟退出0，因此按日志判失败。固定runner源码显示`--doctype`会递归创建fixture，而模块入口仅处理显式test_dependencies；改用原生`--doctype 'Stock Entry'`，并加CI=1保留失败退出码，不改测试断言。
- 首次JUnit参数缺目标文件，CLI退出2且未运行测试；补参数后发现镜像未装可选`xmlrunner`，测试尚未开始。取消可选XML报告，不为报告格式安装整套dev依赖，保留文本结果和CI退出码。相关日志分别保留，未算测试通过。

- 中文向导生成中文根节点，但上游fixture硬编码英文名称；`before_tests`在已有公司时不再英文初始化。`warehouse-baseline-doctype.log`在装载样例时失败，不算执行业务断言。只在测试站点将五类唯一根用原生重命名适配，开发站点不动。Department无公司根的简称hook不适用，显式执行原生`validate_rename`后调用底层`rename_doc`，保留权限/命名/冲突校验和链接更新。首次误调用顶层包装函数不接受validate参数，退出1并回滚；改用已核底层函数后成功，见`test-fixture-adaptation.log`。没有修改ERPNext/Frappe或测试断言，没有创建第二根。

- 首次五类根适配后出现同类Sales Team缺失；静态扫描全部`test_records.json`的parent引用，确认第六类Sales Person根，回读为“销售团队”。只补该同类映射，前五类仅核对。见`test-fixture-roots-after-first-adaptation.json`和`test-fixture-adaptation-complete.log`。
- 最终`warehouse-baseline-final-result.log`退出1：递归装载测试依赖时报`DocType Payment Gateway not found`，未进入本次测试断言。该阻塞不同于根名称差异，本轮停止扩展，不增加支付模块、不删断言、不反复复跑。测试基线保持未通过。


## 本轮结果与证据

记录时间：2026-10-26，Asia/Shanghai。验证属于本机受控运行，不是客户部署或现场验收。

| 检查 | 输入/动作及实际结果 | 证据 |
|---|---|---|
| 固定源码 | ERPNext v15.124.1，HEAD `4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，维护分支 `codex/xgd-maintenance`；Git工作区无业务修改 | [源码记录](checkout-final.json)、克隆记录（仅本地保留；见 publication/evidence-index.json） |
| 构建与运行 | 固定官方镜像上复制上述完整checkout，复用同版本依赖和静态资源；构建成功。实际Bench与Web均为ERPNext15.124.1/Frappe15.124.0，三个业务模块解析路径正确，10个选定文件哈希与checkout一致 | 构建（仅本地保留；见 publication/evidence-index.json）、Bench绑定（仅本地保留；见 publication/evidence-index.json）、最终Web绑定（仅本地保留；见 publication/evidence-index.json） |
| 服务隔离 | 项目`xgd-dev`独立网络/卷；Web只发布`127.0.0.1:18086`。开发库`_6eac624149b820fe`与测试库`_880dfa6b9f4528c3`不同；仅测试库开启allow_tests | 最终服务（仅本地保留；见 publication/evidence-index.json）、最终镜像/挂载（仅本地保留；见 publication/evidence-index.json）、数据对比（仅本地保留；见 publication/evidence-index.json） |
| 中文初始化 | 原生完整向导：中国、中文、上海时区、CNY；两站回读一致。普通账号仅用于环境登录，非System Manager。开发库工单/报工/库存单均0；测试库留有原生fixture产生的2张库存单，不冒充断言通过 | 开发回读（仅本地保留；见 publication/evidence-index.json）、测试回读（仅本地保留；见 publication/evidence-index.json） |
| 登录与失败 | 浏览器普通合成账号登录、退出后重登成功，首页中文；一次故意错误密码显示“登录无效，请重试”，随后正确密码可重新进入 | 首页（仅本地保留；见 publication/evidence-index.json）、错误密码（仅本地保留；见 publication/evidence-index.json）、重登文字（仅本地保留；见 publication/evidence-index.json） |
| 启停与保留 | 首次四服务停止/启动后，两站回读配置和记录数量相同，中文首页可打开。首次Web默认SIGTERM退出137，不能算正常退出；仅配置`stop_signal: SIGINT`后再停Web，退出0且OOMKilled=false；再次启动后首页仍可访问 | 初次停止（仅本地保留；见 publication/evidence-index.json）、重启（仅本地保留；见 publication/evidence-index.json）、持久化对比（仅本地保留；见 publication/evidence-index.json）、修正后退出码（仅本地保留；见 publication/evidence-index.json）、最终启动（仅本地保留；见 publication/evidence-index.json）、重启中文图（仅本地保留；见 publication/evidence-index.json） |
| 错误配置 | 缺DB密码的Compose配置校验明确退出1，不启动、不写库；密码文件0600且排除构建/版本管理 | 拒绝记录（仅本地保留；见 publication/evidence-index.json）、[权限元数据](checkout-final.json) |
| 原生测试 | `CI=1 ... run-tests --app erpnext --doctype 'Stock Entry' --test test_warehouse_user --failfast`最终退出1，依赖装载缺`Payment Gateway`，没有本次断言通过结果；前期失败均保留 | 最终失败（仅本地保留；见 publication/evidence-index.json）、fixture适配（仅本地保留；见 publication/evidence-index.json） |
| 原环境与上游CI | R05四项服务前后均exited，本轮未对其DB执行命令。已读上游`.github/workflows/server-tests-mariadb.yml`，含专用runner/测试分片；未接入或触发远程CI，未改上游CI | R05状态（仅本地保留；见 publication/evidence-index.json）、CI源码（仅本地保留；见 publication/evidence-index.json） |

## 最小处理与保留边界

1. **已做：**环境配置、中文向导、原生账号、源码绑定检查、测试站点fixture名称适配和停止信号修正。无ERPNext/Frappe产品代码差异，无B02/B10修复结果。
2. **不把测试失败变成安装扩张：**缺`Payment Gateway`发生在上游递归样例装载，不足以断言生产权限功能有缺陷，也不能称测试通过。下一步在B02范围准备其最小原生样例，先验证测试能执行，再修已绑定辅助接口；B10按自己的物料样例条件处理。保留本基线失败，不要求先装支付功能或跑全套ERP测试。
3. **数量仍未达标：**向导原生3位/银行家舍入未改；G1十进制与损耗、G2逐笔事实与最小岗位、G3全部必要入口并发仍未验证。
4. **中文范围：**已验初始化、登录、重登和首页。原生“报告 & 大师”“ERP下载设置”等术语及搜索辅助文本英文残留已观察，归B14/所属业务页处理；不宣称所有页面已完成中文交付。测试库内部英文fixture名称不用于产品英文版本。
5. **构建范围：**当前COPY复用同版本静态资源，10个选定文件匹配不等于全镜像审计。后续业务补丁须重建并核变化文件；JS/CSS、依赖或元数据变化按原生构建/迁移处理。删除/重命名文件时需处理基础镜像残留。
6. **开发环境范围：**未配置完整worker/websocket/生产反代；客户部署、备份恢复、生产性能、团队CI和现场验收未验证。环境账号只有登录验证用途，不能当作最终岗位权限方案。

## 操作与交接

- 本机网页：[中文开发环境](http://127.0.0.1:18086/app/home)。当前保持运行，普通账号`b01.operator@example.invalid`；密码只读本机`.development/.env`，报告不保存凭据。
- 首次创建、启停、源码重建和测试命令在[环境说明](../../.development/README.md)。已有站点不重新创建；不删除卷、不修改R05。
- 原33张卡不新增：R00～R06共7张完成，R07/B01部分完成，另24张未完成。B01环境子项交接不代表整卡或其他门槛通过。
- 本轮结束于上述环境与失败证据；下一项为B02最小样例与辅助读取权限子项。B10实耗单位仍在其样例就绪后进入。首版AI三项和中文服务中国公司的目标不变。

**只读复核：**已核环境隔离、秘密排除、实际Web源码绑定、测试失败状态和结束条件。修正B01旧文“完成环境即关闭”与整卡缺口的矛盾；现在只关闭环境子项，测试基线与团队条件保持可见。复核未操作数据库或读取密码。
