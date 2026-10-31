> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# A01结构化草稿与确认边界：本轮验收记录

2026-10-31。沿原总TODO第6步推进A01，不回跑B19或前卡。**本轮不依赖C06的结构化边界包已实现并验收；A01整卡仍部分完成，真实模型未调用。** 用户本轮确认C06“待定”；A02字段候选、A03语言/语音识别仍归原卡，不用本包替代。

## 范围与版本

- 原依据：`docs/任务卡/03-AI与交付.md` A01、CASE-09、`evidence/R07/card-binding.md`本轮A01绑定。先核前置再实施；TODO页首停在B11是延后统一更新，不据此重做B12～B19。
- ERPNext15.124.1维护分支`codex/xgd-maintenance`，基底`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`；Frappe15.124.0。承接B19最终51文件候选。
- 产品/测试增量共4文件：新增`manufacturing/production_ai.py`、`manufacturing/test_production_ai.py`，修改原`doctype/job_card/job_card.py`与`doctype/work_order/work_order.js`。不改Frappe，不新增字段/DocType/锁/草稿事实库或模型平台。
- 复用原B02读取权限、B04计算、B08/B09原确认/防重/事务，以及原JSON快照；OpenSpec继续原卡引用模式，不复制清单、改任务勾选或归档。实际使用已安装ego-browser做网页验收，不重复安装工具。
- 最终[源码清单](source-manifest.json)含53文件（包括新增未跟踪源码）、29个Python；两个运行容器逐文件匹配及编译通过。累计tracked diff SHA256 `c8880ca5ec036d29439ab6ed70b409d28f747c288947cc0f91ef6ab0a06785fe`；A01相对本轮before的完整4文件增量SHA256 `97e293e5ea78c98bd04f795854133439dd2e98f6f419ab18287cbeff1ee2bda0`。tracked diff不含未跟踪文件，不能单独代表候选。

## 实际行为及结果

| 项目 | 实际结果 |
|---|---|
| AI只读取数 | 新工具只接受工单ID，先原生WorkOrder.read，返回对象/版本、状态、单位及已有工序计划/良不良，不返回全单、员工、工资或BOM原文；不接受SQL/任意字段查询 |
| 只读身份写入边界 | 专用普通reader取上下文成功；真实HTTP调用原正式报工、停止审批及领料生成均403。工具本身不新增写入授权 |
| 结构化建议 | 人工导入只接受原6个输入：良品、不良、实际起止时间、停工/加班秒数。未知/注入字段及错误数字拒绝，复用原校验；草稿只在响应和当前浏览器内存，不创建业务单据 |
| 缺项和取消 | 8良2不良缺实际时间时两时间框为空；取消后实际审计为报工0、库存0。原可选停工/加班默认0保留，不能把缺实际时间填为now |
| 人工确认 | 页面人工补实际时间后，原生预览计算有效3600秒、实际效率10Nos/小时；工资/标准未配显示未配置/—。点击原“确认报工”后，只有1笔已提交8良2不良，库存0，原生首次报工推进工单进行中 |
| 来源/审计 | 既有report_time_context.suggestion_draft保存建议、来源工单/工序/modified；原JobCard.owner/创建时间关联确认人。来源是本人确认的客户端声明，不是模型验真或授权凭据。正式数量/时段仍由原业务规则决定 |
| 人工修改与防重 | 测试中原建议8/2可人工改为7/2；原建议保留、正式事实7/2。可选来源纳入原请求hash，同键同内容回同单、改来源复用键被拒；无basis原哈希不变 |
| 过期/撤权 | 新请求的源版本变化、跨工序绑定、撤报工角色后确认被拒，不新增另一事实；原成功请求先按原hash返回，不能因首次报工改了父单版本而失去恢复能力 |
| 旧数据保持 | 回滚35表原行保持；实际页面样例37表原行保持。只用本轮独立物料/BOM/仓库/工位/账号，无期初库存和旧数据清理 |

## 实际命令与证据

