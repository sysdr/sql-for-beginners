#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PID_FILE="$SCRIPT_DIR/.dashboard.pid"
DASHBOARD_PY="$SCRIPT_DIR/dashboard_web.py"
DB_CONTAINER_NAME="retail_catalog_day2_db"

if [ -f "$PID_FILE" ]; then
    PID="$(cat "$PID_FILE")"
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        echo "Stopped dashboard PID $PID."
    fi
    rm -f "$PID_FILE"
fi
pkill -f "$DASHBOARD_PY" 2>/dev/null && echo "Cleared any remaining dashboard processes." || true

if [ "${1:-}" = "--all" ]; then
    if docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER_NAME"; then
        docker stop "$DB_CONTAINER_NAME" >/dev/null && echo "Stopped Postgres container $DB_CONTAINER_NAME."
    fi
fi
echo "Stop complete. (Use ./stop.sh --all to also stop Postgres.)"
