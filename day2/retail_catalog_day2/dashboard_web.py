#!/usr/bin/env python3
"""Retail Catalog Day2 — indexing metrics dashboard (http://127.0.0.1:5006/)."""
import json
import os
import re
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
import socketserver

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

HOST = "0.0.0.0"
PORT = 5006
DB_CONTAINER = "retail_catalog_day2_db"
DB_USER = "admin"
DB_NAME = "retail_catalog"

SEARCH_SQL = "SELECT * FROM products WHERE product_name LIKE 'Vintage Leather Jacket%'"

metrics = {
    "demo_run_count": 0,
    "product_count": 0,
    "jacket_matches": 0,
    "total_inventory_value": 0.0,
    "avg_price": 0.0,
    "min_price": 0.0,
    "max_price": 0.0,
    "index_present": False,
    "index_count": 0,
    "before_ms": 0.0,
    "after_ms": 0.0,
    "speedup": 0.0,
    "before_plan": "",
    "after_plan": "",
    "sample_products": [],
    "last_activity": "",
    "last_error": "",
}


def _psql(sql: str, tuples_only: bool = True) -> str:
    cmd = [
        "docker", "exec", "-i", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
    ]
    if tuples_only:
        cmd.extend(["-t", "-A", "-F", ","])
    cmd.extend(["-c", sql])
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()


def _parse_explain_ms(explain_text: str) -> float:
    """Extract Execution Time (ms) from EXPLAIN ANALYZE output."""
    m = re.search(r"Execution Time:\s*([0-9.]+)\s*ms", explain_text)
    if m:
        return float(m.group(1))
    # Fallback: Planning + Execution if only Planning present
    times = re.findall(r"(?:Planning|Execution) Time:\s*([0-9.]+)\s*ms", explain_text)
    if times:
        return sum(float(t) for t in times)
    return 0.0


def _plan_summary(explain_text: str) -> str:
    lines = [ln.strip() for ln in explain_text.splitlines() if ln.strip()]
    # Prefer index-related nodes when present (Bitmap Index Scan / Index Scan)
    for ln in lines:
        if "Index Scan" in ln or "Index Only Scan" in ln:
            return ln[:120]
    for ln in lines:
        if "Scan" in ln:
            return ln[:120]
    return lines[0][:120] if lines else ""


def refresh_metrics_from_postgres():
    metrics["last_error"] = ""
    try:
        row = _psql(
            "SELECT COUNT(*)::int, "
            "COUNT(*) FILTER (WHERE product_name LIKE 'Vintage Leather Jacket%')::int, "
            "COALESCE(SUM(price),0)::float, "
            "COALESCE(AVG(price),0)::float, "
            "COALESCE(MIN(price),0)::float, "
            "COALESCE(MAX(price),0)::float "
            "FROM products;"
        )
        parts = [p for p in row.split("\n") if p.strip()][-1].split(",")
        metrics["product_count"] = int(float(parts[0]))
        metrics["jacket_matches"] = int(float(parts[1]))
        metrics["total_inventory_value"] = round(float(parts[2]), 2)
        metrics["avg_price"] = round(float(parts[3]), 2)
        metrics["min_price"] = round(float(parts[4]), 2)
        metrics["max_price"] = round(float(parts[5]), 2)

        idx = _psql(
            "SELECT COUNT(*)::int FROM pg_indexes "
            "WHERE tablename = 'products' AND indexname = 'product_name_idx';"
        )
        metrics["index_count"] = int(idx.splitlines()[-1].strip() or "0")
        metrics["index_present"] = metrics["index_count"] > 0

        listing = _psql(
            "SELECT product_id, product_name, price::float FROM products "
            "WHERE product_name LIKE 'Vintage Leather Jacket%' "
            "ORDER BY product_id LIMIT 8;"
        )
        samples = []
        for line in listing.splitlines():
            line = line.strip()
            if not line:
                continue
            pid, name, price = line.split(",", 2)
            samples.append({"id": int(pid), "name": name, "price": float(price)})
        metrics["sample_products"] = samples
        metrics["last_activity"] = datetime.now().isoformat(timespec="seconds")
    except Exception as exc:
        metrics["last_error"] = str(exc)
        metrics["last_activity"] = datetime.now().isoformat(timespec="seconds")


