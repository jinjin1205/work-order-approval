"""Restore pinned upstream source plus the exact six published modifications."""
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
lock = json.loads((root / "source/source-lock.json").read_text())
destination = root / ".development/repos/erpnext"
if destination.exists():
    raise SystemExit("维护源码目录已存在；停止，不覆盖已有代码。")
destination.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(["git", "init", str(destination)], check=True)
subprocess.run(["git", "-C", str(destination), "remote", "add", "origin", lock["upstream"]], check=True)
subprocess.run(["git", "-C", str(destination), "fetch", "--depth=1", "origin", lock["commit"]], check=True)
subprocess.run(["git", "-C", str(destination), "checkout", "-b", "codex/xgd-maintenance", "FETCH_HEAD"], check=True)
actual = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
if actual != lock["commit"]:
    raise SystemExit("上游提交与锁定版本不一致，停止。")
for name, hashes in lock["files"].items():
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise SystemExit("源文件路径超出源码目录，停止。")
    base = (destination / name).read_bytes()
    modified = (root / "source/erpnext" / name).read_bytes()
    if hashlib.sha256(base).hexdigest() != hashes["base_sha256"]:
        raise SystemExit("上游文件哈希不一致：" + name)
    if hashlib.sha256(modified).hexdigest() != hashes["modified_sha256"]:
        raise SystemExit("公开修改文件哈希不一致：" + name)
for name in lock["files"]:
    (destination / name).write_bytes((root / "source/erpnext" / name).read_bytes())
print("完整维护源码已准备：固定上游提交 + 6个已验证修改文件；未启动服务。")
