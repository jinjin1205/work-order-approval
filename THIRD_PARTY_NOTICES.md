# 第三方来源与本轮修改

本次归档日期：2026-10-31。本文件登记实际来源和范围，不替代完整依赖许可审查。

## 项目工作流程说明

- `.agents/skills/openspec-*/SKILL.md`为本项目OpenSpec 1.15.0生成的6份技能说明，文件声明MIT；`.agents/skills/.openspec-target`仅记录目标工具`codex`。对应[固定v1.15.0 MIT许可](third_party/workflow-licenses/OpenSpec-MIT.txt)取自[Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec/tree/v1.15.0)，保留许可原文。
- `.agents/skills/playwright-cli/`为已安装`@playwright/cli` 0.1.22提供的技能及10份引用说明，随安装包声明Apache-2.0；[许可原文](third_party/workflow-licenses/Playwright-Apache-2.0.txt)直接取自该安装包LICENSE，来源项目为[microsoft/playwright-cli](https://github.com/microsoft/playwright-cli)。这里只保存项目说明，不包含CLI二进制、浏览器、登录会话或缓存。
- `.publication/`仅保存4份本项目发布维护脚本源码；其运行依赖原工作区布局及本地私有证据/排除扫描，不能据公开归档宣称完整发布或部署已可在新机器直接运行。未复制Superpowers插件代码或本机全局安装。

## 实际包含的第三方源码

- 上游：[frappe/erpnext](https://github.com/frappe/erpnext)，v15.124.1，提交`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`。
- `source/erpnext/`共46个修改或新增文件：32个源自该固定版本、14个维护新增。累计包含数量/工时、逐笔事实、审批权限、领退料/入库、移动恢复、计划来源、同源报表以及AI只读候选/人工草稿边界和测试，具体内容以[source-lock](source/source-lock.json)及[完整补丁](source/current-implementation.patch)为准；不改Frappe框架。保留原版权头与GPL许可证[license.txt](source/erpnext/license.txt)，修改日期2026-10-26至2026-10-31。新增配置/确定性建议不代表真实外部模型或客户服务接入。
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
