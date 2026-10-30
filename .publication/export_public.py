"""Build an explicit public snapshot; never traverse credentials or runtime stores."""
import hashlib
import json
import re
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".publication/work-order-approval"
REPO = ROOT / ".development/repos/erpnext"
BASE = "4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e"
history_paths_manifest = json.loads((ROOT / ".development/checks/b08-history-paths-source-manifest.json").read_text())
details_manifest = json.loads((ROOT / ".development/checks/b05-details-source-manifest.json").read_text())
closeout_manifest = json.loads((ROOT / ".development/checks/b05-closeout-source-manifest.json").read_text())
header_manifest = json.loads((ROOT / ".development/checks/b05-header-source-manifest.json").read_text())
entries_manifest = json.loads((ROOT / ".development/checks/b05-entries-source-manifest.json").read_text())
manifest = json.loads((ROOT / ".development/checks/b08-quality-source-manifest.json").read_text())
metrics_manifest = json.loads((ROOT / ".development/checks/b08-metrics-source-manifest.json").read_text())
followup_manifest = json.loads((ROOT / ".development/checks/b08-followup-source-manifest.json").read_text())
changes = subprocess.check_output(["git", "diff", "--name-only", BASE], cwd=REPO, text=True).splitlines()
patch = subprocess.check_output(["git", "diff", BASE], cwd=REPO)
assert len(changes) == 31
assert hashlib.sha256(patch).hexdigest() == manifest["patch_sha256"]
assert patch == (ROOT / "evidence/B08/quality-20261030/implementation.patch").read_bytes()
for name in changes:
    assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == manifest["files"][name]

published = {}
receipt = []

def add(path, content, source=None, treatment="unchanged"):
    assert not path.startswith("/") and ".." not in Path(path).parts
    data = content.encode() if isinstance(content, str) else content
    published[path] = data
    if source:
        receipt.append({"source": source, "public_path": path, "treatment": treatment,
                        "source_sha256": hashlib.sha256((ROOT / source).read_bytes()).hexdigest()})

def portable(text):
    text = text.replace(str(ROOT), ".")
    text = text.replace(str(Path.home() / "Downloads") + "/", "[本地原始资料]/")
    text = text.replace(str(Path.home() / "Documents") + "/", "[本地文档]/")
    text = re.sub("/" + r"Users/[^/\s`]+/", "[本地用户目录]/", text)
    text = re.sub(r"(?:MFG-WO-\d{4}-\d+|PO-JOB\d+|MAT-STE-\d{4}-\d+|B02-[A-Za-z0-9]{8}|B10-[A-Za-z0-9]{8})", "[本地样例编号已移除]", text)
    return text

# Sources contain fixture definitions, not exported runtime records; preserve exact bytes.
for name in changes:
    add("source/erpnext/" + name, (REPO / name).read_bytes(), ".development/repos/erpnext/" + name)
add("source/erpnext/license.txt", (REPO / "license.txt").read_bytes(), ".development/repos/erpnext/license.txt")
for name in ("evidence/B08/quality-20261030/implementation.patch", "evidence/B08/quality-20261030/bounded-change.patch", "evidence/B08/navigation-20261030/implementation.patch", "evidence/B08/navigation-20261030/bounded-change.patch", "evidence/B07/materials-20261029/implementation.patch", "evidence/B07/materials-20261029/bounded-change.patch", "evidence/B06/tasks-20261029/implementation.patch", "evidence/B06/tasks-20261029/bounded-change.patch", "evidence/B05/entries-20261029/implementation.patch", "evidence/B05/entries-20261029/bounded-change.patch", "evidence/B05/header-20261029/implementation.patch", "evidence/B05/header-20261029/bounded-change.patch", "evidence/B05/closeout-20261029/implementation.patch", "evidence/B05/closeout-20261029/bounded-change.patch", "evidence/B05/explicit-details-20261029/implementation.patch", "evidence/B05/explicit-details-20261029/bounded-change.patch", "evidence/B10/combined-implementation.patch", "evidence/B19/combined-implementation.patch",
             "evidence/B19/b19-only.patch", "evidence/B19/execution-gate/combined-implementation.patch",
             "evidence/B19/entry-history/combined-implementation.patch",
             "evidence/B19/approved-changes/combined-implementation.patch",
             "evidence/B04/combined-implementation.patch", "evidence/B19/chinese-flow/combined-implementation.patch",
             "evidence/B04/precision-loss/combined-implementation.patch", "evidence/B04/input-ui/implementation.patch",
             "evidence/B04/time-metrics/implementation.patch", "evidence/B14/implementation.patch", "evidence/B08/implementation/implementation.patch",
             "evidence/B08/followup-20261028/implementation.patch", "evidence/B08/followup-20261028/followup-only.patch",
             "evidence/B08/metrics-20261028/implementation.patch", "evidence/B08/metrics-20261028/metrics-only.patch",
             "evidence/B08/history-paths-20261028/implementation.patch", "evidence/B08/history-paths-20261028/history-paths-only.patch"):
    add(name, (ROOT / name).read_bytes(), name)

