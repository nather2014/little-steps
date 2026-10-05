#!/usr/bin/env bash
# Install a compiled release on Ubuntu. Run as root with APP_ORIGIN set.
set -euo pipefail
: "${APP_ORIGIN:?Set APP_ORIGIN to the public browser URL}"
if [ "$(id -u)" != 0 ]; then echo 'Run as root'; exit 1; fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
test -f backend/little-steps
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends postgresql nginx cron python3 ca-certificates tzdata
if ! id little-steps >/dev/null 2>&1; then
  useradd --system --home-dir /opt/little-steps --shell /usr/sbin/nologin little-steps
fi
install -d -m 755 /opt/little-steps
install -m 755 backend/little-steps /opt/little-steps/little-steps
cp -a web /opt/little-steps/
chown -R root:root /opt/little-steps
systemctl enable --now postgresql
python3 - <<'PY'
import os, pathlib, secrets, subprocess
p=pathlib.Path('/etc/little-steps.env')
if not p.exists():
 password=secrets.token_hex(32)
 def sql(text):
  return subprocess.run(['runuser','-u','postgres','--','psql','-v','ON_ERROR_STOP=1','-At'],input=text,text=True,capture_output=True,check=True).stdout.strip()
 if sql("SELECT 1 FROM pg_roles WHERE rolname='little_steps';"):
  raise SystemExit('Database role already exists; configure /etc/little-steps.env before continuing.')
 sql("CREATE ROLE little_steps LOGIN PASSWORD '"+password+"';")
 sql("CREATE DATABASE little_steps OWNER little_steps TEMPLATE template0 ENCODING 'UTF8';")
 origin=os.environ['APP_ORIGIN']
 p.write_text('DATABASE_URL=postgres://little_steps:'+password+'@127.0.0.1:5432/little_steps?sslmode=disable\nAPP_ORIGIN='+origin+'\nSECURE_COOKIES='+('true' if origin.startswith('https://') else 'false')+'\nLISTEN_ADDR=127.0.0.1:8090\nWEB_DIR=/opt/little-steps/web\n')
 p.chmod(0o600)
PY
cat > /etc/systemd/system/little-steps.service <<'UNIT'
[Unit]
Description=Little Steps Go API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
User=little-steps
Group=little-steps
WorkingDirectory=/opt/little-steps
EnvironmentFile=/etc/little-steps.env
ExecStart=/opt/little-steps/little-steps
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
MemoryMax=256M

[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/nginx/sites-available/little-steps <<'NGINX'
server {
    listen 80;
    server_name 51.77.117.66;
    client_max_body_size 16k;
    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 35s;
    }
}
NGINX
ln -sfn /etc/nginx/sites-available/little-steps /etc/nginx/sites-enabled/little-steps
nginx -t
systemctl daemon-reload
systemctl enable --now little-steps
systemctl restart little-steps
systemctl enable --now nginx
systemctl reload nginx
install -d -m 700 /var/backups/little-steps
cat > /usr/local/sbin/little-steps-backup <<'BACKUP'
#!/usr/bin/env bash
set -euo pipefail
umask 077
path="/var/backups/little-steps/little-steps-$(date -u +%Y%m%dT%H%M%SZ).dump"
runuser -u postgres -- pg_dump -d little_steps -Fc > "$path"
echo "Backup saved: $path"
BACKUP
chmod 700 /usr/local/sbin/little-steps-backup
cat > /etc/cron.d/little-steps-backup <<'CRON'
15 2 * * * root /usr/local/sbin/little-steps-backup >> /var/log/little-steps-backup.log 2>&1
CRON
chmod 644 /etc/cron.d/little-steps-backup
systemctl enable --now cron
echo "Installed Little Steps; browser origin: $APP_ORIGIN"
