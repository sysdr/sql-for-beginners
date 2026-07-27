#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# shellcheck source=scripts/db_helpers.sh
source "$SCRIPT_DIR/scripts/db_helpers.sh"

PID_FILE="$SCRIPT_DIR/.dashboard.pid"
DASHBOARD_PY="$SCRIPT_DIR/dashboard_web.py"
PORT=5005

echo "Ensuring Postgres is up..."
ensure_postgres "$SCRIPT_DIR"

# Avoid duplicate dashboards
if [ -f "$PID_FILE" ]; then
    OLD_PID="$(cat "$PID_FILE")"
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Dashboard already running (PID $OLD_PID)."
        echo "URL: http://127.0.0.1:${PORT}/"
        exit 0
    fi
    rm -f "$PID_FILE"
fi
# Extra guard: kill stale listeners on our port/script
EXISTING="$(pgrep -f "$DASHBOARD_PY" || true)"
if [ -n "$EXISTING" ]; then
    echo "Found existing dashboard process(es): $EXISTING — stopping duplicates."
    pkill -f "$DASHBOARD_PY" 2>/dev/null || true
    sleep 1
fi

python3 "$DASHBOARD_PY" &
echo $! > "$PID_FILE"
sleep 1
if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Dashboard started (PID $(cat "$PID_FILE"))."
    echo "URL: http://127.0.0.1:${PORT}/"
else
    rm -f "$PID_FILE"
    echo "Failed to start dashboard." >&2
    exit 1
fi
