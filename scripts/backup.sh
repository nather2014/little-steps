#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
umask 077
mkdir -p backups
backup_path="backups/little-steps-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db pg_dump -U little_steps -d little_steps -Fc > "$backup_path"
echo "Backup saved: $backup_path"