paths = [ROOT / "AGENTS.md", *sorted((ROOT / "docs").rglob("*.md")), *sorted((ROOT / "evidence").rglob("*.md"))]
paths += [ROOT / "openspec/config.yaml"]
paths += sorted((ROOT / "openspec/changes/b08-followup-20261028").glob("*.md"))
paths += [ROOT / "openspec/changes/b08-followup-20261028/.openspec.yaml"]
paths += sorted((ROOT / "openspec/changes/explicit-order-details-20261029").rglob("*.md"))
paths += [ROOT / "openspec/changes/explicit-order-details-20261029/.openspec.yaml"]
paths += sorted((ROOT / "openspec/changes/archive/2026-10-29-b06-task-adjustments-20261029").rglob("*.md"))
paths += [ROOT / "openspec/changes/archive/2026-10-29-b06-task-adjustments-20261029/.openspec.yaml"]
paths += sorted((ROOT / "openspec/changes/archive/2026-10-29-work-order-closeout-20261029").rglob("*.md"))
paths += [ROOT / "openspec/changes/archive/2026-10-29-work-order-closeout-20261029/.openspec.yaml"]
paths += [ROOT / "openspec/specs/production-order-closeout/spec.md", ROOT / "openspec/specs/production-task-adjustments/spec.md"]
paths += sorted((ROOT / "openspec/changes/archive/2026-10-29-b07-material-boundaries-20261029").rglob("*.md"))
paths += [ROOT / "openspec/changes/archive/2026-10-29-b07-material-boundaries-20261029/.openspec.yaml", ROOT / "openspec/specs/production-material-boundaries/spec.md"]
paths += sorted((ROOT / "openspec/changes/archive/2026-10-29-work-order-header-20261029").rglob("*.md"))
paths += [ROOT / "openspec/changes/archive/2026-10-29-work-order-header-20261029/.openspec.yaml"]
paths += [ROOT / "openspec/specs/production-order-header/spec.md"]
paths += sorted((ROOT / "openspec/changes/archive/2026-10-29-work-order-entries-20261029").rglob("*.md"))
paths += [ROOT / "openspec/changes/archive/2026-10-29-work-order-entries-20261029/.openspec.yaml"]
paths += [ROOT / "openspec/specs/production-order-entries/spec.md"]
paths += sorted((ROOT / ".agents/skills").glob("openspec-*/SKILL.md"))
paths += [ROOT / ".agents/skills/.openspec-target", ROOT / ".agents/skills/playwright-cli/SKILL.md"]
paths += sorted((ROOT / ".agents/skills/playwright-cli/references").glob("*.md"))
paths += [ROOT / "third_party/workflow-licenses" / name for name in ("OpenSpec-MIT.txt", "Playwright-Apache-2.0.txt")]
paths += [ROOT / ".publication" / name for name in ("export_public.py", "check_public.py", "verify_b08.py", "check_ci_pause.py")]
paths += [ROOT / ".development" / n for n in ("Dockerfile", "compose.json", "README.md", ".dockerignore", ".gitignore")]
paths += sorted((ROOT / ".development/checks").glob("*.py"))
paths += sorted((ROOT / ".development/checks").glob("*.mjs"))
paths += sorted((ROOT / ".development/checks").glob("*manifest.json"))
paths += [ROOT / ".evaluation/r05-erpnext" / n for n in ("compose.json", "compose.web.json", "README.md")]
paths += sorted((ROOT / ".evaluation/r05-erpnext/probes").glob("*.py"))
paths += sorted((ROOT / "evidence").rglob("*.py"))
for path in paths:
    relative = path.relative_to(ROOT).as_posix()
    original = path.read_text()
    clean = portable(original)
    add(relative, clean, relative, "personal paths/runtime identifiers removed" if original != clean else "unchanged")

