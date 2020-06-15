#!/usr/bin/env bash

printenv | cat - /etc/cron.d/cjob > /code/cjob.tmp \
    && mv /code/cjob.tmp /etc/cron.d/cjob

chmod 744 /etc/cron.d/cjob

tail -f /code/cron.log &

cron -f