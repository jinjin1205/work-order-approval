# R05 隔离评估环境

只服务于本项目R05核验；不是客户交付包。CLI阶段后新增本机Web用于普通HTTP和小屏核验，见`compose.web.json`；只监听127.0.0.1:18085。最终运行/停止状态以环境记录中本轮补证收尾为准，卷中保留合成证据。

- 项目：`xgd-r05-20261026`；站点：`r05.localhost`。
- 应用镜像固定ARM64 digest；数据库/Redis本次实际摘要见[环境记录](../../evidence/R03-R05/environment.md)。未来复验应确认镜像身份，不假定系列标签不变。
- `.env`仅为随机测试凭证，权限0600；不要提交、复制到报告或打印。
- `access-secrets.json`是本轮普通测试用户凭证，权限0600且已忽略；同样禁止打印或进入证据。
- 当前`probes/`为已经执行过的一次性评估脚本；不能原样重复执行。现有结果不可覆盖，合成前缀不可复用。新验证需明确变化的输入和新的输出文件。
- 只有恢复核验时才运行：`docker compose -f .evaluation/r05-erpnext/compose.json up -d --wait db redis-cache redis-queue`。
- 需普通HTTP或网页时，沿用两个文件恢复：`docker compose -f .evaluation/r05-erpnext/compose.json -f .evaluation/r05-erpnext/compose.web.json up -d --wait db redis-cache redis-queue web`。已有站点不要重新初始化，写入前先查原单状态。
- Web使用官方entrypoint以准备assets；`bench serve --noreload`＋CI=1仅用于本机评估，没有websocket/完整生产服务，不能当客户部署包。
- 同一数据库上的写入/测试按顺序执行。console要显式exec命名空间；console退出0不代表脚本无异常，必须核JSON和日志。
- 已有配置/数据不需重建站点。结束时只stop本项目服务；不删卷、不prune、不关闭用户Docker Desktop。

真实执行、失败尝试和未验证项以[运行记录](../../evidence/R05/run-record.md)为准。没有改产品代码。
