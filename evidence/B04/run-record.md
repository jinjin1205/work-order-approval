> 公开归档副本（2026-10-27）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B04 最终需求数量独立子项

2026-10-27。按用户纠偏授权，在原卡执行Q05最终数量子项，不等待B19整卡。起点公开9098e5ed62e5571255c0aee1de9e39a0c624bf7e，ERPNext15.124.1/Frappe15.124.0固定，产品原补丁a6478acc8c02c08b2b2775c273f802a45c0871196c51e5e12c160766f718d25d。

范围：原WorkOrder.set_required_items最终输出，追加/reset两路径；复用原BOM展开、原生商用四舍五入能力和Stock Entry。首版最终需求四位，不改变BOM原始用量、共享BOM计算、库存估价或Frappe。Q05 3×0.000050最终0.0002；保存重读、原生领料草稿/提交均一致。Q01/Q02/Q04、父项基数和半值舍入作相关回归。完整十进制、材料损耗、工时/指标未据此关闭；先保存真实失败再决定最小修补。

Ruling：仅最终结果四位的局部规则使用上游现有舍入，不包装成全程Decimal。成本/风险是中间精度和完整输入边界仍归G1，不能据局部通过宣称全部数量正确。本批不新增通用计算服务或重建账本。最小fixture沿现有make_item/make_bom/make_wo_order_test_record/Stock Entry，合成输入、普通原生校验，事务回滚；管理员仅用于独立计算测试，岗位验收不能据此通过。

执行计划：1. 只新增现有测试文件内TestWorkOrderRequiredQuantity并核实际镜像源码；先验fixture可运行。2. 运行四项，保留基线失败；在R07允许范围修最终输出。3. 同一版本复测本类和受影响B10单位测试，核原数据不变。4. 收口此子项，转原B19中文可操作阶段，不继续无限扩数量例。

最小fixture 1项/1.515秒OK。原实现4项中1通过、3失败（red-results.log，6.306秒）：Q05实际0.00015，reset实际0.00025，父项基数2实际4.16665；预期分别0.0002、0.0003、4.1667。产品只在set_required_items读取原展开结果后统一调用现有flt(...,4,rounding_method="Commercial Rounding")，供追加和reset共用；未改变BOM输入/展开，也未声称float已成为Decimal。

最终受控结果：fixed-results.log 4项/4.571秒OK；unit-regression.log原TestWorkOrderStockUnits 2项/5.267秒OK。source-final.json核对14个运行文件一致；data-before.json/data-after.json原11张业务表完全一致，原测试站点无Workflow。独立审查未发现本数量增量的新问题，仅静态审查不算重复运行。完整G1/G2/G3保留。

```sh
docker compose -f .development/compose.json build bench
docker compose -f .development/compose.json run --rm --no-deps -T bench env/bin/python /b01/check_source.py /b01/b04-source-manifest.json
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --case TestWorkOrderRequiredQuantity --skip-test-records --skip-before-tests
docker compose -f .development/compose.json run --rm --no-deps -T -e CI=1 bench bench --site xgd-test.localhost run-tests --app erpnext --module erpnext.manufacturing.doctype.work_order.test_work_order --case TestWorkOrderStockUnits --skip-test-records --skip-before-tests
```

限制：管理员用于计算/库存原生入口的回滚测试，不代表普通岗位验收。测试内临时float_precision=6用于保留输入，回滚恢复；持久精度配置和完整Decimal未交付。本子项已达到结束条件，转中文操作，不继续扩数量范围。后续从六位链和Q03材料损耗实际未完成处续接。
