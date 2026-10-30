> 公开归档副本（2026-10-30）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B09 作业卡复制与真实批量队列（2026-10-30）

本包限定实现、验收及代码公开回读已完成；最终交接文档另行提交。原卡与R07为唯一范围；OpenSpec只引用，不复制清单。

- 基线公开main `854de6eec0eb294fb82626713ab3194390e1e2ab`；维护ERPNext `4e0dce9`，Frappe15.124.0；原累计补丁`fe0fd20526058649f5a250ff53780e2dea0b51b2a7a6ed7fb93e00cbd8dd0343`。
- 复用：B05父工单复制/历史父删，B08历史保护、I03～I06和质检图片，不重跑。
- 裁定：沿用原B09清单及本记录作为执行账，不建立第二套计划；已获本包隔离验收、白名单公开推送授权。队列验收仅指定作业执行，不启动常驻Worker/调度器，不证明完整G3。
- 首次P0空计划复制1项通过11.045秒；复制+插入反例2项18.850秒，复制6个字段断言失败，插入因fixture误取第三工序触发原生顺序检查。保留失败；改为明确第一工序后P0+插入2项20.470秒，P0通过、插入未抛PermissionError，证实新建缺口。
- 最小修复：原Job Card JSON实际字段no_copy；原validate_report_record只对项目新建且非可信确认上下文拒绝实际时间/数量。无新增字段/DocType/Frappe改动；现有员工/计划安排不删。
- 修复后新类3项26.004秒通过，18表旧行一致；受影响原生非项目工时新建正例1项0.924秒通过，15表旧行一致。不是全套回归或整卡完成。
- 浏览器首次登录脚本使用英文定位，中文页超时且未登录；已按实际中文控件修正。原始含凭据输出只存私有目录。Socket.IO404为此HTTP-only隔离站限制，不算后台通知验收。

## 实际命令

```sh
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py erpnext.manufacturing.doctype.job_card.test_job_card.TestProductionReportLifecycle
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py erpnext.manufacturing.doctype.job_card.test_job_card.TestProductionTimeMetrics.test_native_closed_time_recalculated_and_cross_day
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_ui_fixture.py b09-lifecycle
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_control.py prepare-quality b09-lifecycle
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_control.py approve b09-lifecycle
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b09_lifecycle_fixture.py prepare
```

后三步只用于本包新工单。prepare已生成原报工1/1、取消质检1及私图1、正常关联更正1/0、9张空草稿；第10张须由页面复制并保存。旧27表已捕获，尚待队列后核对。

## 页面与真实队列结果

普通编辑员中文PC使用菜单“重复项”，新草稿显示完成0、时间日志无数据；浏览器实际元数据9项no_copy=1，报工键/实绩/起止/计时均为空或0，保存成功。API不是此页面证据；原始页面快照只存私有目录。

`b09_lifecycle_fixture.py checkpoint`核页面新增恰好1张合法空卡、普通报工员对11目标拥有真实delete权限且不是System Manager；保存原卡/替代卡/时间行/质检/File/工单/工序完整行和图片二进制哈希。

`b09_lifecycle_queue.py dispatch`首次脚本缺原生get_queue的qtype参数，未发HTTP；修正为default后单次POST真实delete_items，200空消息、11目标仍存在，真实RQ job的site/user/method/items完全匹配。`execute`只取出该job并用原生SimpleWorker执行；finished返回1个未删原报工，10张新草稿删除，其他排队条目保留。未启动调度器或常驻worker；原生删除的后续动态链接清理作业未消费，不声称已验长期监听/通知/完整G3。

`b09_lifecycle_fixture.py audit`独立回读：旧27表捕获行完全一致；原报工与替代卡、时间行、已取消质检、私图File和真实文件、工单/工序前后完全一致；净良1/不良0、5卡（3计划+2历史/生效事实）、库存0。QI为人工判定，本样例Reading0行，不能声称覆盖非空检验读数。

```sh
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b09_lifecycle_fixture.py checkpoint
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b09_lifecycle_queue.py dispatch
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b09_lifecycle_queue.py execute
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b09_lifecycle_fixture.py audit
```

独立审查修复及白名单代码推送已完成，见本节末的实际回执。G2/G3整体验收、库存逆向、跨工单/工作站/配置并发、手机/现场和Z01未验；原后台b19不恢复。

## 独立审查修复与边界裁定

