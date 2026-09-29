#!/bin/sh
# Start the web server by hand, see docs/supervisor.rst to run it as a service
# Change to your path
cd /home/radio/trunk-player

. env/bin/activate
ts=`date +%Y%m%d%H%M%S`

[ -f daphne.log ] && cp -f daphne.log daphne.log.$ts
nohup daphne trunk_player.asgi:application --port 7055 --bind 127.0.0.1 > daphne.log 2>&1 &
d_pid=$!

echo "Started $ts" > running.pid
echo "daphne:$d_pid" >> running.pid
