#! /bin/bash
set -e

DATABASE_FILE="/secrets/mysql/database.txt"
MYSQL_DATABASE=$(cat "$DATABASE_FILE")
TIMESTAMP="$(date -u +%Y%m%d%H%M)UTC"
DUMP_FILE="/mysql_backup_dumps/${MYSQL_DATABASE}_${TIMESTAMP}_periodical_dump.sql"
/mysql_backup_service/create_backup.sh ${DUMP_FILE}
