"""Real HTTP checks for this fixture only; no repeated confirmation or business posting."""
import hashlib
import io
import json
import os
import sys
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

os.umask(0o077)
p = Path(".development/private/b08-quality-20261030")
a = json.loads((p / "access.json").read_text())
assert a["site"] == "xgd-b08-http.localhost" and a["base_url"] == "http://127.0.0.1:18090"
actor = a["actors"]["quality"]
headers = {"Authorization": "token " + actor["api_key"] + ":" + actor["api_secret"],
    "Host": a["site"], "Content-Type": "application/json"}
mode = sys.argv[1]
assert mode in ("before-revoke", "after-revoke")
target = p / (mode + "-http.json")
assert not target.exists(), "Keep previous results; do not rerun unchanged HTTP writes"
cases = []


def resource(dt, name=None):
    return "/api/resource/" + quote(dt, safe="") + ("/" + quote(name, safe="") if name else "")


def call(label, path, expected, args=None, verb="GET", binary=False):
    request = Request(a["base_url"] + path, data=json.dumps(args).encode() if args is not None else None,
        headers=headers, method=verb)
    try:
        with urlopen(request, timeout=30) as response:
            status, body = response.status, response.read()
    except HTTPError as error:
        status, body = error.code, error.read()
    case = {"case": label, "status": status, "expected_status": expected}
    cases.append(case)
    target.write_text(json.dumps({"mode": mode, "cases": cases}, ensure_ascii=False, indent=2))
    assert status == expected, (label, status, expected)
    if binary:
        return body
    data = json.loads(body)
    return data.get("data", data.get("message"))


if mode == "before-revoke":
    call("foreign-parent-read-denied", resource("Job Card", a["foreign_report"]), 403)
    inspection = call("native-inspection-readable", resource("Quality Inspection", a["inspection"]), 200)
    assert inspection["docstatus"] == 1 and inspection["status"] == "Rejected"
    image = call("native-image-metadata-readable", resource("File", a["image_file"]), 200)
    assert image["is_private"] == 1
    for label, path in [("private-url-download", a["file_url"]), ("private-fid-download", a["file_url"] + "?fid=" + quote(a["image_file"]))]:
        body = call(label, path, 200, binary=True)
        assert hashlib.sha256(body).hexdigest() == a["image_sha256"]
    archive = call("authorized-native-zip", "/api/method/frappe.core.api.file.zip_files", 200,
        {"files": json.dumps([a["image_file"]])}, "POST", binary=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        assert zf.namelist() == [image["file_name"]]
        assert hashlib.sha256(zf.read(image["file_name"])).hexdigest() == a["image_sha256"]
    call("locked-image-delete-denied", resource("File", a["image_file"]), 403, verb="DELETE")
    call("locked-image-publication-denied", resource("File", a["image_file"]), 403, {"is_private": 0}, "PUT")
    payload = {k: inspection[k] for k in ["inspection_type", "reference_type", "reference_name", "company", "item_code", "sample_size", "inspected_by", "report_date", "manual_inspection", "status"]}
    call("foreign-inspection-create-denied", resource("Quality Inspection"), 403,
        {**payload, "reference_name": a["foreign_report"]}, "POST")
    call("wrong-company-inspection-denied", resource("Quality Inspection"), 403,
        {**payload, "company": a["other_company"]}, "POST")
else:
    call("revoked-parent-read-denied", resource("Job Card", a["report"]), 403)
    call("revoked-inspection-read-denied", resource("Quality Inspection", a["inspection"]), 403)
    call("revoked-image-metadata-denied", resource("File", a["image_file"]), 403)
    call("revoked-private-url-denied", a["file_url"], 403, binary=True)
    call("revoked-private-fid-denied", a["file_url"] + "?fid=" + quote(a["image_file"]), 403, binary=True)
    call("revoked-zip-denied", "/api/method/frappe.core.api.file.zip_files", 403,
        {"files": json.dumps([a["image_file"]])}, "POST")
    for dt, name in [("Quality Inspection", a["inspection"]), ("File", a["image_file"])]:
        rows = call("revoked-" + dt + "-list-empty", "/api/method/frappe.client.get_list", 200,
            {"doctype": dt, "filters": {"name": name}, "fields": ["name"]}, "POST")
        assert rows == []
result = {"mode": mode, "cases": cases, "passed": True,
    "scope": "Real HTTP only; native PC creation/upload/submit/reopen recorded separately; not full card or concurrency acceptance"}
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"mode": mode, "passed": True, "cases": len(cases), "raw_credentials_or_records_printed": False}))
