#!/usr/bin/env python3
"""Retail Catalog Day1 — metrics dashboard (http://127.0.0.1:5005/)."""
import json
import os
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
import socketserver

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

HOST = "0.0.0.0"
PORT = 5005
DB_CONTAINER = "retail_catalog_db"
DB_USER = "admin"
DB_NAME = "catalog"

metrics = {
    "demo_run_count": 0,
    "product_count": 0,
    "total_inventory_value": 0.0,
    "avg_price": 0.0,
    "min_price": 0.0,
    "max_price": 0.0,
    "products": [],
    "last_activity": "",
    "last_error": "",
}


def _psql(sql: str) -> str:
    return subprocess.check_output(
        [
            "docker", "exec", "-i", DB_CONTAINER,
            "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-F", ",", "-c", sql,
        ],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def refresh_metrics_from_postgres():
    metrics["last_error"] = ""
    try:
        row = _psql(
            "SELECT COUNT(*)::int, "
            "COALESCE(SUM(price),0)::float, "
            "COALESCE(AVG(price),0)::float, "
            "COALESCE(MIN(price),0)::float, "
            "COALESCE(MAX(price),0)::float "
            "FROM products;"
        )
        parts = [p for p in row.split("\n") if p.strip()][-1].split(",")
        metrics["product_count"] = int(float(parts[0]))
        metrics["total_inventory_value"] = round(float(parts[1]), 2)
        metrics["avg_price"] = round(float(parts[2]), 2)
        metrics["min_price"] = round(float(parts[3]), 2)
        metrics["max_price"] = round(float(parts[4]), 2)

        listing = _psql("SELECT id, name, price::float FROM products ORDER BY id;")
        products = []
        for line in listing.splitlines():
            line = line.strip()
            if not line:
                continue
            pid, name, price = line.split(",", 2)
            products.append({"id": int(pid), "name": name, "price": float(price)})
        metrics["products"] = products
        metrics["last_activity"] = datetime.now().isoformat(timespec="seconds")
    except Exception as exc:
        metrics["last_error"] = str(exc)
        metrics["last_activity"] = datetime.now().isoformat(timespec="seconds")


def run_demo_and_update_metrics():
    """Mutate catalog so every Run Demo changes all metrics (count, sum, avg, min, max)."""
    next_run = metrics.get("demo_run_count", 0) + 1
    stamp = datetime.now().strftime("%H%M%S")
    name = f"Demo Bundle #{next_run} ({stamp})"
    # Rotating price so avg/min/max shift; also bump every existing price by $1
    new_price = round(19.99 + (next_run * 7.25), 2)
    safe_name = name.replace("'", "''")
    sql = (
        "UPDATE products SET price = ROUND(price + 1.00, 2);\n"
        "INSERT INTO products (name, description, price) VALUES\n"
        f"  ('{safe_name}', 'Auto-added by Run Demo #{next_run}', {new_price});\n"
    )
    try:
        subprocess.run(
            [
                "docker", "exec", "-i", DB_CONTAINER,
                "psql", "-U", DB_USER, "-d", DB_NAME,
            ],
            input=sql,
            text=True,
            capture_output=True,
            timeout=30,
            check=True,
        )
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
  <title>Retail Catalog Dashboard (Day 1)</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; min-height: 100vh; padding: 2rem; }
    .wrap { max-width: 1000px; margin: 0 auto; }
    .header { background: #1e293b; padding: 1.75rem 2rem; border-radius: 12px; border-left: 5px solid #38bdf8; margin-bottom: 1.5rem; }
    .header h1 { margin: 0 0 0.35rem; color: #38bdf8; font-size: 1.55rem; }
    .header p { margin: 0; color: #94a3b8; }
    .actions { display: flex; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    button { background: #38bdf8; color: #0f172a; border: 0; padding: 0.65rem 1.1rem; border-radius: 8px; font-weight: 600; cursor: pointer; }
    button.secondary { background: #334155; color: #e2e8f0; }
    button:hover { filter: brightness(1.08); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .card { background: #1e293b; border-radius: 10px; padding: 1.1rem; }
    .card .label { color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.35rem; }
    .card .value { font-size: 1.55rem; font-weight: 700; color: #f8fafc; }
    .zero { color: #f87171 !important; }
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
      <h1>Retail Catalog Dashboard</h1>
      <p>Day 1 — PostgreSQL products metrics (live from Docker Postgres)</p>
    </div>
    <div class="actions">
      <button id="runDemo">Run Demo</button>
      <button class="secondary" id="refresh">Refresh Metrics</button>
    </div>
    <div class="grid">
      <div class="card"><div class="label">Products</div><div class="value" id="product_count">—</div></div>
      <div class="card"><div class="label">Inventory Value</div><div class="value" id="total_inventory_value">—</div></div>
      <div class="card"><div class="label">Avg Price</div><div class="value" id="avg_price">—</div></div>
      <div class="card"><div class="label">Min Price</div><div class="value" id="min_price">—</div></div>
      <div class="card"><div class="label">Max Price</div><div class="value" id="max_price">—</div></div>
      <div class="card"><div class="label">Demo Runs</div><div class="value" id="demo_run_count">—</div></div>
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
    function setVal(id, val, isMoney) {
      const el = document.getElementById(id);
      const num = Number(val);
      el.textContent = isMoney ? money(num) : String(val);
      el.classList.toggle('zero', !Number.isNaN(num) && num === 0 && id !== 'demo_run_count');
    }
    async function loadMetrics() {
      const res = await fetch('/api/metrics');
      const m = await res.json();
      setVal('product_count', m.product_count, false);
      setVal('total_inventory_value', m.total_inventory_value, true);
      setVal('avg_price', m.avg_price, true);
      setVal('min_price', m.min_price, true);
      setVal('max_price', m.max_price, true);
      setVal('demo_run_count', m.demo_run_count, false);
      document.getElementById('last_activity').textContent = m.last_activity || '—';
      document.getElementById('last_error').textContent = m.last_error || '';
      const tbody = document.getElementById('products');
      tbody.innerHTML = (m.products || []).map(p =>
        '<tr><td>' + p.id + '</td><td>' + p.name + '</td><td>' + money(p.price) + '</td></tr>'
      ).join('');
    }
    document.getElementById('refresh').onclick = loadMetrics;
    document.getElementById('runDemo').onclick = async () => {
      await fetch('/api/run-demo', { method: 'POST' });
      await loadMetrics();
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
        print(f"Retail Catalog dashboard listening on http://127.0.0.1:{PORT}/")
        httpd.serve_forever()
