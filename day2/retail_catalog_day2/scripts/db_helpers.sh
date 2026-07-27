#!/bin/bash
# Shared DB helpers (sourced by start.sh / stop.sh)
DB_CONTAINER_NAME="retail_catalog_day2_db"
DB_USER="admin"
DB_PASSWORD="password"
DB_NAME="retail_catalog"
DB_PORT="5433"
DB_IMAGE="postgres:16-alpine"

wait_for_postgres() {
    local attempts=0
    local max_attempts=20
    until docker exec "${DB_CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" &>/dev/null \
        || [ "$attempts" -eq "$max_attempts" ]; do
        sleep 2
        attempts=$((attempts + 1))
        echo "Waiting for Postgres... ${attempts}/${max_attempts}"
    done
    if [ "$attempts" -eq "$max_attempts" ]; then
        echo "Postgres did not become ready in time." >&2
        docker logs "${DB_CONTAINER_NAME}" 2>&1 | tail -40 || true
        return 1
    fi
    return 0
}

ensure_postgres() {
    local script_root="$1"
    if docker ps --format '{{.Names}}' | grep -qx "${DB_CONTAINER_NAME}"; then
        echo "Postgres container ${DB_CONTAINER_NAME} already running."
        return 0
    fi
    if docker ps -a --format '{{.Names}}' | grep -qx "${DB_CONTAINER_NAME}"; then
        echo "Starting existing container ${DB_CONTAINER_NAME}..."
        docker start "${DB_CONTAINER_NAME}" >/dev/null
        wait_for_postgres
        return $?
    fi
    echo "Creating Postgres container ${DB_CONTAINER_NAME}..."
    docker run --name "${DB_CONTAINER_NAME}" \
        -e POSTGRES_USER="${DB_USER}" \
        -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
        -e POSTGRES_DB="${DB_NAME}" \
        -p "${DB_PORT}:5432" \
        -d "${DB_IMAGE}" >/dev/null
    wait_for_postgres || return 1
    if [ -f "${script_root}/sql/init.sql" ]; then
        echo "Applying sql/init.sql..."
        docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" < "${script_root}/sql/init.sql"
    fi
    return 0
}
