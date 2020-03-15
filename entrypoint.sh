#!/bin/bash

# https://stackoverflow.com/a/41938139
# expose environment vars to cron job
printenv >> /etc/environment
cron -f
