> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# R07｜中文界面与中国公司配置绑定

2026-10-26。依据用户本轮明确要求及C08。**本页为源码核查与待实施步骤，不是已完成中文运行验收。** 保留R05英文/INR/纽约时区原始证据，后续新开发站点按本页配置。

## 可复用入口

源路径均相对对应应用包；本机只读快照在源码目录（仅本地保留；见 publication/evidence-index.json）。版本同[R06](../R06/selection.md)，文件身份见[source-manifest.json](source-manifest.json)。

| 已存在位置 | 已核行为 | 分类及允许动作 |
|---|---|---|
| Frappe `core/doctype/system_settings/system_settings.json:127–198,712`、`.py:204–221` | 有country/language/time_zone/currency/date_format/time_format；保存更新默认值和语言/时区缓存 | 配置使用。新站点简体中文`zh`、中国、Asia/Shanghai、CNY；日期`yyyy-mm-dd`、24小时。时区字段只读，使用原生新站点Setup Wizard，不直接改旧R05库 |
| Frappe `geo/languages.json`、`core/doctype/user/user.json:203–213`、`translate.py:33–106` | 简体`zh`与繁体分开；登录用户语言优先于系统默认，访客可受cookie/header影响 | 配置使用。所有试点测试账号设zh，验证退出/重新登录与访客登录页；只改系统默认不足以验收 |
| Frappe `desk/page/setup_wizard/setup_wizard.py:update_system_settings/create_or_update_user/set_timezone`；ERPNext `setup/setup_wizard/operations/install_fixtures.py:424–476` | 原生向导设置语言/时区并创建公司和本位币；会设置精度3/银行家舍入 | 复用新站点向导。中文配置完成后按B04设置数量精度/舍入，不能让向导默认值覆盖数量要求 |
| ERPNext `locale/zh.po`；Frappe `translations/zh.csv`、`translate.py:135–237`、`gettext/translate.py:247–277,346` | ERPNext用PO/MO，框架兼容CSV与MO，并可叠加原生Translation记录 | 直接复用词库；必要术语用原生Translation记录覆盖，新增业务文案仍走已有翻译入口。不建翻译服务 |
| Frappe `core/doctype/translation/translation.py`、`commands/gettext.py:19–37` | 原生翻译保存/缓存和`compile-po-to-mo --app --locale --force`入口 | 配置/必要词条改动；不是重写Frappe。缺MO时才按原命令编译，仅zh |

初查`erpnext/translations/zh.csv`不存在；随后实际目录核对定位到`erpnext/locale/zh.po`，未把首次路径不存在当成缺中文支持。已读词条如下：

| 业务词 | 底座现有翻译 | 本项目采用术语 |
|---|---|---|
| Work Order | 工单 | 工单 |
| Job Card | 工作卡 | 作业卡；是否作为逐笔报工承载依B08绑定，不仅改名冒充任务 |
| Stock Entry | 手工库存移动 | 库存单 |
| Material Transfer for Manufacture | 材料移送用于制造 | 生产领料 |
| Return Components | 退货组件 | 退料 |
| Start Job / Complete Job | 启动作业／完成作业 | 开工／完成作业；正式报工确认文案由B08语义决定 |
| Draft / Submitted | 草案／已提交 | 草稿／已提交 |

## 绑定步骤和验收

- [ ] B01在新的开发/测试站点通过原生向导设中国、简体中文、上海时区、人民币；新测试公司用中文名称。保留R05站点不迁移、不改历史时区和币种。公司本位币在记库存前确定。
- [ ] B14使用原生Translation覆盖上述必要术语。代码对象名、单号、物料型号等原始标识不翻译；无关ERP模块和其他语言资源不删除。
- [ ] B02/B08/B11的无权限、超报、超退、已取消、重复请求、冲突和失败恢复提示均给出明确中文动作建议，异常详情保留后台日志，界面不显示英文堆栈或假成功。
- [ ] 新开发站点中，必要时在bench目录运行已核原生命令：`bench compile-po-to-mo --app erpnext --locale zh --force`；随后`bench --site xgd-dev.localhost clear-cache`。这是待执行命令，不在R07运行，也不以编译退出0证明页面全部中文。
- [ ] 普通操作工/仓管分别登录PC和390×844页面，核工单、工序、作业卡、领退料、报工/冲销、数量和失败提示；登出再登录，中文不回退英文。只覆盖首版入口；真机由B13/B18另验。
- [ ] 页面与明细导出列名使用中文、数量口径相同；日期按上海时区，金额用人民币。屏幕截图＋配置回读＋导出样例分别留存，不能用英文页面截图作为中文验收。

**结束边界：**B01只验中文初始化和身份默认；B14承接词条，业务卡承接自身正常/错误页面，B16承接导出，B13/B18承接真机。未开发英文交付版本；保留上游英文标识不是增加英文产品。没有引入中国财务/税务/发票/工资结算功能或新增第三方服务。
