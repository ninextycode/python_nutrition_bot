FROM debian:12.8-slim

WORKDIR /mysql_backup_service

RUN apt-get update && \
    apt-get install -y bash cron mariadb-client

RUN chmod +x *.sh
RUN mkdir -p /mysql_backup_dumps && chmod a+rw -R /mysql_backup_dumps
RUN crontab /mysql_backup_service/backup_cron

COPY * ./

CMD ["./start.sh"]
