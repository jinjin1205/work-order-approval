# 第三方来源与本轮修改

本次归档日期：2026-10-27。本文件登记实际来源和范围，不替代完整依赖许可审查。

## 实际包含的第三方源码

- 上游：[frappe/erpnext](https://github.com/frappe/erpnext)，v15.124.1，提交`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`。
- `source/erpnext/`内6个文件来自该版本，在原文件上局部修改辅助读取权限、库存单位汇总/限额、B19审批核心与任务/库存执行门槛及其测试。保留原版权头；上游GPL文本原样附于[license.txt](source/erpnext/license.txt)。修改日期2026-10-26至2026-10-27，差异见本仓补丁与文件哈希。
- 未修改文件按锁定上游SHA获取。运行依赖Frappe v15.124.0；本归档不复制Frappe源码，也不宣称已完成全部容器/依赖许可证兼容核验。

## 要持续核对的参考产品

| 产品 | 入口 | 本轮状态 |
|---|---|---|
| 快格云MES | https://github.com/kuaigeyun/kuaigeyun-mes | 参考候选，未复制其源码；具体模块和许可须按拟用版本核对 |
| qcadoo MES | https://github.com/qcadoo/mes | 参考候选，未复制其源码；商业模块不能当已获开源源码 |
| ERPNext | https://github.com/frappe/erpnext | 当前主要底座，实际修改范围如上 |
| OpenMES | https://github.com/Mes-Open/OpenMes | 已有静态参考；未在本项目运行或复制代码 |
| t3rik-erp | https://github.com/WangSanPing/t3rik-erp | 已有静态参考；未在本项目运行或复制代码 |

具体静态证据和限制保留在`evidence/R01/`，以其核查日期和固定版本为准，不冒称发布日重新核验。新任务先填“直接用/配置用/局部改造/必须新增”，记录相关文件、版本、可获得性、许可、验证和停止边界。只有实际需要的部分不可取得、许可不允许或验证不适用时，才说明最小自研范围；不得因风格、语言或目录偏好重复开发。
