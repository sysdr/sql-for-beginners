# Retail Catalog (Day 1)

PostgreSQL product catalog with a live metrics dashboard.

## Requirements

- Docker
- Python 3

## Quick start

```bash
./start.sh
```

Open http://127.0.0.1:5005/

Stop dashboard:

```bash
./stop.sh
```

Stop dashboard + Postgres:

```bash
./stop.sh --all
```

## Tests

```bash
python3 tests/test_catalog.py
```

## Database

| Setting  | Value |
|----------|-------|
| Container | `retail_catalog_db` |
| User | `admin` |
| Password | `password` |
| Database | `catalog` |
| Port | `5432` |

Connect:

```bash
docker exec -it retail_catalog_db psql -U admin -d catalog
```
