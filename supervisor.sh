#!/usr/bin/env bash
set -euo pipefail

MEMGRAPH_HOST="${MEMGRAPH_HOST:-memgraph}"
MEMGRAPH_PORT="${MEMGRAPH_PORT:-7687}"

mkdir -p /app/logs

shutdown() {
  if [[ -n "${app_pid:-}" ]] && kill -0 "$app_pid" 2>/dev/null; then
    kill "$app_pid" 2>/dev/null || true
  fi
  wait "${app_pid:-}" 2>/dev/null || true
}

trap shutdown EXIT INT TERM

python3 - <<PY
import socket, time, sys

host, port = "${MEMGRAPH_HOST}", ${MEMGRAPH_PORT}
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=1):
            sys.exit(0)
    except OSError:
        time.sleep(1)
sys.exit("Memgraph did not become ready within 60 seconds.")
PY

"$@" > /app/logs/app.log 2>&1 &
app_pid=$!

wait "$app_pid"
status=$?
shutdown
exit "$status"
