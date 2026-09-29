#!/bin/sh

cd /home/radio/trunk-player

for proc in daphne
do
  ps=`grep ^$proc running.pid | tail -n1 | cut -d: -f2`
  echo "Stopping PID $ps for $proc"
  kill $ps
done

