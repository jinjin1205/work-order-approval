> 公开归档副本（2026-10-31）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。

# B13 手机网页、扫码及弱网恢复限定包

2026-10-31统一整理本地回执；范围见原卡和R07。维护基底`4e0dce9`；复用原生页面/Scanner和B09请求键，不新增字段、离线事实队列或新确认入口。

- 新增API定位2项和库存设置3项分批通过；首批设置fixture参数错误保留，修后只跑受阻3项。`docker exec -w /home/frappe/frappe-bench xgd-b08-check env/bin/python /b01/b06_tasks_tests.py <TestProductionMobileBoundaries具体方法>`；另有受控UI return/restore/restore-empty，不能冒充实际页面。
- Playwright CLI `b13`/`b13-report`实际桌面Chromium触屏模拟：领10退2；退料提交200后丢响应，重开同原单已提交。报工200后丢响应，刷新原键查询找回唯一原报工，0次重发确认；另一次确认前断网保留原输入/键，恢复后同键重试仅1笔。
- `run-code --filename=.development/checks/b13_report_recover_browser.js`、`b13_report_offline_ready_browser.js`及`b13_stock_drop_browser.js`为实际浏览器脚本。旧恢复页面阻塞及大量预览请求失败保留；改为原payload一次初始化和待核期间抑制预览，未猜测底层循环成因。
- 原生扫码真实相机权限拒绝后中文回退、手输定位通过；向Scanner回调注入解码结果仅证明后续定位，未证明镜头识别。实际内容视口库存390×844、恢复后报工390×664，非全程同尺寸。
- `/b01/b13_mobile_fixture.py audit`最终31旧表missing/changed均0，领10退2净8/消耗0，两个报工场景各1笔。两容器43文件/22Python匹配编译、4份JS语法和diff检查通过。

真机Android/iOS/Safari/PDA、实际镜头识别、现场弱网、手机完整发起/审核/签批、非开发人员接手、完整G3及Z01未验证。整卡部分完成。原始回执、失败、单据、截图与凭据只留本地，本次收尾未重跑上述流程。
