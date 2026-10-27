> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R01 许可与来源资料清单

日期：2026-10-26。用户已确认客户自行部署、接受适用许可要求的源码开放。本文件只登记实际读到的许可事实和缺口；不是全依赖许可证兼容认证，也没有声明已获私有组件授权。

| 对象 | 已读许可资料 | 已明确的待处理项 |
|---|---|---|
| t3rik后端 | 固定提交LICENSE：Apache-2.0；来源说明含苦糖果MES/若依 | 保留原版权/来源；不是逐文件审计；实际传递依赖未解析 |
| t3rik PC | Gitee仓库展示Apache-2.0 | 固定提交LICENSE/package.json未取得；不能用后端许可证覆盖 |
| t3rik实际报表依赖 | 启动POM直接引用JimuReport/JimuBI，根管理版本1.9.4 | JimuReport发布元数据不足以证明组件全部许可；JimuBI精确版本许可未取得；不能认定无需授权 |
| OpenMES核心 | 顶层AGPL v3；后端AGPL-3.0-only | 根npm元数据ISC不一致，不能认定整仓ISC |
| OpenMES本地包/模块 | ui为AGPL-3.0；module为AGPL-3.0-only；AFL仅在指定模块范围且有相应声明时适用 | 商业/另仓模块未取得；示例文件未见AFL头不能笼统算AFL |
| OpenMES原生mobile | manifest：AGPL-3.0-or-later | 当前不引入原生打包；不因此扩开发范围 |
| OpenMES第三方构建物 | 锁文件的主要PHP/npm许可已登记；Dockerfile另下载ionCube | ionCube分发条款与固定摘要未核，系统镜像/传递依赖未全核 |
| ERPNext代码 | GPL v3正文，package声明GPL-3.0 | 交付修改/源码材料按实际采用整理；不将GPL泛化给所有组件 |
| Frappe框架/容器配置 | 两者各有MIT许可文件 | 框架含字体/前端/第三方依赖；已有attributions较旧，不是当前完整清单 |
| Bench CLI | GPL v3正文，pyproject声明GPL-3.0-only | 单列部署工具，不能随容器配置统称MIT |
| ERPNext文档/商标 | README文档CC-BY-SA-3.0，另列商标政策 | 如实际复用文档/品牌再核，不因使用代码假设可沿用全部品牌 |

每项精确SHA来源、依赖版本、文件头和证据链接分别保存在 [t3rik](t3rik-evidence.md#3-许可与依赖清单)、[OpenMES](openmes-evidence.md#3-许可资料与待项)、[ERPNext](erpnext-evidence.md#3-许可与主要依赖资料)。候选主源码固定见 [source-lock](source-lock.md)。

## 后续实际交付需要的资料

只对最终采用部分整理：仓库/组件/版本、来源、原LICENSE/NOTICE/版权或归属声明、修改说明、实际构建依赖及许可、适用的对应源码/构建材料。保留已有工具和声明，缺失部分补齐；不新建许可证平台。

候选未取得文件时标“未取得”；锁文件只有license字段时标“元数据”，不写成逐包正文核验；商业模块未获授权时不计入可交付。R03～R05获得实际依赖集合后补必要项，Z01再按最终交付包核对。

当前不能给出：全部许可兼容、全部源码已取得、私有功能可免费使用、客户部署已经合法合规或已通过安全审计等结论。R01完成的是发现并登记这些边界，未解决项仍有效。
