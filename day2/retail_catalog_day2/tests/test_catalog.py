#!/usr/bin/env python3
"""Tests for retail catalog Day 2 — indexing + dashboard metrics."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DB_CONTAINER = "retail_catalog_day2_db"
DB_USER = "admin"
DB_NAME = "retail_catalog"


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
    assert n >= 1000, f"expected bulk seed (>=1000), got {n}"


def test_jacket_matches_exist():
    n = int(_psql("SELECT COUNT(*) FROM products WHERE product_name LIKE 'Vintage Leather Jacket%';"))
    assert n >= 1, f"expected Vintage Leather Jacket rows, got {n}"


def test_prices_positive():
    bad = int(_psql("SELECT COUNT(*) FROM products WHERE price IS NULL OR price <= 0;"))
    assert bad == 0, "found products with null/non-positive price"
    total = float(_psql("SELECT COALESCE(SUM(price),0) FROM products;"))
    assert total > 0, "total inventory value should be > 0"


def test_dashboard_metrics():
    import dashboard_web as dw

    dw.refresh_metrics_from_postgres()
    assert dw.metrics["product_count"] >= 1000
    assert dw.metrics["jacket_matches"] >= 1
    assert dw.metrics["total_inventory_value"] > 0
    assert dw.metrics["avg_price"] > 0
    assert dw.metrics["min_price"] > 0
    assert dw.metrics["max_price"] >= dw.metrics["min_price"]
    assert len(dw.metrics["sample_products"]) >= 1
    assert not dw.metrics.get("last_error"), dw.metrics.get("last_error")


def test_run_demo_updates_metrics():
    import dashboard_web as dw

    dw.refresh_metrics_from_postgres()
    before_runs = dw.metrics.get("demo_run_count", 0)
    before_count = dw.metrics["product_count"]
    before_value = dw.metrics["total_inventory_value"]
    before_jackets = dw.metrics["jacket_matches"]

    dw.run_demo_and_update_metrics()

    assert not dw.metrics.get("last_error"), dw.metrics.get("last_error")
    assert dw.metrics["demo_run_count"] == before_runs + 1
    assert dw.metrics["product_count"] == before_count + 1, (
        f"expected product_count +1: {before_count} -> {dw.metrics['product_count']}"
    )
    assert dw.metrics["jacket_matches"] == before_jackets + 1
    assert dw.metrics["total_inventory_value"] > before_value, (
        f"expected inventory value to rise: {before_value} -> {dw.metrics['total_inventory_value']}"
    )
    assert dw.metrics["index_present"] is True
    assert dw.metrics["before_ms"] > 0, "before_ms should be > 0 after demo"
    assert dw.metrics["after_ms"] > 0, "after_ms should be > 0 after demo"
    assert dw.metrics["speedup"] > 0
    assert "Scan" in (dw.metrics["before_plan"] or "") or "scan" in (dw.metrics["before_plan"] or "").lower()
    assert dw.metrics["after_plan"], "after_plan should be populated"


if __name__ == "__main__":
    test_product_count_nonzero()
    test_jacket_matches_exist()
    test_prices_positive()
    test_dashboard_metrics()
    test_run_demo_updates_metrics()
    print("All tests passed.")
