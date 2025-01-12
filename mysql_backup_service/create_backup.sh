#!/usr/bin/env bash

DATABASE_FILE="/secrets/mysql/database.txt"
USER_PASSWORD_FILE="/secrets/mysql/root_password.txt"
MYSQL_HOST_FILE="/mysql_backup_service/mysql_host.txt"

MYSQL_DATABASE=$(cat "${DATABASE_FILE}")
MYSQL_USER="root"
MYSQL_PASSWORD=$(cat "${USER_PASSWORD_FILE}")
MYSQL_HOST=$(cat "${MYSQL_HOST_FILE}")
TIMESTAMP=$(date +%Y%m%d_%H%M)

# Check if a filename is provided
if [ -z "$1" ]; then
  echo "Error: No dump file specified."
  echo "Usage: $0 <dump_file_path>"
  exit 1
fi

# Dump file path from the first argument
DUMP_FILE="$1"

echo "Creating a new dump at ${DUMP_FILE}..."

mysqldump \
  --host=${MYSQL_HOST} \
  --user="${MYSQL_USER}" \
  --password="${MYSQL_PASSWORD}" \
  "${MYSQL_DATABASE}" \
  > "${DUMP_FILE}"

if [ $? -eq 0 ]; then
  chmod a+rw ${DUMP_FILE}
  echo "Backup successful: ${DUMP_FILE}"
else
  echo "Backup failed."
  exit 1
fi
