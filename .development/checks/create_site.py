import os
import subprocess
import sys
from pathlib import Path

site = sys.argv[1]
admin_keys = {"xgd-dev.localhost": "B01_DEV_ADMIN_PASSWORD", "xgd-test.localhost": "B01_TEST_ADMIN_PASSWORD"}
admin_key = admin_keys[site]
if Path("sites", site).exists():
    raise SystemExit("Refusing to overwrite existing site: " + site)
for key, value in {"db_host": "db", "redis_cache": "redis://redis-cache:6379", "redis_queue": "redis://redis-queue:6379", "redis_socketio": "redis://redis-queue:6379"}.items():
    subprocess.run(["bench", "set-config", "-g", key, value], check=True)
args = ["bench", "new-site", site, "--db-host", "db", "--db-root-username", "root", "--db-root-password", os.environ["B01_DB_PASSWORD"], "--admin-password", os.environ[admin_key], "--mariadb-user-host-login-scope", "%", "--install-app", "erpnext"]
result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
output = result.stdout
for key in set(admin_keys.values()) | {"B01_DB_PASSWORD"}:
    output = output.replace(os.environ[key], "[REDACTED]")
print(output)
raise SystemExit(result.returncode)
