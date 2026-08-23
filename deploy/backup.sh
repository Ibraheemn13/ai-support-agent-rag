#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${ENV_FILE:-${project_root}/deploy/vps.env}"
backup_dir="${BACKUP_DIR:-${project_root}/backups}"
retention_days="${BACKUP_RETENTION_DAYS:-7}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ ! -f "${env_file}" ]]; then
  echo "Missing environment file: ${env_file}" >&2
  exit 1
fi

read_env_value() {
  local key="$1"
  awk -F= -v key="${key}" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' \
    "${env_file}"
}

postgres_user="$(read_env_value POSTGRES_USER)"
postgres_db="$(read_env_value POSTGRES_DB)"
if [[ -z "${postgres_user}" || -z "${postgres_db}" ]]; then
  echo "POSTGRES_USER and POSTGRES_DB are required in ${env_file}" >&2
  exit 1
fi

umask 077
mkdir -p "${backup_dir}"

compose=(
  docker compose
  --env-file "${env_file}"
  --file "${project_root}/compose.vps.yaml"
)

database_backup="${backup_dir}/postgres-${timestamp}.dump"
uploads_backup="${backup_dir}/uploads-${timestamp}.tar.gz"

"${compose[@]}" exec -T db \
  pg_dump --username "${postgres_user}" --dbname "${postgres_db}" \
  --format custom > "${database_backup}"

docker run --rm \
  --volume supportmind_uploads:/data:ro \
  --volume "${backup_dir}:/backup" \
  alpine:3.22 \
  tar -C /data -czf "/backup/$(basename "${uploads_backup}")" .

sha256sum "${database_backup}" "${uploads_backup}" \
  > "${backup_dir}/checksums-${timestamp}.sha256"

find "${backup_dir}" -type f -mtime "+${retention_days}" -delete
echo "Backup completed: ${timestamp}"
