> 公开归档副本（2026-10-30）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B08 原生报检与私有图片（2026-10-30）

## 范围与结论

依据[原卡](../../../docs/任务卡/02-生产与物料闭环.md#b08-quality-20261030)及[R07](../../R07/inspection-attachments.md)，本包限定实现与本地验收通过，公开推送/回读尚待执行。用户明确不新增字段。只用原生Quality Inspection追加关联已确认报工，图片挂质检草稿；人工选结果后提交，原报工不回写，不新增生产/库存事实账。

维护分支`codex/xgd-maintenance`，ERPNext15.124.1上游`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，Frappe15.124.0；发布基线main `13f7f6fe5430212428d663f9e106984b642f9916`，本次已fetch核一致。产品仅R07五文件，累计31份修改源码；[最终清单](source-manifest.json)39份运行文件，补丁SHA256 `fe0fd20526058649f5a250ff53780e2dea0b51b2a7a6ed7fb93e00cbd8dd0343`。没有新增字段/元数据或变更Frappe共享框架。

## 实际实现

- Job Card只读报工页新建/查看原生质检；新建结果为空，不自动保存或判定合格。质检校对当前父对象、物料和公司，不能改挂；源报工整行及快照不改。
- 项目质检图片仅允许本地私有PNG/JPEG/WebP内容；本包实际上传验收PNG。已提交/取消质检和图片不能删除、覆盖、公开或改挂；取消时不能夹带字段/子行变更。
- 图片下载、列表、zip及文件owner均受父报工与质检权限约束；独立QI/File分享拒绝，父报工单张分享仍需质检岗位权限。普通原生质检/文件保留原控制器；带图草稿可删。
- 修复File共享二进制公开/优化覆盖的具体入口，原生清理仍先检查父对象；没有捕获通用异常返回假成功。图片解析只转换明确PIL错误并保留原因。
- 中文PC暴露的已确认只读报工查询工单领料配置弹窗，局部跳过不必要查询；不通过扩大工单read来消除提示。

## 实际验证与失败保留

保留[全部12批摘要](test-batches.json)。21个不同方法分批取得通过结果：中间19方法173.324秒；再发现zip下载和图片优化写盘入口，两个红例17.754秒失败，修后只跑两个新入口＋两个受影响方法，4方法42.360秒通过。没有最终21方法一次全量或全ERPNext套件通过结论。每个完成批次回滚后原18张捕获表保持。最初中断的review-red批没有完成结果，明确记INTERRUPTED，不算通过。

实际命令（完整方法名见摘要）：

```sh
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py erpnext.stock.doctype.quality_inspection.test_quality_inspection.TestProductionNativeQuality
# 后续仅zip/优化及受影响两项，按test-batches.json中file-api-green的四个完整方法名执行同一runner
node --check .development/repos/erpnext/erpnext/manufacturing/doctype/job_card/job_card.js
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_source_check.py /b01/b08-quality-source-manifest.json
docker exec -w /home/frappe/frappe-bench xgd-b08-ui env/bin/python /b01/b06_tasks_source_check.py /b01/b08-quality-source-manifest.json
python3 .development/checks/b08_quality_http.py before-revoke
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b08_quality_fixture.py revoke
python3 .development/checks/b08_quality_http.py after-revoke
docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b08_quality_fixture.py audit
```

两容器[检查](test-runtime.json)/[网页](ui-runtime.json)各39文件一致，22个Python文件编译通过，JS语法及维护仓diff检查通过。中间批完整补丁哈希未捕获，明确null；不能事后杜撰。最终源码清单与实际页面行为分别取证。

Playwright CLI专用`b08-quality`实际使用普通报工/原生Quality Manager合成账号：无质检权新建提示、父报工只读分享进入、新建结果空白、手工样本1/不合格、保存草稿、私有PNG上传、确认提交、完整重载及原生附件链接打开；浏览器图片实际解码32×1。撤分享后以新查询参数无缓存访问原图片返回403，不把旧缓存清空当撤权证明。专用浏览器已关闭。

[真实HTTP](http-summary.json)撤权前10项通过：外对象拒绝、QI/File读、普通及fid下载、zip原图哈希、锁图删除/公开拒绝、外对象建QI和错误公司拒绝；撤权后8项通过：父/QI/File读、普通/fid图片、zip均403，QI/File列表为空。只用本包新对象，没有再调用报工确认或库存过账。

失败与限制：Docker原容器停止使上轮测试中断，本轮恢复原5个容器，未建新站/镜像。合成select权限原生默认带read，改为本例新角色明确select-only；原生QI按元数据fetch_from另需当前物料和公司的read，以User Permission限定。Item/Company取值弹窗和未保存草稿导航失败保留，失败草稿未持久保存。首次HTTP由于fixture保存的API secret与实际加密值不符返回401，未到业务权限判断；修正私有fixture后才得18项结果。一次登录日志回显本地合成账号凭据，已轮换该账号，原日志和新旧凭据仅私有保存并纳入发布排除扫描。

## 数据保持与未验范围

[旧行核对](old-row-audit.json)：原26张表捕获行/列全保持，旧用户/权限不改；仅新增独立工单1、计划卡3、正式报工1、时间行1、QI1、私图1。该笔良1/不良1，库存0。原报工在查看前后整行未变，质检前checkpoint与最终整行完全相同，图片磁盘二进制哈希保持；不是仅调用缓存get_content检查。

复用未变化的导航、报工、计价、时段、并发及B05～B07证据，不重跑。现场人工10秒、手机/PDA、完整G1/G2/G3、B08整卡、客户角色映射及Z01/CASE-11仍未验证，不能以本机旧环境验收替代正式交付。后台b19未恢复。
