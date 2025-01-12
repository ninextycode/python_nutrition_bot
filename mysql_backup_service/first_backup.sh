#! /bin/bash
set -e

DATABASE_FILE="/secrets/mysql/database.txt"
MYSQL_DATABASE=$(cat "$DATABASE_FILE")
if [[ "${NEED_BACKUP_ON_RESTART,,}" == "true" ]]; then
  TIMESTAMP="$(date -u +%Y%m%d%H%M)UTC"
  DUMP_FILE="/mysql_backup_dumps/${MYSQL_DATABASE}_${TIMESTAMP}_init_dump.sql"
  /mysql_backup_service/create_backup.sh ${DUMP_FILE}
else
  echo "Initial backup skipped"
fi