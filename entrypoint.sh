#!/usr/bin/env bash
set -euo pipefail

MEMGRAPH_URI="${MEMGRAPH_URI:-bolt://127.0.0.1:7687}"
export MEMGRAPH_URI

mkdir -p /app/logs /var/lib/memgraph /var/log/memgraph

shutdown() {
  if [[ -n "${app_pid:-}" ]] && kill -0 "$app_pid" 2>/dev/null; then
    kill "$app_pid" 2>/dev/null || true
  fi
  if [[ -n "${memgraph_pid:-}" ]] && kill -0 "$memgraph_pid" 2>/dev/null; then
    kill "$memgraph_pid" 2>/dev/null || true
  fi
  wait "${app_pid:-}" "${memgraph_pid:-}" 2>/dev/null || true
}

trap shutdown EXIT INT TERM

/usr/lib/memgraph/memgraph > /app/logs/memgraph.log 2>&1 &
memgraph_pid=$!

python3 - <<'PY'
import socket
import time

deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", 7687), timeout=1):
            raise SystemExit(0)
    except OSError:
        time.sleep(1)
raise SystemExit("Memgraph did not become ready within 60 seconds.")
PY

"$@" > /app/logs/app.log 2>&1 &
app_pid=$!

wait -n "$memgraph_pid" "$app_pid"
status=$?
shutdown
exit "$status"