safe_json = [
    "evidence/发布/2026-10-30-6d4dd00-remote.json",
    "evidence/B08/quality-20261030/code-ci.json",
    "evidence/发布/2026-10-30-13f7f6f-remote.json",
    "evidence/发布/2026-10-30-a06ad21-remote.json",
    "evidence/B08/quality-20261030/source-manifest.json",
    "evidence/B08/quality-20261030/test-batches.json",
    "evidence/B08/quality-20261030/acceptance-summary.json",
    "evidence/B08/quality-20261030/http-summary.json",
    "evidence/B08/quality-20261030/old-row-audit.json",
    "evidence/B08/quality-20261030/test-runtime.json",
    "evidence/B08/quality-20261030/ui-runtime.json",
    "evidence/发布/2026-10-29-ff14ba9-remote.json",
    "evidence/B08/navigation-20261030/source-manifest.json",
    "evidence/B08/navigation-20261030/test-batches.json",
    "evidence/B08/navigation-20261030/acceptance-summary.json",
    "evidence/B08/navigation-20261030/old-row-audit.json",
    "evidence/B08/navigation-20261030/test-runtime.json",
    "evidence/B08/navigation-20261030/ui-runtime.json",
    "evidence/B06/tasks-20261029/retention-correction.json",
    "evidence/B06/tasks-20261029/retention-probe.json",
    "evidence/发布/2026-10-29-69aa1b9-remote.json",
    "evidence/B07/materials-20261029/source-manifest.json",
    "evidence/B07/materials-20261029/test-batches.json",
    "evidence/B07/materials-20261029/acceptance-summary.json",
    "evidence/B07/materials-20261029/old-row-audit.json",
    "evidence/B07/materials-20261029/test-runtime.json",
    "evidence/B07/materials-20261029/ui-runtime.json",
    "evidence/B06/tasks-20261029/source-manifest.json",
    "evidence/B06/tasks-20261029/test-batches.json",
    "evidence/B06/tasks-20261029/http-summary.json",
    "evidence/B06/tasks-20261029/old-row-audit.json",
    "evidence/B06/tasks-20261029/test-runtime.json",
    "evidence/B06/tasks-20261029/ui-runtime.json",
    "evidence/B06/tasks-20261029/acceptance-summary.json",
    "evidence/发布/2026-10-29-1f2fc31-remote.json",
    "evidence/B05/entries-20261029/source-manifest.json",
    "evidence/B05/entries-20261029/baseline-source.json",
    "evidence/B05/entries-20261029/intermediate-suite-source.json",
    "evidence/B05/entries-20261029/affected-copy-source.json",
    "evidence/B05/entries-20261029/row-facts-source.json",
    "evidence/B05/entries-20261029/stopped-cancel-source.json",
    "evidence/B05/entries-20261029/final-fixture-source.json",
    "evidence/B05/entries-20261029/final-backend-source.json",
    "evidence/B05/entries-20261029/test-first-runtime-source.json",
    "evidence/B05/entries-20261029/test-runtime-source.json",
    "evidence/B05/entries-20261029/row-runtime-source.json",
    "evidence/B05/entries-20261029/stopped-cancel-runtime-source.json",
    "evidence/B05/entries-20261029/test-runtime-final.json",
    "evidence/B05/entries-20261029/ui-runtime-source.json",
    "evidence/B05/entries-20261029/ui-preserve-final.json",
    "evidence/B05/entries-20261029/acceptance-summary.json",
    "evidence/B05/header-20261029/source-manifest.json",
    "evidence/B05/header-20261029/intermediate-suite-source.json",
    "evidence/B05/header-20261029/ui-preserve-final.json",
    "evidence/B05/header-20261029/test-runtime-source.json",
    "evidence/B05/header-20261029/ui-runtime-source.json",
    "evidence/B05/header-20261029/ui-preserve.json",
    "evidence/B05/header-20261029/acceptance-summary.json",
    "evidence/B05/closeout-20261029/source-manifest.json",
    "evidence/B05/closeout-20261029/intermediate-suite-source.json",
    "evidence/B05/closeout-20261029/test-runtime-source.json",
    "evidence/B05/closeout-20261029/ui-runtime-source.json",
    "evidence/B05/closeout-20261029/ui-preserve-final.json",
    "evidence/B05/closeout-20261029/http-race.json",
    "evidence/B05/closeout-20261029/acceptance-summary.json",
    "evidence/B05/explicit-details-20261029/source-manifest.json",
    "evidence/B05/explicit-details-20261029/test-runtime-source.json",
    "evidence/B05/explicit-details-20261029/ui-runtime-source.json",
    "evidence/B05/explicit-details-20261029/ui-preserve.json",
    "evidence/B05/explicit-details-20261029/acceptance-summary.json",
    "evidence/维护/2026-10-28-缓存清理结果.json",
    "evidence/发布/2026-10-28-c048268-remote.json",
    "evidence/发布/2026-10-28-c048268-ci.json",
    "evidence/发布/2026-10-28-9684f38-remote.json",
    "evidence/发布/2026-10-28-9684f38-ci.json",
    "evidence/发布/2026-10-28-83aaf4e-remote.json",
    'evidence/B08/recovery-20261028/baseline.json',
    'evidence/B08/recovery-20261028/source-manifest.json',
    'evidence/B08/recovery-20261028/runtime-source.json',
    'evidence/B08/recovery-20261028/web-source.json',
    'evidence/B08/recovery-20261028/transaction-source.json',
    'evidence/B08/recovery-20261028/http-setup-before.json',
    'evidence/B08/recovery-20261028/http-setup.json',
    'evidence/B08/recovery-20261028/http-i05-before.json',
    'evidence/B08/recovery-20261028/http-i05.json',
    'evidence/B08/recovery-20261028/i06-controlled-before.json',
    'evidence/B08/recovery-20261028/i06-controlled.json',
    'evidence/B08/recovery-20261028/acceptance-summary.json',
    "evidence/发布/2026-10-28-698a780-remote.json",
    "evidence/B08/distinct-concurrency-20261028/http-setup-before.json",
    "evidence/B08/distinct-concurrency-20261028/http-setup.json",
    "evidence/B08/distinct-concurrency-20261028/http-i03-before.json",
    "evidence/B08/distinct-concurrency-20261028/http-i03.json",
    "evidence/B08/distinct-concurrency-20261028/http-i04-before.json",
    "evidence/B08/distinct-concurrency-20261028/http-i04.json",
    "evidence/B08/distinct-concurrency-20261028/http-retention-final.json",
    "evidence/B08/distinct-concurrency-20261028/http-summary.json",
    "evidence/B08/distinct-concurrency-20261028/server-prerequisite.json",
    "evidence/B08/distinct-concurrency-20261028/baseline.json",
    "evidence/B08/distinct-concurrency-20261028/source-manifest.json",
    "evidence/B08/distinct-concurrency-20261028/web-source.json",
    "evidence/B08/distinct-concurrency-20261028/runtime-source.json",
    "evidence/发布/2026-10-28-00cfbfc-remote.json",
    "evidence/B08/history-paths-20261028/http-summary.json",
    "evidence/B08/history-paths-20261028/http-fixture.json",
    "evidence/B08/history-paths-20261028/http-preflight.json",
    "evidence/B08/history-paths-20261028/http-acceptance.json",
    "evidence/B08/history-paths-20261028/http-remaining.json",
    "evidence/B08/history-paths-20261028/http-finish.json",
    "evidence/B08/history-paths-20261028/http-empty-times.json",
    "evidence/B08/history-paths-20261028/http-retention-after-resource.json",
    "evidence/B08/history-paths-20261028/http-retention-final.json",
    "evidence/B08/history-paths-20261028/acceptance-summary.json",
    "evidence/B08/history-paths-20261028/baseline.json",
    "evidence/B08/history-paths-20261028/source-manifest.json",
    "evidence/B08/history-paths-20261028/first-source.json",
    "evidence/B08/history-paths-20261028/first-runtime-source.json",
    "evidence/B08/history-paths-20261028/reparent-first-source.json",
    "evidence/B08/history-paths-20261028/reparent-first-runtime.json",
    "evidence/B08/history-paths-20261028/fixed-source.json",
    "evidence/B08/history-paths-20261028/fixed-runtime-source.json",
    "evidence/B08/history-paths-20261028/draft-fixed-source.json",
    "evidence/B08/history-paths-20261028/draft-fixed-runtime.json",
    "evidence/B08/history-paths-20261028/cancelled-only-source.json",
    "evidence/B08/history-paths-20261028/cancelled-only-runtime.json",
    "evidence/B08/history-paths-20261028/web-source.json",
    "evidence/B08/history-paths-20261028/built-source.json",
    "evidence/B08/history-paths-20261028/source-retention-summary.json",
    "evidence/发布/2026-10-28-d90f568-remote.json",
    "evidence/B08/metrics-20261028/acceptance-summary.json",
    "evidence/B08/metrics-20261028/baseline.json",
    "evidence/B08/metrics-20261028/source-manifest.json",
    "evidence/B08/metrics-20261028/runtime-source.json",
    "evidence/B08/metrics-20261028/runtime-final-source.json",
    "evidence/B08/metrics-20261028/web-final-source.json",
    "evidence/B08/metrics-20261028/built-source.json",
    "evidence/B08/metrics-20261028/config-ui.json",
    "evidence/B08/metrics-20261028/config-http.json",
    "evidence/B08/metrics-20261028/ui-retention-summary.json",
    "evidence/发布/2026-10-28-d4d73f0-remote.json",
    "evidence/B08/followup-20261028/acceptance-summary.json",
    "evidence/B08/followup-20261028/source-manifest.json",
    "evidence/B08/followup-20261028/runtime-final-source.json",
    "evidence/B08/followup-20261028/web-final-source.json",
    "evidence/B08/followup-20261028/built-source.json",
    "evidence/B08/followup-20261028/http-results.json",
    "evidence/B08/followup-20261028/ui-retention-summary.json",
    "evidence/B08/implementation/pause-code-ci.json",
    "evidence/发布/B08-2026-10-27-519759e-remote.json",
    "evidence/B08/implementation/acceptance-summary.json", "evidence/B08/implementation/source-manifest.json",
    "evidence/B08/implementation/business-tests-source-manifest.json", "evidence/B08/implementation/source-runtime.json",
    "evidence/B08/implementation/web-source.json", "evidence/B08/implementation/retention-summary.json",
    "evidence/B08/implementation/restore-check.json", "evidence/B08/implementation/closeout-check.json",
    "evidence/发布/B14-2026-10-27-remote.json",
    "evidence/B14/closeout-check.json", "evidence/B14/restore-check.json", "evidence/B14/source-manifest.json",
    "evidence/B14/web-source.json", "evidence/B08/native-fact/summary.json",
    "evidence/R07/time-config-source-manifest.json",
    "evidence/发布/B04-time-metrics-2026-10-27-remote.json",
    "evidence/B04/time-metrics/closeout-check.json", "evidence/B04/time-metrics/source-manifest.json",
    "evidence/B04/input-ui/closeout-check.json", "evidence/B04/input-ui/source-manifest.json",
    "evidence/R00/document-check.json", "evidence/R02/arithmetic-check.json",
    "evidence/R06/document-check.json", "evidence/R07/document-check.json",
    "evidence/R07/scope-review.json", "evidence/R07/source-manifest.json",
    "evidence/B01/checkout-final.json", "evidence/B01/closeout-check.json",
    "evidence/B10/pause-save-check.json", "evidence/B10/acceptance-web-http.json",
    "evidence/B10/acceptance-web-source.json", "evidence/B10/acceptance-bench-source.json",
    "evidence/R07/approval-source-check.json", "evidence/B19/closeout-check.json",
    "evidence/B19/source-manifest.json", "evidence/B19/document-check.json",
    "evidence/B19/execution-gate/closeout-check.json", "evidence/B19/execution-gate/source-manifest.json",
    "evidence/B19/execution-gate/source-final.json", "evidence/B19/execution-gate/document-check.json",
    "evidence/B19/entry-history/closeout-check.json", "evidence/B19/entry-history/source-manifest.json",
    "evidence/B19/entry-history/source-fixed.json", "evidence/B19/entry-history/document-check.json",
    "evidence/B19/http/acceptance-summary.json", "evidence/B19/http/source-web.json",
    "evidence/B19/http/document-check.json",
    "evidence/B19/approved-changes/closeout-check.json", "evidence/B19/approved-changes/source-manifest.json",
    "evidence/B19/approved-changes/source-final.json", "evidence/B19/approved-changes/document-check.json",
    "evidence/发布/B19-2026-10-27-remote.json",
    "evidence/B04/source-manifest.json", "evidence/B04/source-final.json", "evidence/B04/closeout-check.json",
    "evidence/B19/chinese-flow/source-manifest.json", "evidence/B19/chinese-flow/source-web.json",
    "evidence/B19/chinese-flow/menu-regression.json", "evidence/B19/chinese-flow/acceptance-summary.json",
    "evidence/B19/chinese-flow/readback-verified.json", "evidence/B19/chinese-flow/document-check.json",
    "evidence/B04/precision-loss/source-delivery-manifest.json",
    "evidence/B04/precision-loss/source-delivery-runtime.json",
    "evidence/B04/precision-loss/acceptance-summary.json",
    "evidence/发布/B04-B19-ui-2026-10-27-remote.json",
]
for name in safe_json:
    path = ROOT / name
    if path.exists():
        data = json.loads(portable(path.read_text()))
        add(name, json.dumps(data, ensure_ascii=False, indent=2) + "\n", name, "allowlisted metadata; personal paths removed")

