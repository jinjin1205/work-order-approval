> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B19剩余项本地验收记录（2026-10-31）

**结论：B19仍为部分完成。** 本轮补齐原卡余2～余5的下述限定缺口，并完成企业微信群机器人适配的本地验收；没有真实群发送、客户部署或B18现场验收。原TODO、任务卡勾选、交接与提交按用户要求延后。本记录是证据，不是第二份任务清单。

## 范围和版本

- 唯一任务来源：`docs/任务卡/02-生产与物料闭环.md`原B19余1～余6；实施绑定：`evidence/R07/approval-binding.md`本轮追加段。余1停止后关联新单引用B17真实HTTP证据，不重跑。
- ERPNext 15.124.1，开发分支`codex/xgd-maintenance`，基底`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；Frappe 15.124.0。根目录不是Git仓库，源码在`.development/repos/erpnext`。
- 复用既有OpenSpec 1.15.0、Playwright CLI 0.1.22和技能，不安装或升级。OpenSpec沿原卡引用，不复制清单、不勾选或归档。
- 仅改5个产品文件：原`work_order.py`、`production_quality.py`、`hooks.py`，新增`manufacturing/permissions.py`及`approval_notification.py`。不改Frappe，不新增业务字段/DocType、锁、重试或多渠道平台。
- 隔离验证：`xgd-test.localhost`回滚测试；`xgd-b08-http.localhost`专用持久站，普通测试岗位，非B18人员。真机、开发/客户启用及正式交付没有据此完成。
- 最终[运行源码清单](source-manifest.json)：51文件含全部未跟踪产品文件，27个Python；两个容器逐文件匹配并编译通过。累计tracked diff SHA256为`d379c8c82e4b0d3b892cf3d388d1aff99050ad5869974b735b1a0155f3643c21`，B19相对本轮before副本的完整增量SHA256为`f3256ccbe14a840f16f8c546c0864adc17acbfe0cacdc9a04ef676488db84151`。tracked diff本身不包括未跟踪文件，不能单独代表候选源码。

## 本轮实际结果

| 原剩余项 | 实际完成与依据 | 限制 |
|---|---|---|
| 余2 页面/配置 | 普通岗位真实网页新建空明细、预览确认、送审；390×844审核退回、改交期再送审、签批人取消；原修订空草稿保存并终止；有领料后窄屏停止。中文状态/原因可查，停止原因在Comment，不能冒称approval_note字段有值 | 桌面窄视口，不是真手机；SSO/企业微信内置浏览器未验 |
| 余2 可重复配置 | 只读导出[原生Workflow配置](production-workflow.json)，原生import_doc在回滚fixture连续导入两次；单流程、旧单不误批准、原业务/待办不变 | 需要既有角色/字段，不等于Z01干净环境配置交付；未在客户站启用 |
| 余3 附件/依据 | 两轮送审：交期11-07/1份附件→退回→交期11-10/2份附件；原Version日期差异、Comment时点、File字节/MD5及送审HTTP快照相符。3工序/1用料输入保持；签批派生排程单列。改名/删/改挂/覆盖/公开别名/晚加均被拒，退回后新版本可编辑并再次冻结 | 只核本样例本地私有文件；外部URL版本、历史公有迁移未验 |
| 余3 历史读取 | 原父工单docinfo真实HTTP：合法审核200、撤对象范围403、跨公司403。普通Desk可见两版附件、两轮送审、退回原因和交期差异 | 直接`/app/version/...`被原岗位Page权限拒绝；未赋予全库Version读取。父单活动入口与管理员只读还原不等于独立Version页通过 |
| 余3 日志配置 | 只读检查实际Log Settings：存储清理规则为空，scheduler暂停；保留默认hooks记录；未发现四类保护记录的显式清理条目 | 未运行清理，也未核客户站、90天实际留存 |
| 余4 权限差集 | 跨公司签批拒绝；撤审核角色后仍有父单read正例但审批动作403。Workflow Action原生岗位/Open条件叠加父工单read；跨公司列表为空、单张403，select-only不扩大读取，单张分享只限该父单；like/%/引号/!=保留 | 只补原矩阵差集，不宣称所有客户岗位组合已验 |
| 余5 限定事务 | 四组独立进程一次性实跑：同版本双签仅一次成功；签批/撤回仅签批生效、旧撤回失败；签批/领料观察到父锁等待，批准commit后仅一笔领5；写审批Comment故障前已实际更新docstatus1，rollback后新读仍待签批/0且选定原行/数量一致 | 不是完整G3/全部库存竞争。已验四组未重跑；前两组早期source仅保存脚本hash，后两组另有完整当时运行清单，不伪称四组均采集最终候选清单 |
| 余6 企业微信 | 按用户选择只做群机器人，B19绑定审批群；原生系统待办保留。仅显式配置后，审批成功写审计且转待审核/待签批才登记提交后通知，回滚不入队。队列只带脱敏号和状态；worker读受限env；HTTP、业务码、非法响应、超时均明确失败，日志不存密钥URL、原响应或异常原文；不影响审批事实 | 8项本地受控验收通过；未启用真实配置、未发群、未证实消息送达或常驻worker可用 |

## 反例、修补和最终验证

1. 最初真实File改名/删除/改挂均未拒绝；先保留失败，再复用现有File扩展与送审Comment时点保护已纳入依据的附件。
2. 跨公司账号父工单read/sign均403，但原生待办列表/单张曾200；新增父单read条件，复用原生岗位和现有`_read_match`，不新建权限引擎。
3. File owner撤Company范围后父单403、File元数据/私有URL仍200；补父单read。原File列表已正确为空，不重写其查询。
4. 一次最终只读审查提出2个具体输入问题，均实际复现后修补：私有声明加公有URL会被原生规范化为公开；无关File同时改目标URL/私有性会移动冻结依据。修补仅在规范化后校验新File，并按实际移动URL和原生更新涉及的hash检查别名。原审查“No”报告保留，不冒称再次审查通过；两项用反例RED→GREEN关闭，无Minor遗留。

最终实际命令（工作目录为项目根目录）：

```sh
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b19_remaining_tests.py
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b19_remaining_notification_tests.py
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b19_remaining_tests.py erpnext.stock.doctype.quality_inspection.test_quality_inspection.TestProductionNativeQuality.test_draft_image_delete_allowed_but_cancelled_history_frozen erpnext.stock.doctype.quality_inspection.test_quality_inspection.TestProductionNativeQuality.test_locked_image_cannot_be_public_or_replaced erpnext.stock.doctype.quality_inspection.test_quality_inspection.TestProductionNativeQuality.test_unrelated_unattached_file_preserves_native_owner_permissions
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/b19_remaining_basis.py
python3 .development/checks/b19_remaining_history_http.py
python3 .development/checks/b19_remaining_review_http.py
python3 .development/checks/b19_remaining_review_http.py verify-retained
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b19_remaining_source_check.py
docker exec -w /home/frappe/frappe-bench xgd-b08-ui env/bin/python /b01/b19_remaining_source_check.py
git -C .development/repos/erpnext diff --check
```

| 最终日志（本机受限目录） | 实际结果 |
|---|---|
| `review-final-targeted-tests.log` | 13/13，126.564s，35旧表保持；各方法fixture都经过本次修改的新File入口 |
| `notification-final-fixed.log` | 8/8，26.016s，35旧表保持；真实本地HTTP、原生队列及审批fixture，未实发 |
| `review-affected-quality-files.log` | 3/3，43.766s，35旧表保持；仅变动入口直接受影响分支 |
| `review-file-inputs-red.log` / `review-file-inputs-green.log` | 两项先均未抛PermissionError，后2/2通过（15.851s） |
| `review-file-http-retained.log` | 重启UI后两种输入各403；原依据仍私有，下载200且字节MD5不变；2个合成File对照已删除 |
| `history-docinfo.log` / `basis-inspection.json` | 原历史授权/撤权边界及两轮依据核对通过 |
| `race-*.log` / `races/*/summary.json` | 四组限定调度一次实跑通过；raw失败与rollback证据保留 |
| `xgd-b08-*-final-source.log` | 两运行容器51文件匹配/27Python编译通过，UI已重启加载 |
| `final-business-audit-reviewed.json` | 37旧表原记录保持；本轮8工单、0生效报工、2库存单 |

原始日志位于`.development/private/b19-remaining-20261031/`，不直接发布凭据、登录脚本或运行数据。页面Playwright操作及快照/截图同目录；本轮专用浏览器会话已关闭。

验收脚本的真实错误也保留：首次登录域名混用后更正并轮换本轮测试账号口令；初次fixture导入早于Frappe初始化；通知脚本误计原生缓存回调后改为仅筛本模块；最终HTTP脚本曾误将已有下载helper返回dict当tuple解包，HTTP已执行且finally已清理，之后只核对保留响应和原始字节收口，没有重发已验请求。这些退出不得写成当次命令通过。UI有socket.io 404的环境限制；依赖输出Python支持期FutureWarning，未擅自升级。

## 企业微信实际接入尚缺条件

用户授权范围为三个B18试点群内经负责人确认的角色账号。本卡只给“B18试点-总装二车间审批群”提醒，其他两群不自动接收审批消息；不接钉钉。群成员/机器人归属和试点结束后5工作日清理需现场负责人落实，本机未核验。

用户给出的登录URL明确标注“示例域名，实际部署时替换”，不能作为可达性、SSO或403测试结果。本机实际检查`/etc/b18-pilot/secrets/local.env`不存在；Windows路径也是部署模板。没有读取或搜索其他项目密钥，没有访问示例域名或发送消息，更没有登记“已发1条”。

适配已支持：服务账号可读且其他账号无文件权限的env文件，唯一键`B18_ASSEMBLY_APPROVAL_WEBHOOK`；站点配置仅设`xgd_wecom_robot_secret_file`与`xgd_wecom_login_url`，后者须实际无凭据HTTPS登录地址。配置前不启用；部署时需确保该Webhook确属审批群、worker具有只读密钥文件权限且队列可运行。消息只含不可逆脱敏工单标识、审批状态、待办提示和通用登录链接，无原工单链接、姓名、材料或价格。

实际条件齐后才可向该获准群发送1条脱敏验收通知，分别核接口接受、群内实际收到及实际登录权限。协议依据：[腾讯CloudBase企业微信群机器人官方示例](https://docs.cloudbase.net/recipes/connect-wecom-webhook-cloud-function)；本实现检查`errcode == 0`，不能用HTTP 200代替业务接受，更不能用业务接受代替群成员已读。

## 保留边界

- 独立Version页仍按原岗位拒绝，仅父单活动/附件入口实际可用；外部URL版本、客户历史公有文件不迁移、不删除。普通岗位完整独立Version页不是本轮通过项。
- B18真实现场/4周观察、B13真机、此前B14/B15等未验证项、完整G3、Z01/CASE-11均保持原状态；没有用本轮有限结果关闭整卡或正式交付。
- 沿用户约定保留开发分支和所有累计改动；无commit/push/PR，没有新提交SHA及本轮CI结果。公开发布checkout本轮未同步，不把本地保存称远程交付。
- 33份原AGENTS/TODO/决策/任务卡/OpenSpec文件hash保持；不改旧勾选、不重复新建TODO或交接。
- 未运行ERPNext全套测试；本轮按变动的共享File入口、审批/待办及单渠道适配做绑定的定向验证，未变已验项不重跑。
