"""Generate a masked rehearsal copy from retained B17 evidence; no business requests."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.development/private/b17-core-20261031'
PRIVATE = ROOT / '.development/private/b18-pilot-20261031'
OUTPUT = ROOT / 'evidence/B18/rehearsal-package'
INPUTS = [
    'forward-audit.json', 'reverse-audit.json',
    'continuation-06-request.json', 'continuation-07-review.json', 'continuation-08-sign.json',
    'continuation-10-issue-submit.json', 'continuation-12-return-submit.json',
    'continuation-21-manufacture-four-submit.json', 'continuation-25-manufacture-six-submit.json',
    'continuation-27-reports.json', 'continuation-after-reverse-27-reports.json',
    'continuation-35-original-preserved.json', 'final-source-check.json',
]
HEADERS = {
    'orders.csv': ['证据性质', '快照阶段', '脱敏工单号', '来源工单', '审批状态', '执行状态', '计划数量', '成品入库数量', '成品库存单位', '记录时间'],
    'approvals.csv': ['证据性质', '脱敏工单号', '动作', '岗位代号', '审批状态', '记录时间'],
    'reports.csv': ['证据性质', '快照阶段', '脱敏报工号', '脱敏工单号', '工序代码', '岗位代号', '状态', '良品数量', '不良数量', '库存单位', '有效秒数', '更正原单', '记录时间'],
    'stock.csv': ['证据性质', '快照阶段', '脱敏流水号', '脱敏工单号', '动作', '岗位代号', '状态', '行号', '脱敏物料码', '库存数量', '库存单位', '原领料关联', '记录时间'],
    'manual-sample.csv': ['抽检序号', '实际日期', '脱敏工单号', '范围与原始对照索引', '审批核对', '报工核对', '领退料核对', '入库核对', '权限与纠错核对', 'AI核对', '问题及原卡', '验收人代号', '接受结果', '记录状态'],
}
NATURE = '合成自动化历史回执；非现场使用'
DOCSTATUS = {0: '草稿', 1: '生效', 2: '已取消'}


def load_sources():
    data = {name: json.loads((SOURCE/name).read_text()) for name in INPUTS}
    order = data['forward-audit.json']['order']
    reverse = data['reverse-audit.json']
    assert order['production_item'].startswith('b17-core-')
    assert reverse['order']['name'] == order['name']
    assert data['forward-audit.json']['old_rows_unchanged'] and reverse['old_rows_unchanged']
    assert order['qty'] == order['produced_qty'] == 10 and reverse['order']['produced_qty'] == 0
    return data


def build_rows(data):
    forward = data['forward-audit.json']
    reverse = data['reverse-audit.json']
    order = forward['order']
    aliases = {order['name']: 'WO-SIM-001', order['previous_work_order']: 'WO-SIM-000',
               order['production_item']: 'MAT-SIM-FG', order['required_items'][0]['item_code']: 'MAT-SIM-RM',
               order['stock_uom']: 'UOM-SIM-FG', order['required_items'][0]['stock_uom']: 'UOM-SIM-RM'}
    aliases.update({row['name']: f'OP-SIM-{i:02}' for i, row in enumerate(order['operations'], 1)})
    aliases.update({name: f'RPT-SIM-{i:03}' for i, name in enumerate(sorted(r['name'] for r in reverse['reports']), 1)})
    aliases.update({name: f'SE-SIM-{i:03}' for i, name in enumerate(sorted(r['name'] for r in reverse['stock']), 1)})
    rows = {name: [] for name in HEADERS}
    for stage, snapshot in [('正向完成', forward), ('逆向更正后', reverse)]:
        doc = snapshot['order']
        rows['orders.csv'].append([NATURE, stage, aliases[doc['name']], aliases[doc['previous_work_order']],
            doc['workflow_state'], {'Completed':'已完成', 'In Process':'进行中'}[doc['status']],
            doc['qty'], doc['produced_qty'], aliases[doc['stock_uom']], doc['modified']])
    for source, action, role in [('continuation-06-request.json','送审','发起-A'),
                                ('continuation-07-review.json','审核通过','审核-A'),
                                ('continuation-08-sign.json','签批通过','签批-A')]:
        doc = data[source]
        rows['approvals.csv'].append([NATURE, aliases[doc['name']], action, role, doc['workflow_state'], doc['modified']])
    for stage, source in [('正向完成','continuation-27-reports.json'), ('逆向更正后','continuation-after-reverse-27-reports.json')]:
        for report in data[source]['result']:
            rows['reports.csv'].append([NATURE, stage, aliases[report['name']], aliases[report['work_order']],
                aliases[report['operation_id']], '报工-A', report['record_state'], report['good_qty'],
                report['bad_qty'], aliases[report['unit']], report['effective_seconds'],
                aliases[report['amended_from']] if report['amended_from'] else '', report['confirmed_at']])
    original = data['continuation-35-original-preserved.json']
    original_unit = json.loads(original['report_metrics_context'])['unit']
    rows['reports.csv'].append([NATURE, '逆向更正后', aliases[original['name']], aliases[original['work_order']],
        aliases[original['operation_id']], '报工-A', DOCSTATUS[original['docstatus']], original['total_completed_qty'],
        original['process_loss_qty'], aliases[original_unit], original['report_effective_seconds'], '', original['creation']])
    for stage, snapshot in [('正向完成', forward), ('逆向更正后', reverse)]:
        statuses = {r['name']: r['docstatus'] for r in snapshot['stock']}
        for source, action in [('continuation-10-issue-submit.json','领料'), ('continuation-12-return-submit.json','退料'),
                               ('continuation-21-manufacture-four-submit.json','部分成品入库'), ('continuation-25-manufacture-six-submit.json','剩余成品入库')]:
            doc = data[source]
            for item in doc['items']:
                linked = item['against_stock_entry']
                rows['stock.csv'].append([NATURE, stage, aliases[doc['name']], aliases[doc['work_order']], action,
                    '仓管-A', DOCSTATUS[statuses[doc['name']]], item['idx'], aliases[item['item_code']],
                    item['transfer_qty'], aliases[item['stock_uom']], aliases[linked] if linked else '', doc['modified']])
    for number in range(1, 21):
        rows['manual-sample.csv'].append([number]+['']*(len(HEADERS['manual-sample.csv'])-2)+['未执行'])
    return rows, aliases


def write_csv(name, rows):
    with (OUTPUT/name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS[name])
        writer.writerows(rows)


def verify_output(rows, aliases):
    expected_counts = {'orders.csv':2, 'approvals.csv':3, 'reports.csv':7, 'stock.csv':12, 'manual-sample.csv':20}
    forbidden = ['@', '预计工资', '薪资', '身份证', '手机号', 'api_secret', 'api_key']
    for name, expected in expected_counts.items():
        content = (OUTPUT/name).read_text(encoding='utf-8-sig')
        table = list(csv.reader(content.splitlines()))
        assert table[0] == HEADERS[name] and len(table)-1 == expected, name
        assert all(len(row)==len(HEADERS[name]) for row in table), name
        assert not any(value in content for value in forbidden), name
        assert not any(value in content for value in aliases if value not in ('Nos',)), name
    samples = rows['manual-sample.csv']
    assert all(not any(row[1:-1]) and row[-1]=='未执行' for row in samples)
    reports = rows['reports.csv']
    assert sorted(r[7] for r in reports if r[1]=='正向完成') == [10,10,10]
    assert sorted(r[7] for r in reports if r[1]=='逆向更正后' and r[6]=='生效') == [8,10,10]
    corrected = next(r for r in reports if r[1]=='逆向更正后' and r[7]==8)
    cancelled = next(r for r in reports if r[1]=='逆向更正后' and r[6]=='已取消')
    assert corrected[11]==cancelled[2] and cancelled[7]==10
    return {'rows':expected_counts, 'sample_slots':20, 'actual_manual_samples':0,
            'masked_copy_checks_passed':True, 'source_business_reexecuted':False,
            'product_privacy_accepted':False, 'real_field_acceptance':False}


def main():
    data = load_sources()
    rows, aliases = build_rows(data)
    OUTPUT.mkdir(exist_ok=True)
    for name, content in rows.items():
        write_csv(name, content)
    result = verify_output(rows, aliases)
    manifest = {'kind':'B17 retained synthetic evidence rehearsal copy', 'source_record_date':'2026-10-31',
        'head':data['final-source-check.json']['head'], 'patch_sha256':data['final-source-check.json']['patch_sha256'],
        'source_files':{name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in INPUTS},
        'outputs':{name:hashlib.sha256((OUTPUT/name).read_bytes()).hexdigest() for name in HEADERS},
        'real_field_acceptance':False}
    (OUTPUT/'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    (OUTPUT/'README.md').write_text('''# B18 脱敏演练证据包

本包从B17已保存的合成自动化回执生成，属于历史快照副本。不是本轮业务重跑、现场使用记录、人工抽检或验收签收。

工单WO-SIM-001及来源WO-SIM-000、工序OP-SIM、报工RPT-SIM、库存SE-SIM、物料MAT-SIM使用稳定别名。库存单位UOM-SIM-FG/RM亦为别名，数量直接取原库存单位，未换算。原始映射仅留受限本地目录。本包没有姓名、邮箱、工号、工资、金额、价格或BOM原文；这不证明原系统页面/日志已脱敏。

- orders.csv：同一工单正向/逆向两个时点，不能当成两张工单。
- approvals.csv：原三次审批动作；岗位代号不改变原C10授权，模拟工程师/主管岗位映射仍待确认。
- reports.csv：正向3笔及逆向3笔生效＋1笔取消记录；同一记录跨快照出现不代表新增报工。
- stock.csv：领料、已取消退料、两笔成品入库的两阶段明细。状态按对应快照；记录时间取原提交回执时间，未记录取消事件时间，不能用它计算取消耗时；原领料关联保留。
- manual-sample.csv：20个空抽检位置。实际日期、工单、原始对照、核对、验收人、接受结果均留空，状态未执行。它不是20张工单、20次人工抽检或通过率。
- source-manifest.json：输入/输出hash与B17候选版本；不能当当前运行环境或现场版本证明。

实际抽检须由获准验收人按既定范围填写日期、工单和线下对照，逐项核对审批、报工、领退料、入库、权限/纠错和AI，记录问题原卡及接受结果。空项和未具备的AI能力保持未验证，不能填通过。本包不提供现场成功率、审批平均耗时、一致率或零缺陷结论。

观察计划仅为用户模拟输入：2026-11-16至12-11，周五11-20、11-27、12-04、12-11。没有生成周报或启动周期任务；90天留存仍待明确起算和范围，没有自动删除。独立返修、离线审批、岗位更改和系统隐私差异仍未实施/验收。

本包由`python3 .development/checks/b18_pilot_package.py`从源回执生成。生成文件不手改，正式抽检另存获准填写副本。原始明细、证据及历史记录不删除。B18完整验收仍需要B17/A01～A03前置、真实人员、设备、周期及业务接受。
''')
    (PRIVATE/'rehearsal-aliases-private.json').write_text(json.dumps(aliases, ensure_ascii=False, indent=2)+'\n')
    (PRIVATE/'rehearsal-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    for name in ('rehearsal-aliases-private.json','rehearsal-verification.json'):
        (PRIVATE/name).chmod(0o600)
    print(json.dumps(result, ensure_ascii=False))


if __name__=='__main__':
    main()