一次独立只读审查给出2项Important、0项Critical/Minor：子工序实绩与员工安排夹带实际时间。实测各2反例均红（16.995/18.404秒），R07已补绑两个现有子表JSON；仅其实际字段no_copy，计划定义/人员/计划时间保留。新建guard检查两个载体，既有计划编辑/计时不扩保护。

修补后的8项65.174秒批次：6通过、1失败、1错误。原生Python copy_doc(ignore_no_copy=False)将no_copy字段置None，不给新默认值；copy字段选择测试错误期待未insert时status=Pending，改为只允许None/Pending，保存后仍要求Pending。合法子工序复制insert时completed_qty原无默认导致None累加TypeError；通过原生元数据为该已有数量字段设default=0，由Document._set_defaults在insert补值，不添加catch或掩盖非法实绩。只复测这2个失败方法，其余刚通过的6项不重跑。

审查搁置项裁定：既有计划编辑/计时、非项目完整Amend、库存逆向/共享工位并发/完整G2G3/常驻Worker均继续保留未验，不能外推本包；B05/B08旧项按原证据复用；页面沿执行者实际截图/元数据/保存和独立DB证据；远端与CI只在推送后判断。这些限制若被误作整卡通过，会造成交付误判，故原卡门槛不关闭。

## 本包验证收口

最后受影响2项23.024秒通过、18表旧行一致；共7个新方法＋1个原生正例分批通过，9批真实回执含红/中间失败全部保留，未重跑最终全8或全库。两个容器41文件一致、22份Python语法检查通过（实际数以runtime.json为准）。当前五文件最小变更、累计33份修改源码，源版本和SHA见source-manifest.json。

浏览器完整重载后，用真实客户端原生copy_doc构造子工序/员工实绩输入，只在内存复制、不保存：7个新增子字段no_copy=1，子工序定义、员工和计划时间保留，实际值清空、状态Pending、原表单未改。首次脚本末尾分号不被CLI表达式包装接受，语法错误无业务写入；去除后通过。原生菜单Duplicate并保存的实际页面证据在前述主流程，二者不混称。

登录日志的一次本地输出误含合成账号密码，已轮换该唯一新编辑员密码并失效会话；现值/旧值均列入公开排除扫描。未输出或上传客户凭据，凭据与原始样例、图片、浏览器日志均不公开。

无待修复Important/Minor。审查两项已先红后绿关闭，合法计划及原生路径正例保留。后台队列旧条目和未消费动态链接清理不改；达到本包停止点，不追加库存或完整并发开发。

`openspec validate b08-followup-20261028 --strict`实际返回issues：skip_specs明确接受零delta，但引用模式tasks没有复刻checkbox，报告0 tasks warning。严格检查未获无警告通过；按用户要求保留原34卡为唯一任务表，不为消除CLI警告另建清单或归档整卡。

公开准备检查：export_public.py沿文件白名单生成614文件、33源码；check_public.py检查当前/旧合成凭据、运行数据和个人路径，命中均0，所有Python可解析。旧76批测试回执逐项保持，本包追加9批（含失败），不拼成累计全套通过。

## 代码保存与交接

代码[`48c2f4b`](https://github.com/jinjin1205/work-order-approval/commit/48c2f4beb2162c7dde4a155e6e46ec5ca1fed499)已推送main。`python3 .publication/verify_b08.py`新克隆回读614跟踪文件/613内容哈希、33份源码完全一致，缺失/多余/哈希差异均0，见[回执](../../发布/2026-10-30-48c2f4b-remote.json)。`python3 .publication/check_ci_pause.py 48c2f4beb2162c7dde4a155e6e46ec5ca1fed499`核精确SHA全部事件：0工作流/运行/check/status、无API错误，见[CI查询](code-ci.json)；未配置/未触发，不是CI通过，无运行链接，[Actions入口](https://github.com/jinjin1205/work-order-approval/actions)。

下一步从原B10真实领料提交/取消链继续：先核已验单位子项和B07/B19依赖，再补R07权限/先锁工单/原生库存调用链；随后B11/B12。B09整卡和G2/G3仍部分，等待真实下游逆向/并发证据，不重跑本包已验项。最终文档提交及其CI只在最终回复报告，不回填循环提交。

公开仓库保存白名单源码/任务卡/脱敏证据；维护codex/xgd-maintenance仍以固定上游为HEAD，33份累计工作区差异已由源码锁/补丁公开归档，未向ERPNext上游推送。私有凭据、原始运行数据/图片/日志及本地验证克隆保留在本机，不属于公开交付遗漏。后台b19本轮未操作；沿原PAUSED交接状态，未重新读取实时自动化状态。