http_name = "evidence/B02/acceptance-http-summary.json"
http = json.loads((ROOT / http_name).read_text())
keys = ("initial_requests", "revoked_same_token_requests", "all_passed", "business_state_unchanged", "patch_sha256", "verified_after_all_requests")
assert http["initial_requests"] == 12 and http["revoked_same_token_requests"] == 4 and http["all_passed"]
safe_http = {key: http[key] for key in keys}
safe_http["publication_note"] = "Only assertions/counts retained; runtime business_state and raw responses remain local."
add(http_name, json.dumps(safe_http, ensure_ascii=False, indent=2) + "\n", http_name, "runtime business_state removed")

# Test receipts contain counts and final status only. Full stdout remains local.
test_receipts = []
old_patch = json.loads((ROOT / ".development/checks/b02-b10-source-manifest.json").read_text())["patch_sha256"]
approval_patch = json.loads((ROOT / "evidence/B19/source-manifest.json").read_text())["patch_sha256"]
execution_patch = json.loads((ROOT / "evidence/B19/execution-gate/source-manifest.json").read_text())["patch_sha256"]
history_patch = json.loads((ROOT / "evidence/B19/entry-history/source-manifest.json").read_text())["patch_sha256"]
changes_patch = json.loads((ROOT / "evidence/B19/approved-changes/source-manifest.json").read_text())["patch_sha256"]
b04_patch = json.loads((ROOT / "evidence/B04/source-manifest.json").read_text())["patch_sha256"]
groups = [
    ("B05 entries final empty-create fixture only", "2026-10-29", json.loads((ROOT / "evidence/B05/entries-20261029/final-fixture-source.json").read_text())["patch_sha256"], [("evidence/B05/entries-20261029/final-fixture.log",1)]),
    ("B05 entries corrected viewed-version fixture method only", "2026-10-29", entries_manifest["patch_sha256"], [("evidence/B05/entries-20261029/final-history-only.log",1)]),
    ("B05 final overdue warning policy affected date methods only", "2026-10-29", header_manifest["patch_sha256"], [("evidence/B05/header-20261029/overdue-fixed.log",2)]),
    ("B05 native header numbering and prerequisites with two affected original cases", "2026-10-29", json.loads((ROOT / "evidence/B05/header-20261029/intermediate-suite-source.json").read_text())["patch_sha256"], [("evidence/B05/header-20261029/green-first.log",10)]),
    ("B05 Chinese snapshot display fix affected method only", "2026-10-29", closeout_manifest["patch_sha256"], [("evidence/B05/closeout-20261029/unicode-fixed.log",1)]),
    ("B05 timer finish/manual close bounded suite and affected original cases", "2026-10-29", json.loads((ROOT / "evidence/B05/closeout-20261029/intermediate-suite-source.json").read_text())["patch_sha256"], [("evidence/B05/closeout-20261029/final-tests.log",12)]),
    ("B05 explicit details reviewed bounded suite and affected original cases", "2026-10-29", details_manifest["patch_sha256"], [("evidence/B05/explicit-details-20261029/final-with-revocation.log",11)]),
    ("B08 history paths corrected draft fixture", "2026-10-28", json.loads((ROOT / "evidence/B08/history-paths-20261028/draft-fixed-source.json").read_text())["patch_sha256"], [("evidence/B08/history-paths-20261028/draft-fixed.log",1)]),
    ("B08 history paths cancelled-only reference; controlled native cancellation fixture", "2026-10-28", history_paths_manifest["patch_sha256"], [("evidence/B08/history-paths-20261028/cancelled-only.log",1)]),
    ("B08 metrics fixture fix and additions", "2026-10-28", json.loads((ROOT / "evidence/B08/metrics-20261028/runtime-source.json").read_text())["patch_sha256"], [("evidence/B08/metrics-20261028/server-fixed-second.log",4)]),
    ("B08 metrics affected old regression", "2026-10-28", json.loads((ROOT / "evidence/B08/metrics-20261028/runtime-source.json").read_text())["patch_sha256"], [("evidence/B08/metrics-20261028/affected-regression.log",5)]),
    ("B08 metrics child guard and source/history; intermediate whole-patch digest not captured", "2026-10-28", None, [("evidence/B08/metrics-20261028/child-fixed.log",3), ("evidence/B08/metrics-20261028/child-entry-boundaries.log",1), ("evidence/B08/metrics-20261028/settings-history.log",1)]),
    ("B08 followup fixed permissions", "2026-10-28", json.loads((ROOT / "evidence/B08/followup-20261028/runtime-fixed-source.json").read_text())["patch_sha256"], [("evidence/B08/followup-20261028/permissions-fixed.log",4)]),
    ("B08 followup history regression; intermediate whole-patch digest not captured; product file matches final", "2026-10-28", None, [("evidence/B08/followup-20261028/permissions-history-regression.log",2)]),
    ("B08 followup rules", "2026-10-28", followup_manifest["patch_sha256"], [("evidence/B08/followup-20261028/rules-isolated.log",1)]),
    ("B08 confirmation and affected original cases", "2026-10-27", json.loads((ROOT / "evidence/B08/implementation/business-tests-source-manifest.json").read_text())["patch_sha256"], [("evidence/B08/implementation/final-confirmation-tests.log", 14), ("evidence/B08/implementation/affected-regression.log", 3)]),
    ("B08 added native derivation rollback case; product logic unchanged", "2026-10-27", json.loads((ROOT / ".development/checks/b08-source-manifest.json").read_text())["patch_sha256"], [("evidence/B08/implementation/derivation-rollback.log", 1)]),
    ("B14 configuration and boundaries", "2026-10-27", json.loads((ROOT / ".development/checks/b14-source-manifest.json").read_text())["patch_sha256"], [("evidence/B14/review-fixed-tests.log", 15)]),
    ("B02/B10 historical", "2026-10-26", old_patch, [("evidence/B02/acceptance-tests.log", 10), ("evidence/B10/acceptance-consumption.log", 2), ("evidence/B10/acceptance-transfer.log", 3)]),
    ("B19 approval core historical", "2026-10-27", approval_patch, [("evidence/B19/final-results.log", 17), ("evidence/B19/unit-regression.log", 2)]),
    ("B19 execution gate historical", "2026-10-27", execution_patch, [("evidence/B19/execution-gate/job-fixed-first.log", 10), ("evidence/B19/execution-gate/stock-fixed-first.log", 11), ("evidence/B19/execution-gate/units-work-order.log", 2), ("evidence/B19/execution-gate/units-stock-entry.log", 3)]),
    ("B19 batch-save and history previous batch", "2026-10-27", history_patch, [("evidence/B19/entry-history/fixed-results.log", 14), ("evidence/B19/entry-history/approval-regression.log", 1)]),
    ("B19 approved changes historical", "2026-10-27", changes_patch, [("evidence/B19/approved-changes/final-results.log", 18), ("evidence/B19/approved-changes/approval-regression.log", 17), ("evidence/B19/approved-changes/stock-regression.log", 3), ("evidence/B19/approved-changes/status-regression.log", 4)]),
    ("B04 final demand", "2026-10-27", b04_patch, [("evidence/B04/fixed-results.log", 4), ("evidence/B04/unit-regression.log", 2)]),
    ("B04 precision and material loss", "2026-10-27", json.loads((ROOT / ".development/checks/b04-precision-delivery-source-manifest.json").read_text())["patch_sha256"], [("evidence/B04/precision-loss/delivery-tests.log", 8)]),
    ("B04 input/save and Chinese BOM PC", "2026-10-27", json.loads((ROOT / ".development/checks/b04-input-source-manifest.json").read_text())["patch_sha256"], [("evidence/B04/input-ui/final-tests.log", 4)]),
    ("B04 time and metrics calculation layer", "2026-10-27", json.loads((ROOT / ".development/checks/b04-time-source-manifest.json").read_text())["patch_sha256"], [("evidence/B04/time-metrics/final-tests.log", 12)]),
]
for group, date, patch_sha, logs in groups:
  for name, count in logs:
    raw = (ROOT / name).read_text()
    match = re.search(r"Ran (\d+) tests? in ([0-9.]+)s\s+OK", raw)
    assert match and int(match[1]) == count
    test_receipts.append({"local_log": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                          "tests": count, "seconds": match[2], "result": "OK", "executed_on": date,
                          "group": group, "source_patch_sha256": patch_sha,
                          **({"product_job_card_sha256": followup_manifest["files"]["erpnext/manufacturing/doctype/job_card/job_card.py"]} if group.startswith("B08 followup") else {}),
                          **({"product_job_card_sha256": metrics_manifest["files"]["erpnext/manufacturing/doctype/job_card/job_card.py"]} if group.startswith("B08 metrics") else {})})