```sh
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a01_boundary_tests.py
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a01_boundary_fixture.py prepare
python3 .development/checks/a01_boundary_http.py prepare-order
python3 .development/checks/a01_boundary_http.py read-only-denials
docker exec -w /home/frappe/frappe-bench -e PYTHONPATH=/b01 xgd-b08-check env/bin/python /b01/a01_boundary_fixture.py audit
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/a01_source_check.py
docker exec -w /home/frappe/frappe-bench xgd-b08-ui env/bin/python /b01/a01_source_check.py
node --check .development/repos/erpnext/erpnext/manufacturing/doctype/work_order/work_order.js
git -C .development/repos/erpnext diff --check
```

- `draft-red.log`：最小新fixture因连接缺失真实失败，1失败/0错误，9.325s，35旧表保持。
- `boundary-first.log`：新增7/7通过，74.882s，35旧表保持，真实原生业务fixture，无mock业务实现。原普通确认也由本轮过期测试的前置消费，没有重跑旧B08全套。
- `reader-denials.log`：取数正例、三种写入口403；原响应保存。
- `after-cancel-audit.json`：实际页面取消后报工0/库存0，37旧表保持。
- `reviewed-draft.log`及`ui-defaults-fixed.json`、`ui-filled-values-fixed.json`：完整重载新JS，原生计数0、实际时间空；本人填写后预览通过。
- `confirm-ui.log`、`confirmed.png`和`after-confirm-audit.json`：普通worker点击原确认按钮，实际生效一笔8/2、建议来源快照存在、库存0，37旧表保持。结构化建议由受控测试送入原弹窗，不能冒称已有真实模型/语音入口。
- `xgd-b08-check-source.log` / `xgd-b08-ui-source.log`：最终53文件匹配、29Python编译通过；Node语法及diff检查退出0。

原始响应、受限账号、脚本和快照只保存在`.development/private/a01-boundary-20261031/`，不直接公开运行数据或凭据。浏览器空间本轮创建，验收后关闭。

## 本轮失败、修复与审查

页面实际发现：导入时把原可选停工/加班0默认也清成空，导致本人填完时间后原生报“停工秒数必须是有效数字”。保留`preview-state.log`等真实失败，最小改为仅清空缺失的4个必填数量/时间，两个可选计数沿原0默认。只复验此失败页面路径并清目标缓存/重载；Python未变的7项不重跑。修补后页面原生预览及确认通过。

工具失败也保留：重开后隐藏/可见同标题导致ego定位歧义，改用当前可见modal控件；第一次诊断误用带校验副作用的get_values，之后只读DOM定位。没有为这些工具错误修改权限或业务规则，没有重发已验写入。

一次独立只读审查对4份增量未发现Critical/Important，1个Minor记录延后：服务器明确拒绝后，原恢复逻辑会解锁建议的任务选择；若改另一任务，服务器仍按原basis正确拒绝。无错写或越权，切回原任务或关闭重开可恢复。本轮未把这个组合标已验；不循环派审查。审查时正在进行的页面验收以随后实际回执为准，审查意见不代替页面通过。

## 本轮停止边界与后续入口

- 本包的本地结构化边界已验；真实模型和语音服务、调用费用、真实模型prompt注入/工具失败、A02完整候选及A03识别仍未验证。用户已确认C06待定，不再次索取相同信息、不调用外部服务、不用0冒充未知费用。
- 后续按原A02消费已有明细预览和本包只读取数/草稿边界；不重新开发B05～B19，也不重新执行本包未变化的验收。缺模型只阻塞真实模型子项，确定性候选/预览按原卡独立推进。
- B19实发、B18真实现场、手机真机、此前B14/B15等缺条件项及完整G1/G2/G3、Z01/CASE-11保持原未验状态，不据此关闭整卡或正式交付。
- 按用户约定保留本地开发分支；未commit/push/PR，未更新TODO、交接、任务卡或OpenSpec勾选，无本轮提交SHA/CI结果；未运行ERPNext全量测试或重复未变旧批次。
