#!/bin/bash
set -e

echo ${MYSQL_HOST} > /mysql_backup_service/mysql_host.txt

/mysql_backup_service/first_backup.sh

touch /var/log/periodical_backup.log
cron -l2
tail -f /var/log/periodical_backup.log
