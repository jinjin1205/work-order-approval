"""R02 文档预期的独立算术复核；不是产品代码或候选应用测试。"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo


root = Path(__file__).resolve().parent
D = Decimal
checks = []


def check(name, actual, expected):
    passed = actual == expected
    checks.append({"id": name, "actual": str(actual), "expected": str(expected), "passed": passed})


for key, plan, unit, base, loss, expected in [
    ("Q01", "100", "0.5495", "1", "0", "54.9500"),
    ("Q02", "100", "0.083333", "1", "0", "8.3333"),
    ("Q03", "100", "0.5", "2", "0.1", "27.5000"),
    ("Q04", "100", "0.000167", "1", "0", "0.0167"),
    ("Q05", "3", "0.00005", "1", "0", "0.0002"),
]:
    value = (D(plan) * D(unit) / D(base) * (1 + D(loss))).quantize(D("0.000001"), rounding=ROUND_HALF_UP)
    check(key, value.quantize(D("0.0001"), rounding=ROUND_HALF_UP), D(expected))

check("CASE01-demand", D("10") * D("0.5"), D("5"))
check("CASE01-source-stock", D("20") - D("5"), D("15"))
check("U01-net-kg", D("0.001") - D("0.0004"), D("0.0006"))
check("U01-net-g", (D("0.001") - D("0.0004")) * 1000, D("0.6"))
check("V01-value", D("10") * 2 + D("10") * 4, D("60"))
check("V01-average", D("60") / 20, D("3"))
check("V02-quantity", D("20") - 5, D("15"))
check("V02-value", D("60") - 5 * D("3"), D("45"))
check("M01-M02-yield-percent-excluding-rework", D("8") / (D("8") + D("2")) * 100, D("80"))
check("M01-remaining", max(D("0"), D("10") - D("8") - D("2")), D("0"))

tz = ZoneInfo("Asia/Shanghai")
for key, start, end, rest, expected_report, expected_effective in [
    ("T01", "2026-10-20T09:00:00", "2026-10-20T17:00:00", 3600, 28800, 25200),
    ("T02", "2026-10-20T22:00:00", "2026-10-21T02:00:00", 7200, 14400, 7200),
    ("T04", "2026-10-20T12:30:00", "2026-10-20T12:45:00", 900, 900, 0),
]:
    elapsed = int((datetime.fromisoformat(end).replace(tzinfo=tz) - datetime.fromisoformat(start).replace(tzinfo=tz)).total_seconds())
    check(key + "-report", elapsed, expected_report)
    check(key + "-effective", elapsed - rest, expected_effective)

check("T03-shutdown-limit", max(0, 28800 - 3600), 25200)
check("T03-reject-excess", 28800 > 25200, True)
check("T05-estimated-wage", D("7200") / 3600 * 10, D("20"))
check("T06-effective", 28800 - 3600 - 3600 + 1800, 23400)
check("T07-reject-excess", 3601 > 3600, True)
check("T10-no-rule-effective", 3600 - 0 - 0 + 0, 3600)
check("T11-union-rest", 3600 + 3600 - 1800, 5400)
check("T11-effective", 28800 - 5400, 23400)
check("CASE05-full-reversal-net", 10 - 10 + 8, 8)
check("CASE05-partial-reversal-net", 10 - 2, 8)
check("CASE05-remaining", 10 - 8, 2)
check("CASE06-source-stock", 20 - 10 + 2, 12)
check("CASE06-net-issued", 10 - 2, 8)
check("CASE06-cumulative-progress", D("10") / 10 * 100, D("100"))
check("CASE06-unknown-difference", 8 - 7, 1)

result = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "仅R02合成预期的独立算术核对；未执行候选代码或业务路径",
    "command": "python3 evidence/R02/verify-arithmetic.py",
    "python_version": platform.python_version(),
    "fixture_version": "v1",
    "documents_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ["fixture-spec.md", "expected-results.md", "verify-arithmetic.py"]},
    "checks": checks,
    "passed": sum(item["passed"] for item in checks),
    "failed": sum(not item["passed"] for item in checks),
    "application_run": False,
    "ai_real_run": False,
    "restore_run": False,
    "field_acceptance": False,
}
(root / "arithmetic-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ["scope", "passed", "failed", "application_run"]}, ensure_ascii=False))
if result["failed"]:
    raise SystemExit(1)