def run_demo_and_update_metrics():
    """Drop index → timed query → create index → timed query → mutate catalog."""
    next_run = metrics.get("demo_run_count", 0) + 1
    stamp = datetime.now().strftime("%H%M%S")
    safe_name = f"Vintage Leather Jacket - Demo {next_run} ({stamp})".replace("'", "''")
    new_price = round(89.99 + (next_run * 3.5), 2)

    try:
        # 1) Ensure clean slate without index
        _psql("DROP INDEX IF EXISTS product_name_idx;")

        # 2) Before: Seq Scan expected
        before_out = _psql(f"EXPLAIN ANALYZE {SEARCH_SQL};", tuples_only=False)
        before_ms = _parse_explain_ms(before_out)
        before_plan = _plan_summary(before_out)

        # 3) Create pattern-ops index so LIKE 'prefix%' can use btree
        _psql(
            "CREATE INDEX product_name_idx ON products "
            "(product_name varchar_pattern_ops);"
        )
        _psql("ANALYZE products;")

        # 4) After: Index / Bitmap Index Scan expected
        after_out = _psql(f"EXPLAIN ANALYZE {SEARCH_SQL};", tuples_only=False)
        after_ms = _parse_explain_ms(after_out)
        after_plan = _plan_summary(after_out)

        # 5) Mutate catalog so inventory metrics change every demo
        _psql(
            "UPDATE products SET price = ROUND(price + 0.50, 2), "
            "updated_at = CURRENT_TIMESTAMP "
            "WHERE product_name LIKE 'Vintage Leather Jacket%';"
        )
        _psql(
            "INSERT INTO products (product_name, description, price, stock_quantity, category_id) "
            f"VALUES ('{safe_name}', 'Auto-added by Run Demo #{next_run}', {new_price}, 25, 2);"
        )

        metrics["before_ms"] = round(before_ms, 3)
        metrics["after_ms"] = round(after_ms, 3)
        metrics["before_plan"] = before_plan
        metrics["after_plan"] = after_plan
        if after_ms > 0:
            metrics["speedup"] = round(before_ms / after_ms, 2)
        else:
            metrics["speedup"] = round(before_ms, 2) if before_ms else 0.0
        metrics["last_error"] = ""
    except Exception as exc:
        metrics["last_error"] = str(exc)

    refresh_metrics_from_postgres()
    metrics["demo_run_count"] = next_run


