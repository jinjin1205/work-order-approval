"""Check the publication allowlist without printing credential values."""
import ast
import base64
import hashlib
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).resolve().parent.parent
public = root / ".publication/work-order-approval"
allowed = set(json.loads((root / ".publication/exported-paths.json").read_text()))
allowed.update({"README.md", "THIRD_PARTY_NOTICES.md", ".gitignore", "tools/prepare_source.py"})
allowed.update({"publication/files.sha256.json", "publication/publish-check.json", "publication/remote-verification.json"})
files = {p.relative_to(public).as_posix(): p for p in public.rglob("*") if p.is_file() and ".git" not in p.relative_to(public).parts}
unexpected = sorted(set(files) - allowed)
assert not unexpected, "Unexpected files: " + str(unexpected)

secrets = set()
credential_sources = [root / ".development/private/b05-entries-20261029/access.json", root / ".development/private/b05-header-20261029/access.json", root / ".development/private/b05-closeout-20261029/access.json", root / ".development/private/b05-details-20261029/access.json", root / ".development/private/b08-metrics/config-access.json", root / ".development/private/b08-followup/http-fixture.json",root / ".development/private/b08-http/fixture.json", root / ".development/private/b14-ui/access.json", root / ".development/private/b04-bom-ui/access.json", root / ".development/.env", root / ".development/private/b02-http.json",
                      root / ".development/private/b19-http/fixture.json",
                      root / ".development/private/b19-http/ui-access.json",
                      root / ".evaluation/r05-erpnext/.env", root / ".evaluation/r05-erpnext/access-secrets.json"]
credential_sources += [root / ".development/private/b08-navigation-20261030/access.json", root / ".development/private/b06-tasks-20261029/access.json", root / ".development/private/b06-retention-20261029/access.json", root / ".development/private/b07-materials-20261029/access.json"]
credential_sources += [root / ".development/private/b08-quality-20261030/access.json", root / ".development/private/b08-quality-20261030/retired-access.json"]
credential_sources += sorted((root / ".development/private/b08-history-paths").glob("*.json"))
credential_sources += sorted((root / ".development/private/b08-distinct-concurrency").glob("*.json"))
credential_sources += sorted((root / ".development/private/b08-recovery").glob("*.json"))
def collect(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if re.search(r"password|secret|token|api_key", key, re.I) and isinstance(child, str) and len(child) >= 8:
                secrets.add(child)
            else:
                collect(child)
    elif isinstance(value, list):
        for child in value:
            collect(child)
for path in credential_sources:
    if not path.exists():
        continue
    if path.suffix == ".json":
        collect(json.loads(path.read_text()))
    else:
        for line in path.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip("\"'")
            if re.search(r"password|secret|token|key", key, re.I) and len(value) >= 8:
                secrets.add(value)
assert secrets, "No local credential values were available for the exclusion check"
needles = {variant.encode() for value in secrets for variant in (value, quote(value, safe=""), base64.b64encode(value.encode()).decode())}
patterns = [rb"gh[pousr]_[A-Za-z0-9]{25,}", rb"github_pat_[A-Za-z0-9_]{30,}", rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"]
secret_hits = []
raw_data_hits = []
for name, path in files.items():
    data = path.read_bytes()
    if any(value in data for value in needles) or any(re.search(pattern, data) for pattern in patterns):
        secret_hits.append(name)
    assert (b"/" + b"Users/") not in data, "Personal path: " + name
    assert not any(part in {"private", "sites", "logs", "volumes", "__pycache__"} for part in Path(name).parts), name
    assert path.suffix not in {".log", ".jsonl", ".png", ".jpg", ".sqlite", ".db", ".pyc"}, name
    if path.suffix == ".json":
        obj = json.loads(data)
        def has_records(obj):
            if isinstance(obj, dict):
                return any(k in {"business_state", "api_secret", "api_key", "db_password", "database_name"} or has_records(v) for k, v in obj.items())
            if isinstance(obj, list):
                return any(has_records(v) for v in obj)
            return False
        if has_records(obj):
            raw_data_hits.append(name)
    if path.suffix == ".py":
        ast.parse(data, filename=name)
assert not secret_hits, "Potential credentials in paths: " + str(secret_hits)
assert not raw_data_hits, "Runtime-data JSON in paths: " + str(raw_data_hits)
lock = json.loads(files["source/source-lock.json"].read_text())
for name, entry in lock["files"].items():
    assert hashlib.sha256(files["source/erpnext/" + name].read_bytes()).hexdigest() == entry["modified_sha256"]
report = {"date": datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(), "scope": "Explicit public snapshot only; application test receipts retain their execution batch and source hash; publication does not rerun application tests",
          "allowlist_passed": True, "known_credential_literal_matches": 0,
          "credential_pattern_matches": 0, "raw_runtime_json_matches": 0,
          "personal_host_paths": 0, "python_sources_parse": True, "modified_source_files_exact": len(lock["files"]),
          "business_test_data_in_export": "No runtime documents/responses/databases; fixture definitions and expected results retained",
          "limitation": "This is a bounded publication check, not a universal secret or license audit"}
(public / "publication/publish-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
files["publication/publish-check.json"] = public / "publication/publish-check.json"
hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sorted(files.items()) if name != "publication/files.sha256.json"}
(public / "publication/files.sha256.json").write_text(json.dumps({"algorithm": "sha256", "scope": "All published files except this self-referential manifest", "files": hashes}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"publication_check": "passed", "published_files": len(hashes) + 1, "code_files_exact": len(lock["files"]), "secret_or_runtime_data_matches": 0}, ensure_ascii=False))
