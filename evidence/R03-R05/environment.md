> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R03～R05 本机与运行筛选记录

日期：2026-10-26（Asia/Shanghai）。范围：本机隔离候选核验，不是客户环境。

本页按阶段追加：前述无Web/未选型状态是首次运行历史；最新环境及收尾见末节。当前选型见[R06](../R06/selection.md)。

## 实际检查

| 检查 | 实际结果 |
|---|---|
| `uname -sm` | Darwin arm64 |
| `df -h .` | 工作盘可用52GiB（检查时快照） |
| `git --version` / `python3 --version` | Git2.54.0（Apple Git-157）/Python3.9.6 |
| `command -v` | Docker、Git、Python3可定位；Node、PHP、Maven、Bench在当前PATH未找到 |
| `/usr/libexec/java_home -V` | 没有可用Java Runtime；`/usr/bin/java`存在不代表JDK已安装 |
| Docker CLI / Compose / Desktop | 29.8.2 / v5.6.0 / 4.95.0 |
| 初始Docker访问 | 沙箱首次socket拒绝；提升后确认daemon未运行。不能将权限拒绝写成未安装Docker |
| `docker desktop start` | 退出0，输出Starting Docker Desktop；后续info确认服务已运行 |
| `docker info` | 服务29.8.2、aarch64、8CPU、4106604544字节内存（约3.82GiB） |
| `docker ps` | 无运行容器；未修改已有容器或镜像 |
| 已有镜像 | 有其他项目镜像；无本次ERPNext镜像，不清理已有资产 |

启动Docker属于本次隔离核验准备，不是安装/升级Docker。未全局安装JDK/PHP/Node/Bench，未修改Docker资源配置。

## 限量运行决策

- R03：Gitee PC通过提升后的只读Git获取成功，上一轮缺口已部分关闭；源码显示两位数量字段、报工审批、自动耗料等差异。详见[R03矩阵](../R03/fit-matrix.md)，本轮先保留静态结果，不安装。
- R04：同仓源码可读，但数量、冲销、任务授权、领退耗与网页入口存在需要进一步改造/核实的差异。详见[R04矩阵](../R04/fit-matrix.md)，本轮不优先安装。
- R05：固定15系有可定位的领WIP/制造/退余料路径及原生定向测试，选择一个候选做运行先导。不是选定最终底座，不表示其精度/冲销已符合要求。

## ERPNext隔离运行基线

