# Retail Catalog (Day 2) — Indexing

PostgreSQL product catalog demonstrating query performance before and after an index on `product_name`, with a live metrics dashboard.

## Requirements

- Docker
- Python 3 (stdlib only — see `requirements.txt`)

## Quick start

```bash
./start.sh
```

Open http://127.0.0.1:5006/

Click **Run Indexing Demo** to compare Seq Scan vs Index Scan timings.

Stop dashboard:

```bash
./stop.sh
```

Stop dashboard + Postgres:

```bash
./stop.sh --all
```

Full cleanup (stop services, remove container, prune unused Docker resources):

```bash
./cleanup.sh
```

## Tests

```bash
python3 tests/test_catalog.py
```

## Database

| Setting   | Value |
|-----------|-------|
| Container | `retail_catalog_day2_db` |
| User      | `admin` |
| Password  | `password` |
| Database  | `retail_catalog` |
| Host port | `5433` |

Connect:

```bash
docker exec -it retail_catalog_day2_db psql -U admin -d retail_catalog
```
