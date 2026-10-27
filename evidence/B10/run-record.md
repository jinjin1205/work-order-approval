> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B10 实耗与领料上限单位子项执行记录

2026-10-26，执行者Codex。结论：**本轮单位子项完成限定验证；B10整卡仍部分完成。** 依据原B10卡、R07 quantity-return.md及R02 U01，复用B01独立环境；未操作R05或客户库。

## 版本、范围与最小改动

ERPNext v15.124.1/`4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e`，Frappe v15.124.0原版。一个`codex/xgd-maintenance`维护分支，没有新库存账、新换算框架或依赖。与B02共同改动3个业务文件及对应3个测试文件；本子项产品改动仅4处字段引用：

1. `work_order.py:update_consumed_qty_for_required_items`：`SUM(detail.qty)`改`SUM(detail.transfer_qty)`；工单、单据状态、用途、来源仓、原料/替代关系过滤不变。
2. `stock_entry.py:_validate_no_excess_transfer`：累计使用`transfer_qty`，比较精度使用`transfer_qty`，提示单位使用`stock_uom`。原退料及按转移量回冲的提前返回不变。

复用`set_transfer_qty`原生换算；既有validate先换算后限额检查。不加qty兜底、不重复换算、不改库存过账、退料生成器或数据库字段。旧直接调用限额方法的精度测试补齐stock_uom/conversion_factor并先调用原生换算，符合实际调用顺序。

## 样例与预期

`test_work_order.py:TestWorkOrderStockUnits`自行创建真实合成公司下物料、两个换算单位、BOM、工单和三仓；通过原入口收料、领料、退料、提交实耗、取消。未mock库存或Work Order汇总。

| 输入/动作 | 预期与修后实际 |
|---|---|
| 库存单位kg，交易单位g，换算0.001；领0.001kg，退0.0004kg | 工单领0.001、退0.0004，WIP0.0006kg |
| 耗0.5g | 源行仍0.5g，库存数量0.0005kg，工单实耗0.0005kg，WIP0.0001kg |
| 取消这张实耗单 | 工单实耗0，WIP恢复0.0006kg；取消单docstatus=2及原行0.5保留 |
| 两工单同物料；本单草稿、提交、取消 | 草稿不计入，提交本单0.0003kg；另单0.0002kg互不冒充；取消仅恢复本单 |
| 领料限额0.5kg：500g/600g；限额500g：0.5kg/0.6kg | 前者各允许，后者各拒绝 |
| 两行0.2kg＋300g/400g；同单位0.5kg/0.6kg | 等额允许，超额拒绝 |
| qty精度3、库存数量精度6，限额0.0005kg、领0.6g | 换算0.0006kg，拒绝；不能用交易数量精度掩盖超额 |

最后三行用真实Document及原生set_transfer_qty/限额方法作受控测试，**不冒称每个限额子例都完成真实库存提交**。U01和跨工单例确实完成数据库/库存提交与取消。

测试用原生`change_settings`临时六位精度及必要生产设置，结束恢复；不是把产品全局精度改成6来宣称G1完成。末次站点回读仍为原3位/银行家舍入。

## 失败与通过证据

| 日志 | 实际结果 |
|---|---|
| `consumption-red.log` | 2项中1失败：库存已0.0005kg，工单实耗却0.5 |
| `transfer-red.log` | 3项中1失败、2错误（同一方法的子例）：500g误拒；0.6kg绕过500g；混合单位误拒 |
| `consumption-green.log`、`transfer-green.log` | 初轮2＋3通过；保留为阶段结果 |
| `acceptance-consumption.log` | **最终2项，OK，4.519秒**，真实提交/取消与过滤 |
| `acceptance-transfer.log` | **最终3项，OK，1.218秒**，含8个正反/混合/同单位子例及独立精度验证 |

测试前后有独立源码审查，未发现本4处字段修补引入的阻塞问题。取消库存单保留的证据不等于报工原记录已保护，G2不变。

## 命令

在项目根目录；同一测试库串行执行，不能并行改共享设置：

```sh
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --case TestWorkOrderStockUnits --skip-test-records --skip-before-tests
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.stock.doctype.stock_entry.test_stock_entry --test test_transfer_limit_uses_stock_uom --test test_transfer_limit_uses_stock_quantity_precision --test test_material_transfer_for_manufacture_qty_precision --skip-test-records --skip-before-tests
```

仅跳过全量fixture/hook，真实最小资料自行建立；原生业务校验仍执行。沿用现有测试文件，不安装支付模块，不做无关全量回归。

## 最终运行对象与环境

- 合并工作区补丁SHA256：`221937fbf2f011d04012aa6e0a602a982d65edb5e9a72b7b53f40060322ec5d3`。基线和工作区差异见[完整补丁](combined-implementation.patch)、[文件清单](../../.development/checks/b02-b10-source-manifest.json)。改动未提交/推送，未触发远程CI。
- 实际开发Web与最终HTTP服务镜像均`sha256:79f41c4bba83946a1bb0fe59c4c928a62e56bb6b2e1040f9351a90981e54653c`，见`acceptance-runtime-images.txt`。该文件采集后临时HTTP服务已停。
- `acceptance-bench-source.json`和`acceptance-web-source.json`：**13个源码/测试/翻译/元数据文件逐一一致**，三个业务模块解析到独立维护源码。不是整个镜像逐文件审计。
- `acceptance-dev-site.json`：中文/China/CNY/Shanghai，allow_tests=false，工单/卡/库存单均0；`acceptance-test-site.json`：独立库、allow_tests=true，保留2工单/2卡/2库存单，数量精度已恢复3。未把测试写入开发库。
- `acceptance-r05-state.txt`：历史R05四个服务仍exited。没有候选重部署或数据清理。
- Ruff采用仓库指定0.2.0，仅在`/private/tmp`运行；本次6文件lint/format及`git diff --check`通过。未修改产品依赖、无关旧代码或Frappe。
- 开发网页继续在`http://127.0.0.1:18086`；最终`/login`真实HTTP返回200且有中文登录文本（`acceptance-web-http.json`）；本轮未重新做浏览器登录操作验收，界面基线沿用B01。

源码再核对入口：

```sh
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b02-b10-source-manifest.json
```

## 保留事项与停止点

G1全程十进制/损耗、G2逐笔报工及岗位回写、G3并发继续未通过。完整领料审批/权限、库存成本、库存不足/错仓、替代料不同库存单位、批次/序列号、退料生成与全部CASE-06/07均不由本轮结果替代。

只完成单位子项，达到结束条件即停止。本轮没有AI调用、客户部署或现场业务验收。