# Preserve the real FAILED batch; one fixture timestamp error was corrected separately.
partial_log = ROOT / "evidence/B05/entries-20261029/final-affected.log"
partial_text = partial_log.read_text()
assert "Ran 10 tests in 103.397s" in partial_text and "FAILED (errors=1)" in partial_text
assert len(re.findall(r"^(?:test_.* [.][.][.] )?ok$", partial_text, re.M)) == 9
test_receipts.insert(2, {"local_log": "evidence/B05/entries-20261029/final-affected.log",
    "sha256": hashlib.sha256(partial_log.read_bytes()).hexdigest(), "tests": 10,
    "passed_methods": 9, "errors": 1, "seconds": "103.397", "result": "FAILED",
    "executed_on": "2026-10-29", "group": "B05 entries final affected batch: nine pass, one fixture stale-version error",
    "source_patch_sha256": json.loads((ROOT / "evidence/B05/entries-20261029/final-backend-source.json").read_text())["patch_sha256"],
    "resolved_fixture_only_by": "evidence/B05/entries-20261029/final-history-only.log",
    "scope": "Nine passing methods reused unchanged; only the fixture reload was corrected and rerun. Not a single final full-suite pass."})
previous_receipts = json.loads((ROOT / ".development/private/b06-tasks-20261029/base-receipts.json").read_text())["tests"]
assert test_receipts == previous_receipts, "Historical 42 receipts must remain exact"
for batch in json.loads((ROOT / "evidence/B06/tasks-20261029/test-batches.json").read_text())["batches"]:
    test_receipts.append({**batch, "executed_on": "2026-10-29", "group": "B06 bounded task adjustments: " + Path(batch["local_log"]).stem})
