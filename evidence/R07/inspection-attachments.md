> 公开归档副本（2026-10-30）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R07 · 原生报检与私有图片绑定（2026-10-30）

用户已明确“暂不新增字段，先推进原生报检/图片”。唯一任务清单为原B08本包；B14仅消费现有字段/角色/附件配置，不另建清单或配置表。

## 做什么、不做什么、怎样通过

复用原生Quality Inspection引用本笔已确认Job Card，作为后续追加质检单；图片挂原生质检草稿，由有权限的普通质检岗位人工填写检验数量、结果并提交。报工页提供原生新建/查看关联入口；不能把草稿或预填值称为已检，不能自动确认合格/不合格。原报工的数量、工时、快照和整行原值保持。

不新增字段、DocType、存储服务、通用附件平台或质检审批流；不让质检改生产/库存事实，不自动返工、扣料或改报工数量。不授予操作工系统管理员或整个质检经理角色；合成质检用户用原生Quality Manager并明确授权只读生产记录，客户角色初始化仍待相应验收。时段、计价、已验报工/并发/导航冻结；现场10秒、手机、完整G1/G2/G3与Z01仍未验。

原生复用能运行、正常/无权/跨对象/撤权/单张分享有明确结果，质检与图片可由中文PC保存/提交/重开且原报工不变；已提交/取消质检及其图片不能改挂、覆盖或删除，失败不损坏原二进制。无关原生质检/文件正常；旧捕获行、库存保持。满足本包条件即停止，不重复其他验收。

## 实时依据与必要适配

基线公开main `13f7f6f`，ERPNext15.124.1/Frappe15.124.0；维护分支codex/xgd-maintenance，上包36份源清单实际一致。当前隔离站仅6个既有审批Custom Field定义，原生质检数/Job Card附件数/质检附件数均0；不是客户环境普查。用户已明确不新增自定义字段。Custom Field原生配置角色为Administrator/System Manager，不能因已有时段配置权自动获得元数据管理权。

`Quality Inspection`已有company、reference_type/reference_name、item_code、sample_size、inspected_by、status及manual_inspection；Job Card已有quality_inspection及template，原生JS支持In Process/Job Card默认引用。原生validate会由引用取得公司。`quality_inspection.py:update_qc_reference`会SQL回写Job Card的quality_inspection与modified，和已确认报工保留要求冲突，须对本项目确认事实跳过回写，仍使用质检单原生反向引用。

Frappe File已有私有附件、上传与磁盘回滚机制；原生owner权限可直接删除，on_trash会进入二进制删除。须在父记录锁定时于原生删除前拒绝，并使私有读取随父对象授权撤销。用ERPNext合法扩展点，不改共享Frappe；不凭静态核对称运行安全。

## 产品白名单（5文件，无元数据变更）

1. `erpnext/manufacturing/doctype/job_card/job_card.js`：仅本项目已确认记录的原生新建/查看质检入口；按当前原生权限提示，不自动保存或填写检验结果。
2. `erpnext/stock/doctype/quality_inspection/quality_inspection.py`：项目引用校验/原引用保护、保留已提交与取消历史，跳过项目事实的原生回写；其他业务继续原链。
3. `erpnext/manufacturing/production_quality.py`（必要最小新增）：限定项目质检/图片父对象判断；原生权限谓词/DatabaseQuery复用，读写不因文件owner或分享绕过父对象；File子类在原保存/删除前执行私有图片及历史保护，之后调用原控制器。无关File完全委托原实现。图片限本包支持的普通栅格图，校验真实内容，不接远程URL。
4. `erpnext/hooks.py`：登记上述File控制器扩展和File/Quality Inspection权限/查询入口，保留已有Address等映射。目标是局部保护，不改Frappe。
5. `erpnext/stock/doctype/quality_inspection/test_quality_inspection.py`：复用B08真实审批/报工fixture，先最小P0；再精确红例与修补、必要正常/失败路径及无关原生正例。

## 验证、配置及证据

复用原runner：`docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py <测试完整名>`。只运行本包及实际受影响原方法，不装Payment Gateway或重建依赖。允许`.development/checks/`为独立样例补原生质检角色/只读父对象、图片、普通用户和旧行/原值哈希；不改原用户与权限矩阵，不重放已消耗样例。File测试仅清理本例新建文件，可靠finally/原生回滚，不加生产测试旁路。

网页用Playwright CLI普通质检岗位完成原生新建、手工填写、私有图片上传、保存/提交/重开；操作工无质检权有明确提示，跨对象与撤权拒绝。读取/列表/下载、已锁File删除失败均核真实记录与二进制；每批源版本、输入、输出、限制记`evidence/B08/quality-20261030/`。新增控制器同步后清必要hook/controller缓存并重启专用Web，浏览器实际行为不由磁盘哈希代替。

五底座及许可证结论沿原R03～R07：当前主要底座仍ERPNext，不另装模块/第二账。新File扩展只核当前Frappe/ERPNext两app组合，其他客户插件组合待Z01，不能预先声称兼容。

## 独立审查后限定补充（仍同5文件）

原生私有下载直接走File.is_downloadable，不只走通用权限钩子；分享还有原生兜底。故本包私图以父报工单张分享和既有质检角色为准，禁止项目QI/File独立分享绕开父对象（普通原生分享不变），File下载及Doc检查都核父授权，列表同样过滤；不自动分享父报工。当前试验站此前QI/相关附件/其独立分享均0，不迁移或清理客户分享。

取消入口另校持久数据，只允许系统取消字段变化；质检删除附件须在父行仍存在时按原生清理，以保留带图草稿删除正例。File原生私有性规范化处再核实际值，影响共享二进制/私有性的修改先查受保护别名，不能经普通File移动或公开受保护图片。以上先补对应真实反例，不假定仅一般权限False即安全。

同一File原生源码另有批量zip下载直接调用模块权限、图片优化先覆盖磁盘再save两条具体入口；在原五文件内将zip API登记到薄权限前置再调原函数，File覆写写盘前拒绝受保护共享路径的overwrite。不改zip打包或图片优化算法；先补真实反例，只重测这两个新入口与受影响正常路径。