- 官方容器资料固定：`frappe/frappe_docker@2e6c8573a2af9882df705ce4247a26eb69c4f597`。已读[pwd.yml](https://github.com/frappe/frappe_docker/blob/2e6c8573a2af9882df705ce4247a26eb69c4f597/pwd.yml)，blob `dc8a1ec4baa34596e0b02e003f3f72670215e377`；原配置是v16.52.1和MariaDB11.8，不照抄为本次15系。
- `docker manifest inspect frappe/erpnext:v15.124.1`成功：ARM64子摘要`sha256:4160d3c77aafb41c7770aad3daa67254a13f8750765ee83d632434ed564a4834`；AMD64摘要`sha256:6026efbd4928f652dc5f9d83cb8936298c8cca346237844a9ceaa364676700aa`。选择ARM64，不使用跨架构模拟。
- 已读固定[Frappe兼容检查](https://github.com/frappe/frappe/blob/f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab/frappe/database/mariadb/setup_db.py#L100)，blob `aec4497bcca1d4ecc7ef67063e1cf3bc9513fec5`：低于10.6不支持、10.9以上未测试提示。本次选择10.6系列核验；这不证明任意补丁版本已兼容。
- 只用独立项目名/卷/样例站点。先核镜像内实际ERPNext/Frappe版本与R01是否一致；不一致时先记录差异再决定继续，不能以镜像标签代替源码身份。
- 应用实际启动、测试与停止状态只在[R05运行记录](../R05/run-record.md)登记；本页不预填通过结果。R02算术核对结果不能计入候选运行结果。

## 实际环境补充

- 镜像已拉取并成功执行版本读取：ERPNext15.124.1、Frappe15.124.0、Bench5.31.1、Python3.11.17。官方镜像没有`.git`，不能读取仓库HEAD；另以Git blob算法比对工单、作业卡、库存单及对应测试、Frappe精度与测试命令共8个文件，全部与R05固定源码相同。只证明所查文件一致，不夸成全镜像逐文件审计。
- 一次使用`bash -lc`时Node因登录shell PATH未定位而使后续串行命令中断；正常非登录容器环境中Node路径为`/home/frappe/.nvm/current/bin/node`。没有因此认定镜像缺Node或安装Node。
- 17:38 Docker日志记录`actionMenuQuit`、electron请求backend shutdown、正常退出；不是本轮已证明的崩溃。用户随后明确“我又重新打开了，你再试一试”；继续核验后Docker info恢复成功。
- 隔离配置保存于[compose.json](../../.evaluation/r05-erpnext/compose.json)，项目名`xgd-r05-20261026`。仅db、redis-cache、redis-queue及按需CLI容器；无宿主端口，无客户数据。随机测试凭证保存在该目录`.env`、权限0600，未写入本报告。
- MariaDB实际镜像：`mariadb@sha256:88ac718dafee1e8fb415233c04f314f3c3866af99177ce25d436106c62090461`，arm64，413615122字节；Redis：`redis@sha256:592b215e9287182f11ba9d7c229dc0ba312bb900a016ea65ae378b0127567319`，arm64，41918577字节。Compose的系列标签与本次实际摘要同时保留，复验应按摘要而非猜测未来标签不变。
- 新站点`r05.localhost`已在独立卷完成Frappe与ERPNext初始化，命令退出0；scheduler为disabled。初始化日志见R05/site-init.log（仅本地保留；见 publication/evidence-index.json）。没有打开公共网站或模拟客户上线。

## 本轮结束状态

- 真实运行结果见R05记录第5节：4个上游定向测试、两条数量主链子集及有限精度/边界观察，未完成整卡验收。
- 最后新连接回读的时间为2026-10-26 10:23:03 UTC；站点仍保留合成数据，原制造/精度/舍入配置已恢复。
- 已执行`docker compose -f .evaluation/r05-erpnext/compose.json stop db redis-cache redis-queue`；随后`ps --all --format json`确认三个服务均`exited`、ExitCode=0，见原始状态（仅本地保留；见 publication/evidence-index.json）。没有删除卷/镜像或停止Docker Desktop。
- 本地文件链接、33张任务编号/依赖和停止状态复核见document-check.json（仅本地保留；见 publication/evidence-index.json）。这是文档检查，不计为产品测试。

## R05补证阶段环境与最终停止状态（19:24北京时间核对）

- 新增本机Web评估服务：[compose.web.json](../../.evaluation/r05-erpnext/compose.web.json)，复用原站点/卷和固定应用镜像，官方entrypoint，`bench serve --noreload`、CI=1；只绑定127.0.0.1:18085。没有对外开放端口，没有websocket完整服务，不是生产部署包。
- 最初绕过官方entrypoint导致sites/assets未准备、登录返回500；读取官方脚本后改回官方entrypoint，登录成功。只改评估配置，没有改产品代码。浏览器socket.io错误仍保留，不宣称实时通知正常。
- 本轮物料/权限/并发/小屏合成样例分别在R05三个补证报告记录。新普通用户凭证单独0600存放并忽略，不进入证据；原始客户数据没有进入站点。
- 中断后恢复：Docker socket一度不存在；随后`docker desktop status/start`显示running/already running，使用同项目两个Compose文件恢复db、redis-cache、redis-queue、web，返回healthy。旧浏览器tab已不存在，另建测试tab；没有重建站点、重跑已完成测试或重复提交原单。未据此推断是谁关闭服务。
- 小屏操作结束恢复默认浏览器尺寸。库存普通账户最后新连接回读见issue-submitted.json（仅本地保留；见 publication/evidence-index.json），原有提交与新提交分别保留。
- 已执行`docker compose -f .evaluation/r05-erpnext/compose.json -f .evaluation/r05-erpnext/compose.web.json stop web db redis-cache redis-queue`，命令退出0。日志（仅本地保留；见 publication/evidence-index.json）、最终容器状态（仅本地保留；见 publication/evidence-index.json）确认四个服务均exited；db/两个Redis ExitCode=0，Web ExitCode=137，不能写成四个都正常退出。Web详细状态见web-final-state.json（仅本地保留；见 publication/evidence-index.json），保留原始停止码，不把停止动作写成业务测试失败。
- Desktop状态（仅本地保留；见 publication/evidence-index.json）确认仍running。没有删除卷、镜像、原始文件或其他项目数据。
- 文档和证据检查见[R06/document-check.json](../R06/document-check.json)；不计为业务通过数。
