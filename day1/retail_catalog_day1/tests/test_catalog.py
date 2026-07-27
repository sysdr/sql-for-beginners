#!/usr/bin/env python3
"""Tests for retail catalog Day 1 — Postgres seed + dashboard metrics."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DB_CONTAINER = "retail_catalog_db"
DB_USER = "admin"
DB_NAME = "catalog"


def _psql(sql: str) -> str:
    return subprocess.check_output(
        [
            "docker", "exec", "-i", DB_CONTAINER,
            "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", sql,
        ],
        text=True,
    ).strip()


def test_product_count_nonzero():
    n = int(_psql("SELECT COUNT(*) FROM products;"))
    assert n >= 3, f"expected >= 3 products, got {n}"


def test_prices_positive():
    bad = int(_psql("SELECT COUNT(*) FROM products WHERE price IS NULL OR price <= 0;"))
    assert bad == 0, "found products with null/non-positive price"
    total = float(_psql("SELECT COALESCE(SUM(price),0) FROM products;"))
    assert total > 0, "total inventory value should be > 0"


def test_dashboard_metrics():
    import dashboard_web as dw

    dw.refresh_metrics_from_postgres()
    assert dw.metrics["product_count"] >= 3
    assert dw.metrics["total_inventory_value"] > 0
    assert dw.metrics["avg_price"] > 0
    assert dw.metrics["min_price"] > 0
    assert dw.metrics["max_price"] >= dw.metrics["min_price"]
    assert len(dw.metrics["products"]) >= 3
    assert not dw.metrics.get("last_error"), dw.metrics.get("last_error")


def test_run_demo_updates_metrics():
    import dashboard_web as dw

    dw.refresh_metrics_from_postgres()
    before_runs = dw.metrics.get("demo_run_count", 0)
    before_count = dw.metrics["product_count"]
    before_value = dw.metrics["total_inventory_value"]
    before_avg = dw.metrics["avg_price"]

    dw.run_demo_and_update_metrics()

    assert dw.metrics["demo_run_count"] == before_runs + 1
    assert dw.metrics["product_count"] == before_count + 1, (
        f"expected product_count to increase: {before_count} -> {dw.metrics['product_count']}"
    )
    assert dw.metrics["total_inventory_value"] > before_value, (
        f"expected inventory value to rise: {before_value} -> {dw.metrics['total_inventory_value']}"
    )
    assert dw.metrics["avg_price"] != before_avg or dw.metrics["max_price"] > 0
    assert not dw.metrics.get("last_error"), dw.metrics.get("last_error")


if __name__ == "__main__":
    test_product_count_nonzero()
    test_prices_positive()
    test_dashboard_metrics()
    test_run_demo_updates_metrics()
    print("All tests passed.")
