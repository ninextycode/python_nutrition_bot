FROM debian:12.8-slim

# Install necessary packages
RUN apt-get update && \
    apt-get install -y bash cron mariadb-client

# Copy the dump script into the container

WORKDIR /mysql_backup_service
COPY * ./

RUN chmod +x *.sh
RUN mkdir -p /mysql_backup_dumps && chmod a+rw -R /mysql_backup_dumps
RUN crontab /mysql_backup_service/backup_cron

CMD ["./start.sh"]
