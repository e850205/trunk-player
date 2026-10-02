#! /bin/bash
# Switch a local trunk-recorder between systems that one SDR can't cover at the same time.
#
#   switch-system.sh <name>   restart trunk-recorder with config-<name>.json
#   switch-system.sh status   print the name of the running config
#
# Each system needs a config-<name>.json in the trunk-recorder folder (set
# TRUNK_RECORDER_DIR, default ../trunk-recorder next to trunk-player). config.json
# is a link to the active one so a plain restart keeps the last choice.
#-------------------------------------------------------
PLAYER_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TR_DIR="${TRUNK_RECORDER_DIR:-$PLAYER_DIR/../trunk-recorder}"
cd "$TR_DIR" || exit 1

PID_FILE=trunk-recorder.pid
LOG_FILE=trunk-recorder.log

active() {
  basename "$(readlink config.json)" .json | sed 's/^config-//'
}

running_pid() {
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    echo "$pid"
  else
    # Started some other way
    pgrep -f "build/trunk-recorder -c config" | head -1
  fi
}

case "$1" in
  status|"")
    echo "$(active)"
    [ -n "$(running_pid)" ] || echo "(not running)"
    exit 0
    ;;
esac

name="$1"
if [ ! -f "config-$name.json" ]; then
  echo "No config-$name.json in $TR_DIR" >&2
  exit 1
fi

pid="$(running_pid)"
if [ -n "$pid" ]; then
  kill -INT "$pid"
  for i in $(seq 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  kill -9 "$pid" 2>/dev/null
fi

ln -sfn "config-$name.json" config.json
nohup ./build/trunk-recorder -c config.json >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Switched to $name"
