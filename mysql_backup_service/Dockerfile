FROM debian:12.8-slim

WORKDIR /mysql_backup_service

RUN apt-get update && \
    apt-get install -y bash cron mariadb-client

COPY * ./
RUN chmod +x *.sh

RUN mkdir -p /mysql_backup_dumps && chmod a+rw -R /mysql_backup_dumps
RUN crontab /mysql_backup_service/backup_cron

CMD ["./start.sh"]
