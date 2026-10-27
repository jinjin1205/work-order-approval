> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B08 核心逐笔报工实施记录

依据原B08最小闭环及R07三份绑定；2026-10-27开始。公开基线c064b6caf33b3cf8b440e02cf6f0926d06455b1f，产品基于ERPNext4e0dce9/Frappe f1cf50c；原累计补丁a08b8eb7e2ec509982b817527c840bd2cbdc252e1d1a121e425077605fcbab1f。继续codex/xgd-maintenance和原隔离测试站；不动客户/开发审批，不重跑不变B14/Q05。

Ruling：沿用户原任务卡和本目录记录，不另建技能计划或工作树。已有原生计划占量/差额损耗反例直接引用native-fact；新的确认契约先以可运行最小岗位样例留红。只用一个Job Card事实账。

接口交接：Work Order Operation身份/计划→每笔Job Card；B04计算→B14内部规则→确认快照；B19执行门槛→B02/B06任务scope→受限父派生。三处均由原绑定确定，不新增主管报工审批。公开确认前先完成事实、窄角色及原记录保护局部门槛，完整G1/G2/G3保留。

当前工程选择：保留原自动计划卡及排程/人员资料；本项目已绑定审批工单中，无report_request_id的卡仍为计划/准备记录，有服务端唯一请求键的提交卡为事实。原数量校验分别核计划占量和已提交事实，不删除计划卡、不抬高超产率。原有非项目工单不迁移。确认走原Document insert/submit和原工单汇总；仅既定派生字段在服务器上下文允许回写。

- [x] 最小元数据/普通岗位fixture可运行、确认契约红测。
- [x] 三笔数量及普通岗位/受限回写。
- [x] 计算、确认、历史、防重和必要原记录保护。
- [x] 实际HTTP/中文入口及体验计量已留证；10秒目标未达本次计量，不关闭体验项。
- [ ] 一次最终独立审查、原卡更新、公开保存及回读。

## 本轮实际过程

- fixture第一次因发起人引用另一班组的任务授权被原生用户权限拒绝；样例改为未配置scope的任务作拒绝对照，未放宽权限。第二次fixture可运行，确认接口未实现红测见contract-red.log。
- 三笔实现早期发现B04校验返回float与本轮Decimal接续错误，及缺少原生在制仓字段；分别在输入/原生保存边界修正，未改B04计算。
- 受限回写第一次拒绝required_items差异，诊断证明仅为modified/modified_by；只容许原生子行审计信息变化，业务字段继续冻结。
- core-guards-red.log：三笔、权限、超量、防重、旧新规则快照通过。删除/子行检查最初收到原生ValidationError而非预期PermissionError，修正断言后加绕过提交字段限制的子行测试，history-red.log证实原时间行可从1改成9。该真实漏洞只补Job Card Time Log父事实保护。
- 用户本轮确认：更正起止时间不变时沿用原时段依据。最小全冲10→8继续用cancel/amend；原卡数量和快照保留，不重算历史。本轮只覆盖无库存后续单据样例，不关闭完整G2/G3。

## 一次最终独立审查与限定修补

按executing-plans要求使用一次gpt-6-astra只读独立审查，无再次审查循环。审查指出4项Important，本轮均纳入一轮必要修补：

1. 有后工序事实时前工序10→8没有拒绝：相邻工序授权fixture修正后`review-downstream-red.log`复现；补取消前的后工序事实检查，不做整套逆向链。
2. 停止后旧请求重试被新增执行门槛拒绝：`review-business-red.log`复现；历史权限/摘要找回在先，仅新事实再检查执行状态；复用B19原状态判定。
3. 含原生子工序配置时预览未给出边界：同log复现；本包只支持单层工序，预览/确认明确中文拒绝。没有增加子工序分摊或另一套计算。
4. 提交成功后刷新失败被显示为未保存：`review-ui-red.log`以当前JS函数做受控前端故障注入复现，修后`review-ui-fixed.log`通过。此项不是实际HTTP事务测试，成功事实提示与页面刷新错误已分开。

审查未评判的完整G1/G2/G3、跨工单/库存、手机/现场、工资及整套逆向链继续按原卡保留；属于未覆盖范围，不能当已通过。独立审查之后的必要改动只做对应反例和受影响正例，不再请第二名审查员。

## 实际页面

普通操作工通过原工单页面的逐笔报工对话框完成三笔；原生日期输入需实际键盘change事件，自动化fill只改DOM造成最初无预览，改用真实键盘后正常，未因此改全局控件。临时诊断输出已移除。

三次上下文就绪后确认分别804/682/569毫秒，各一次点击；第二、三笔弹窗到成功含工具与诊断等待为63273/23281毫秒，不当作人工现场效率。另从列表完成默认剩余7、无不良样例：18015毫秒、3次主要指针点击、2个时间输入，确认595毫秒。一次确认条件已验；“全流程尽量10秒”未证明达标，待现场计量/必要简化，不能关闭B08-07体验或整卡。原始AX、截图、账号与运行数据仅留本地，不公开上传。

## 本批结果及下一步

最终14项针对性测试134.652秒通过；3项原审批/任务/计时回归36.812秒通过。收尾新增1项派生失败回滚14.911秒通过：已真实写入Job Card和时间行后，故障注入使父计划量被原白名单拒绝，真实savepoint回滚后卡/行/累计均无残留，服务器上下文已清理；这是受控DB故障测试，不称真实HTTP内部提交故障通过。最后仅新增测试定义，14项/3项所测产品逻辑与最终产品逻辑相同，具体批次补丁见两个source-manifest。

HTTP保留失败及修补：同键并发最初200/唯一键错误，随后结果读取旧快照404；分别改为父锁后的当前读取/当前聚合及取回同笔结果。最终同键并发2×200指向同一事实；不同请求键的相同零时长输入各计一笔；正时长重叠仍遵循原生限制。真实超量417前后事实一致，无权任务、整单PUT、原卡PUT和时间行PUT均403；丢响应查询200。证据分别为http-same-key-pass-zero-time-failure、http-followup-results、http-remaining-results，不把中间脚本/样例错误隐藏或累计成全套通过。

32份清单文件在最终镜像和专用中文网页一致；测试容器最后只补同步未参与Python业务测试的前端JS，未重跑无关业务。源测试站11张原业务表内容/条数一致，仅排除本批新增空元数据字段；源站Work Order Workflow仍0。新的B08合成站启用的是其自有测试流程，不是开发/客户审批。所有失败样例及本地数据保留。

具体命令：
```sh
# 当前14项主批（在新增回滚测试定义之前执行）
bench --site xgd-test.localhost run-tests --module erpnext.manufacturing.doctype.job_card.test_job_card --case TestProductionReportConfirmation --skip-test-records --skip-before-tests
# 原受影响回归
env/bin/python /b01/b08_affected_regression.py
# 新增1项受控派生失败
bench --site xgd-test.localhost run-tests --module erpnext.manufacturing.doctype.job_card.test_job_card --test test_derivation_failure_rolls_back_native_fact --skip-test-records --skip-before-tests
# 不重放已消耗样例；HTTP脚本按各阶段单独执行，定义位于.development/checks/b08_http*.py
env/bin/python /b01/check_source.py /b01/b08-source-manifest.json
env/bin/python /b01/b08_preserve.py
```

状态：B08/B09部分完成，不关闭G1/G2/G3。下一步仅补未覆盖权限组合、停用规则组合及现场10秒体验；工资/效率展示等整卡余项仍在原卡。最终公开文件核对及远程SHA另存发布回执，不把本地保存当远程完成。
