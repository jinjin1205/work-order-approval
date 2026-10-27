> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R05 补证：小屏网页实际操作

2026-10-26。**普通操作工报工、普通仓库角色提交领料已实际完成；进行中工单的原生退料入口受状态限制，未完成网页退料。** 这是桌面浏览器 390×844 视口的受控核验，不能写成真实手机、现场易用性或 CASE-08 全部通过。未修改产品代码。

## 环境、身份与输入

- 沿用 R05 固定 ERPNext 15.124.1／Frappe 15.124.0 和 ARM64 镜像，完整身份见 [运行记录](run-record.md)。仅本机合成站点 `r05.localhost`。
- 新增 [Web 评估配置](../../.evaluation/r05-erpnext/compose.web.json)：官方入口脚本、`bench --site r05.localhost serve --port 8000 --noreload`，CI=1；仅绑定 `127.0.0.1:18085`。不是生产部署；没有 websocket 服务，浏览器有 socket.io 连接错误，不将实时推送计为通过。
- 用 Codex 浏览器工具真实点击、填写和确认，未用页面隐藏状态、脚本调用业务方法替代操作。视口390×844，操作结束恢复默认尺寸。
- 报工身份 `r05f-a-a@example.invalid`：Manufacturing User＋关联员工带来的 Employee，非管理员。夹具工单 `[本地样例编号已移除]`、卡 `[本地样例编号已移除]`、员工 `HR-EMP-00001`，计划10、预先指派员工、初始没有时间行。初始化见 access-setup.json（仅本地保留；见 publication/evidence-index.json）。
- 库存身份 `r05f-a-stock@example.invalid`：Stock User，按工单显式 User Permission。浏览器 My Settings 路径和页面用户名均确认该身份。夹具工单 `[本地样例编号已移除]`，原料 `R05F-U-MAT-RM` 初始来源20／在制0，已保存领料草稿5。原生初始化记录 material-setup.json（仅本地保留；见 publication/evidence-index.json）、[脚本](../../.evaluation/r05-erpnext/probes/mobile_material_setup.py)，未重新初始化或重复提交旧夹具。
- 凭证仅在隔离目录0600文件中，不包含在证据。站点沿用 America/New_York、英文业务界面和测试公司 INR；未完成中文、时区或客户配置。

## 实际步骤与结果

| 操作 | 观察与持久化结果 | 判断 |
|---|---|---|
| 登录→Manufacturing→Job Card 列表→指定卡 | 原生小屏能打开卡；Start Job／Complete Job 在 Menu 中 | 能到达已有卡；未测试扫码派工或建单全流程 |
| Menu→Start Job→Menu→Complete Job→数量10→对话框 Submit | 卡总完成10、只有一条时间行，但 docstatus=0，工单工序有效完成仍0；见 before-submit.json（仅本地保留；见 publication/evidence-index.json） | “完成数量”操作尚未使报工生效，不能把对话框成功当提交成功 |
| 页面 Submit→Yes | 卡 docstatus=1、完成10，工单工序完成10、工单成品产出0；见 submitted.json（仅本地保留；见 publication/evidence-index.json） | 同一操作工确认后生效，没有切主管账号；原生多步流程仍需适配首报开工／逐笔确认要求 |
| 刷新原卡一次 | docstatus=1、时间行仍1、工序仍10、成品仍0；见 refreshed.json（仅本地保留；见 publication/evidence-index.json） | 本次普通刷新未重复增加；不是断网丢响应恢复或重复请求全判据 |
| 仓库角色打开既有领料草稿45→Submit→Yes | 页面 Submitted；普通账号新连接回读 docstatus=1，来源15／在制5，库存账同单-5/+5；工单累计转料5。见 issue-submitted.json（仅本地保留；见 publication/evidence-index.json） | 既有草稿的普通小屏过账子项通过；没有把后台建草稿算作网页建单通过 |
| 从领料单进入关联进行中工单→Menu | 可见 Start／Finish／Close／Stop，未见 Return Components。见 菜单文本（仅本地保留；见 publication/evidence-index.json）与截图 | 当前状态下的这一退料入口不可用，网页退料未完成；未为测试关闭工单或绕过权限 |

报工发生于北京时间约18:52～19:00；库存提交为19:16:49，对应站点显示07:16:49。只读 JSON 有 UTC 检查时刻。操作间隔包含工具等待，不作为点击效率或工时准确性的测量。

库存页加载时实际弹出 `No permission for Stock Settings`，调用 `frappe.client.get_value/get_single_value` 返回权限错误；关闭提示后本次提交成功。需要在最小岗位配置与页面读取范围中处理，不能直接授予仓库人员管理员权限。见 提示截图（仅本地保留；见 publication/evidence-index.json）和 浏览器错误（仅本地保留；见 publication/evidence-index.json）。没有推断这就是所有页面错误的原因。

## 退料入口的源码核对

在相同镜像只读查看 `work_order.js:242–267`：`add_custom_button_to_return_components` 要求 docstatus=1 且状态属于 Closed／Completed，并存在未耗完物料；其后调用原生 `make_stock_return_entry`。因此本例 In Process 时不显示符合原生代码，不能归咎于390宽度藏按钮。

同镜像 `stock_entry.json` 的 `is_return` 为 hidden=1、read_only=1；定向检索 `stock_entry.js` 没有定位到制造退料创建按钮。此检查不等于穷尽整个ERP所有入口。源码身份沿用 [物料报告](followup-material.md) 中实际文件blob；[固定提交入口](https://github.com/frappe/erpnext/blob/4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e/erpnext/manufacturing/doctype/work_order/work_order.js#L242)可复核。

最小适配方向：沿用原生表单和库存单入口，为有权限的在制工单提供必要退料动作；同时解决已复现的可退净额、单位和工单上限问题。只改按钮不足以保证数量正确，具体文件及失败路径由 R07 绑定。

## 截图与复核方法

- 报工前（仅本地保留；见 publication/evidence-index.json）、完成数量对话框（仅本地保留；见 publication/evidence-index.json）、报工已提交（仅本地保留；见 publication/evidence-index.json）。
- 领料已提交（仅本地保留；见 publication/evidence-index.json）、在制工单菜单（仅本地保留；见 publication/evidence-index.json）。
- 报工回读命令：`python3 .evaluation/r05-erpnext/probes/ui_readback.py --stage <独占输出名>`；库存回读：[mobile_stock_readback.py](../../.evaluation/r05-erpnext/probes/mobile_stock_readback.py)。均只读普通账号 Resource API，原始响应单独保存；不以截图替代库存事实。
- 中断恢复时 Docker socket 一度不存在；随后 Desktop status 为 running，恢复同项目四个服务成功。旧浏览器tab已不存在，新tab沿用仓库会话；未重复初始化、报工或领料。此过程不是弱网恢复验收。

**未验证：**真实手机／触控／相机扫码／麦克风语音、弱网与提交后丢响应、网页退料完成、手机新建领料、现场中文与效率、普通用户完整权限面、完整工时口径、客户部署。首版手机与三项AI仍是必需范围，不因本轮选型核验结束而取消。