previous_b07_receipts = json.loads((ROOT / ".development/private/b07-materials-20261029/base-receipts.json").read_text())["tests"]
assert test_receipts == previous_b07_receipts, "Historical 50 receipts must remain exact"
for batch in json.loads((ROOT / "evidence/B07/materials-20261029/test-batches.json").read_text())["batches"]:
    test_receipts.append({**batch, "executed_on": "2026-10-29", "group": "B07 bounded material boundaries: " + Path(batch["local_log"]).stem})
navigation_base = json.loads((ROOT / ".development/private/b08-navigation-20261030/base-receipts.json").read_text())["tests"]
assert test_receipts == navigation_base, "Historical 59 receipts must remain exact"
for batch in json.loads((ROOT / "evidence/B08/navigation-20261030/test-batches.json").read_text())["batches"]:
    test_receipts.append({**batch, "executed_on": "2026-10-30", "group": "B08 task follow-up navigation: " + Path(batch["local_log"]).stem})
quality_base = json.loads((ROOT / ".development/private/b08-quality-20261030/base-receipts.json").read_text())["tests"]
assert test_receipts == quality_base, "Historical 64 receipts must remain exact"
for batch in json.loads((ROOT / "evidence/B08/quality-20261030/test-batches.json").read_text())["batches"]:
    test_receipts.append({**batch, "executed_on": "2026-10-30", "group": "B08 native quality/images: " + Path(batch["local_log"]).stem})