def get_dashboard_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Retail Catalog Indexing Dashboard (Day 2)</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; min-height: 100vh; padding: 2rem; }
    .wrap { max-width: 1100px; margin: 0 auto; }
    .header { background: #1e293b; padding: 1.75rem 2rem; border-radius: 12px; border-left: 5px solid #34d399; margin-bottom: 1.5rem; }
    .header h1 { margin: 0 0 0.35rem; color: #34d399; font-size: 1.55rem; }
    .header p { margin: 0; color: #94a3b8; }
    .actions { display: flex; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    button { background: #34d399; color: #0f172a; border: 0; padding: 0.65rem 1.1rem; border-radius: 8px; font-weight: 600; cursor: pointer; }
    button.secondary { background: #334155; color: #e2e8f0; }
    button:hover { filter: brightness(1.08); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .card { background: #1e293b; border-radius: 10px; padding: 1.1rem; }
    .card .label { color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.35rem; }
    .card .value { font-size: 1.45rem; font-weight: 700; color: #f8fafc; word-break: break-word; }
    .zero { color: #f87171 !important; }
    .plans { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }
    @media (max-width: 800px) { .plans { grid-template-columns: 1fr; } }
    .plan { background: #1e293b; border-radius: 10px; padding: 1rem; font-family: ui-monospace, monospace; font-size: 0.85rem; color: #cbd5e1; min-height: 4rem; }
    .plan h3 { margin: 0 0 0.5rem; color: #94a3b8; font-family: 'Segoe UI', system-ui, sans-serif; font-size: 0.9rem; }
    table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 10px; overflow: hidden; }
    th, td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #334155; }
    th { color: #94a3b8; font-weight: 600; }
    .status { color: #94a3b8; font-size: 0.9rem; margin-top: 1rem; }
    .err { color: #f87171; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <h1>Retail Catalog — Indexing Dashboard</h1>
      <p>Day 2 — Seq Scan vs Index Scan on product_name (live from Docker Postgres)</p>
    </div>
    <div class="actions">
      <button id="runDemo">Run Indexing Demo</button>
      <button class="secondary" id="refresh">Refresh Metrics</button>
    </div>
    <div class="grid">
      <div class="card"><div class="label">Products</div><div class="value" id="product_count">—</div></div>
      <div class="card"><div class="label">Jacket Matches</div><div class="value" id="jacket_matches">—</div></div>
      <div class="card"><div class="label">Inventory Value</div><div class="value" id="total_inventory_value">—</div></div>
      <div class="card"><div class="label">Avg Price</div><div class="value" id="avg_price">—</div></div>
      <div class="card"><div class="label">Min Price</div><div class="value" id="min_price">—</div></div>
      <div class="card"><div class="label">Max Price</div><div class="value" id="max_price">—</div></div>
      <div class="card"><div class="label">Index Present</div><div class="value" id="index_present">—</div></div>
      <div class="card"><div class="label">Before (ms)</div><div class="value" id="before_ms">—</div></div>
      <div class="card"><div class="label">After (ms)</div><div class="value" id="after_ms">—</div></div>
      <div class="card"><div class="label">Speedup</div><div class="value" id="speedup">—</div></div>
      <div class="card"><div class="label">Demo Runs</div><div class="value" id="demo_run_count">—</div></div>
    </div>
    <div class="plans">
      <div class="plan"><h3>Plan BEFORE index</h3><div id="before_plan">—</div></div>
      <div class="plan"><h3>Plan AFTER index</h3><div id="after_plan">—</div></div>
    </div>
    <table>
      <thead><tr><th>ID</th><th>Name</th><th>Price</th></tr></thead>
      <tbody id="products"></tbody>
    </table>
    <p class="status">Last activity: <span id="last_activity">—</span></p>
    <p class="status err" id="last_error"></p>
  </div>
  <script>
    function money(n) { return '$' + Number(n).toFixed(2); }
    function setVal(id, val, opts) {
      opts = opts || {};
      const el = document.getElementById(id);
      const num = Number(val);
      if (opts.bool) {
        el.textContent = val ? 'Yes' : 'No';
        el.classList.toggle('zero', !val);
        return;
      }
      if (opts.money) el.textContent = money(num);
      else if (opts.ms) el.textContent = Number(val).toFixed(3) + ' ms';
      else if (opts.x) el.textContent = Number(val).toFixed(2) + 'x';
      else el.textContent = String(val);
      const allowZero = opts.allowZero || id === 'demo_run_count';
      el.classList.toggle('zero', !allowZero && !Number.isNaN(num) && num === 0);
    }
    async function loadMetrics() {
      const res = await fetch('/api/metrics');
      const m = await res.json();
      setVal('product_count', m.product_count, {});
      setVal('jacket_matches', m.jacket_matches, {});
      setVal('total_inventory_value', m.total_inventory_value, { money: true });
      setVal('avg_price', m.avg_price, { money: true });
      setVal('min_price', m.min_price, { money: true });
      setVal('max_price', m.max_price, { money: true });
      setVal('index_present', m.index_present, { bool: true });
      setVal('before_ms', m.before_ms, { ms: true, allowZero: m.demo_run_count === 0 });
      setVal('after_ms', m.after_ms, { ms: true, allowZero: m.demo_run_count === 0 });
      setVal('speedup', m.speedup, { x: true, allowZero: m.demo_run_count === 0 });
      setVal('demo_run_count', m.demo_run_count, { allowZero: true });
      document.getElementById('before_plan').textContent = m.before_plan || '— (run demo)';
      document.getElementById('after_plan').textContent = m.after_plan || '— (run demo)';
      document.getElementById('last_activity').textContent = m.last_activity || '—';
      document.getElementById('last_error').textContent = m.last_error || '';
      const tbody = document.getElementById('products');
      tbody.innerHTML = (m.sample_products || []).map(p =>
        '<tr><td>' + p.id + '</td><td>' + p.name + '</td><td>' + money(p.price) + '</td></tr>'
      ).join('');
    }
    document.getElementById('refresh').onclick = loadMetrics;
    document.getElementById('runDemo').onclick = async () => {
      const btn = document.getElementById('runDemo');
      btn.disabled = true;
      btn.textContent = 'Running…';
      try {
        await fetch('/api/run-demo', { method: 'POST' });
        await loadMetrics();
      } finally {
        btn.disabled = false;
        btn.textContent = 'Run Indexing Demo';
      }
    };
    loadMetrics();
    setInterval(loadMetrics, 5000);
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, content_type="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            refresh_metrics_from_postgres()
            self._send(200, get_dashboard_html())
        elif path == "/api/metrics":
            refresh_metrics_from_postgres()
            self._send(200, json.dumps(metrics), "application/json")
        else:
            self._send(404, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/run-demo":
            run_demo_and_update_metrics()
            self._send(200, json.dumps(metrics), "application/json")
        else:
            self._send(404, "Not found")


class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    refresh_metrics_from_postgres()
    with ReuseTCPServer((HOST, PORT), Handler) as httpd:
        print(f"Retail Catalog Day2 dashboard listening on http://127.0.0.1:{PORT}/")
        httpd.serve_forever()
