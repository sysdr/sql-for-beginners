#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

DB_CONTAINER_NAME="retail_catalog_db"

echo "=== Stopping dashboard ==="
if [ -f ".dashboard.pid" ]; then
    PID="$(cat .dashboard.pid)"
    kill "$PID" 2>/dev/null && echo "Killed dashboard PID $PID." || true
    rm -f .dashboard.pid
fi
pkill -f "$SCRIPT_DIR/dashboard_web.py" 2>/dev/null || true

echo "=== Stopping and removing Docker container ==="
docker stop "$DB_CONTAINER_NAME" 2>/dev/null && echo "Stopped $DB_CONTAINER_NAME." || true
docker rm "$DB_CONTAINER_NAME" 2>/dev/null && echo "Removed $DB_CONTAINER_NAME." || true

echo "=== Removing unused Docker resources ==="
docker container prune -f 2>/dev/null || true
docker image prune -f 2>/dev/null || true
docker volume prune -f 2>/dev/null || true
docker network prune -f 2>/dev/null || true

echo "=== Removing cache and temp files ==="
find "$SCRIPT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -type d -name venv -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -name '*.pyc' -delete 2>/dev/null || true
find "$SCRIPT_DIR" -name '*.pyo' -delete 2>/dev/null || true
find "$SCRIPT_DIR" -name '.dashboard.pid' -delete 2>/dev/null || true

echo "=== Cleanup complete ==="
