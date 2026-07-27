#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

DB_CONTAINER_NAME="retail_catalog_day2_db"

echo "=== Stopping dashboard ==="
if [ -f ".dashboard.pid" ]; then
    PID="$(cat .dashboard.pid)"
    if [ -n "${PID}" ] && kill -0 "${PID}" 2>/dev/null; then
        kill "${PID}" 2>/dev/null && echo "Killed dashboard PID ${PID}." || true
    fi
    rm -f .dashboard.pid
fi
pkill -f "${SCRIPT_DIR}/dashboard_web.py" 2>/dev/null && echo "Cleared remaining dashboard processes." || true

echo "=== Stopping and removing Docker container ==="
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "${DB_CONTAINER_NAME}"; then
    docker stop "${DB_CONTAINER_NAME}" >/dev/null 2>&1 && echo "Stopped ${DB_CONTAINER_NAME}." || true
    docker rm "${DB_CONTAINER_NAME}" >/dev/null 2>&1 && echo "Removed ${DB_CONTAINER_NAME}." || true
else
    echo "Container ${DB_CONTAINER_NAME} not found."
fi

echo "=== Removing unused Docker resources ==="
docker container prune -f 2>/dev/null || true
docker image prune -f 2>/dev/null || true
docker volume prune -f 2>/dev/null || true
docker network prune -f 2>/dev/null || true

echo "=== Removing cache, target, and temp files ==="
find "${SCRIPT_DIR}" -type d \( -name __pycache__ -o -name .pytest_cache -o -name target -o -name dist -o -name build -o -name .venv -o -name venv \) -prune -exec rm -rf {} + 2>/dev/null || true
find "${SCRIPT_DIR}" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.dashboard.pid' -o -name '*.log' \) -delete 2>/dev/null || true

echo "=== Cleanup complete ==="