add("publication/test-receipts.json", json.dumps({"scope": "Separate executed batches; FAILED red/intermediate batches preserved. Exact source patch where captured, explicit null otherwise. No cumulative full-suite result; publication does not rerun tests", "tests": test_receipts, "http_B02_historical": safe_http, "current_patch_sha256": manifest["patch_sha256"]}, ensure_ascii=False, indent=2) + "\n")

index = []
for path in sorted((ROOT / "evidence").rglob("*")):
    if path.is_file() and path.suffix != ".pyc":
        relative = path.relative_to(ROOT).as_posix()
        index.append({"path": relative, "original_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "published": relative in published, "reason": "public copy" if relative in published else "local raw execution evidence; not uploaded"})
add("publication/evidence-index.json", json.dumps(index, ensure_ascii=False, indent=2) + "\n")
add("publication/export-transformations.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")

source_map = {}
for name in changes:
    existing = subprocess.run(["git", "cat-file", "-e", BASE + ":" + name], cwd=REPO, capture_output=True).returncode == 0
    original = subprocess.check_output(["git", "show", BASE + ":" + name], cwd=REPO) if existing else None
    source_map[name] = {"base_sha256": hashlib.sha256(original).hexdigest() if original is not None else None, "modified_sha256": manifest["files"][name]}
add("source/source-lock.json", json.dumps({"upstream": "https://github.com/frappe/erpnext.git", "commit": BASE, "version": "15.124.1", "frappe_version": "15.124.0", "frappe_commit": "f1cf50cf9bbc641bb015adb7008bf2ea1c8483ab", "patch_sha256": manifest["patch_sha256"], "files": source_map}, indent=2) + "\n")

# Public copies explain intentionally unexported artifacts instead of leaving silent broken links.
for name, data in list(published.items()):
    if not name.endswith(".md"):
        continue
    text = data.decode()
    def link(match):
        label, target = match[1], match[2]
        if "://" in target or target.startswith("#"):
            return match[0]
        bare = target.split("#")[0].strip("<>")
        candidate = (OUT / Path(name).parent / bare).resolve()
        try:
            destination = candidate.relative_to(OUT.resolve()).as_posix()
        except ValueError:
            return label + "（本地资料，不上传）"
        if destination in published or any(x.startswith(destination.rstrip("/") + "/") for x in published):
            return match[0]
        return label + "（仅本地保留；见 publication/evidence-index.json）"
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    if name.startswith("evidence/"):
        header = "> 公开归档副本（" + datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat() + "）：保留结论、方法与限制；个人路径/运行编号已移除。原始运行单据、响应、截图和日志不上传，原件索引见 `publication/evidence-index.json`。本页历史结果不是发布日重测。"
        previous = OUT / name
        if previous.exists():
            parts = previous.read_text().split("\n\n", 1)
            if len(parts) == 2 and parts[0].startswith("> 公开归档副本（") and parts[1] == text:
                header = parts[0]
        text = header + "\n\n" + text
    published[name] = text.encode()

for name, data in published.items():
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
(ROOT / ".publication/exported-paths.json").write_text(json.dumps(sorted(published), ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"exported_files": len(published), "bytes": sum(map(len, published.values())), "source_files_exact": len(changes), "original_evidence_indexed": len(index)}, ensure_ascii=False))
