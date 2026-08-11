from __future__ import annotations

import os
from datetime import datetime, timezone
from html import escape
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse


METRICS_URL = os.getenv("DASHBOARD_METRICS_URL", "http://127.0.0.1:8000/metrics")
REFRESH_SECONDS = 30
OBSERVATION_WINDOW = "Since API startup"

REQUIRED_METRICS = {
    "latency_p50",
    "latency_p95",
    "latency_p99",
    "traffic",
    "error_rate_pct",
    "error_breakdown",
    "total_cost_usd",
    "avg_cost_usd",
    "tokens_in_total",
    "tokens_out_total",
    "quality_avg",
}

PANEL_SPECS: dict[str, dict[str, Any]] = {
    "latency": {
        "title": "Latency percentiles",
        "unit": "ms",
        "threshold": {"field": "p95", "operator": "lte", "value": 3000},
    },
    "traffic": {
        "title": "Request traffic",
        "unit": "requests",
        "threshold": {"field": "total", "operator": "gte", "value": 1},
    },
    "errors": {
        "title": "Error rate and breakdown",
        "unit": "%",
        "threshold": {"field": "error_rate_pct", "operator": "lte", "value": 2},
    },
    "cost": {
        "title": "Current cost",
        "unit": "USD",
        "threshold": {"field": "total_cost_usd", "operator": "lte", "value": 2.5},
    },
    "tokens": {
        "title": "Input and output tokens",
        "unit": "tokens",
        "threshold": {"field": "max_field_total", "operator": "lte", "value": 50000},
    },
    "quality": {
        "title": "Quality proxy",
        "unit": "score 0–1",
        "threshold": {"field": "quality_avg", "operator": "gte", "value": 0.75},
    },
}


def fetch_metrics(url: str = METRICS_URL) -> dict[str, Any]:
    response = httpx.get(url, timeout=5.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("The /metrics endpoint must return a JSON object")
    return payload


def metrics_to_panels(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    missing = sorted(REQUIRED_METRICS - metrics.keys())
    if missing:
        raise ValueError(f"The /metrics response is missing: {', '.join(missing)}")

    error_breakdown = metrics["error_breakdown"]
    if not isinstance(error_breakdown, dict):
        raise ValueError("error_breakdown must be a JSON object")

    tokens_in = int(metrics["tokens_in_total"])
    tokens_out = int(metrics["tokens_out_total"])
    return {
        "latency": {
            "p50": float(metrics["latency_p50"]),
            "p95": float(metrics["latency_p95"]),
            "p99": float(metrics["latency_p99"]),
        },
        "traffic": {"total": int(metrics["traffic"])},
        "errors": {
            "error_rate_pct": float(metrics["error_rate_pct"]),
            "breakdown": {str(name): int(count) for name, count in error_breakdown.items()},
        },
        "cost": {
            "total_cost_usd": float(metrics["total_cost_usd"]),
            "avg_cost_usd": float(metrics["avg_cost_usd"]),
        },
        "tokens": {
            "tokens_in_total": tokens_in,
            "tokens_out_total": tokens_out,
            "max_field_total": max(tokens_in, tokens_out),
        },
        "quality": {"quality_avg": float(metrics["quality_avg"])},
    }


def build_dashboard_payload(
    metrics_snapshot: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    snapshot = metrics_snapshot if metrics_snapshot is not None else fetch_metrics()
    return {
        "title": "Day 13 AI Observability",
        "generated_at": current_time.isoformat(),
        "observation_window": OBSERVATION_WINDOW,
        "refresh_seconds": REFRESH_SECONDS,
        "source": "/metrics",
        "source_url": METRICS_URL,
        "panels": metrics_to_panels(snapshot),
    }


def _threshold_status(value: float, threshold: dict[str, Any]) -> tuple[str, str]:
    target = float(threshold["value"])
    operator = str(threshold["operator"])
    passing = value <= target if operator == "lte" else value >= target
    symbol = "≤" if operator == "lte" else "≥"
    return ("healthy" if passing else "breached", f"{symbol} {target:g}")


def render_dashboard(payload: dict[str, Any]) -> str:
    panels = payload["panels"]
    statuses = {
        panel_id: _threshold_status(
            float(panel[PANEL_SPECS[panel_id]["threshold"]["field"]]),
            PANEL_SPECS[panel_id]["threshold"],
        )
        for panel_id, panel in panels.items()
    }

    breakdown = panels["errors"]["breakdown"]
    breakdown_html = "<br>".join(
        f"{escape(str(name))}: {count}" for name, count in sorted(breakdown.items())
    ) or "No errors"

    cards = [
        (
            "latency",
            f"P50 {panels['latency']['p50']:.0f} · P95 {panels['latency']['p95']:.0f} · P99 {panels['latency']['p99']:.0f}",
            "P95 is evaluated against the latency SLO",
        ),
        (
            "traffic",
            f"{panels['traffic']['total']}",
            "Total requests received since API startup",
        ),
        (
            "errors",
            f"{panels['errors']['error_rate_pct']:.2f}",
            breakdown_html,
        ),
        (
            "cost",
            f"{panels['cost']['total_cost_usd']:.6f}",
            f"Average per successful request: {panels['cost']['avg_cost_usd']:.6f} USD",
        ),
        (
            "tokens",
            f"{panels['tokens']['tokens_in_total']} in · {panels['tokens']['tokens_out_total']} out",
            "Input and output totals are tracked separately",
        ),
        (
            "quality",
            f"{panels['quality']['quality_avg']:.4f}",
            "Mean heuristic quality score",
        ),
    ]

    card_html = "".join(
        f"""
        <section class="card {statuses[panel_id][0]}">
          <div class="status">{statuses[panel_id][0].upper()}</div>
          <h2>{escape(PANEL_SPECS[panel_id]['title'])}</h2>
          <div class="value">{value}</div>
          <div class="unit">{escape(PANEL_SPECS[panel_id]['unit'])}</div>
          <div class="threshold">Threshold: {escape(statuses[panel_id][1])}</div>
          <div class="details">{details}</div>
        </section>
        """
        for panel_id, value, details in cards
    )

    refresh_ms = int(payload["refresh_seconds"]) * 1000
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(payload['title']))}</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, system-ui, sans-serif; }}
    body {{ margin: 0; background: #0b1220; color: #e5edf8; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }}
    header {{ display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    .meta {{ color: #9eb0c8; font-size: 14px; line-height: 1.6; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .card {{ position: relative; background: #121d30; border: 1px solid #25344d; border-left: 5px solid; border-radius: 12px; padding: 20px; min-height: 190px; }}
    .card.healthy {{ border-left-color: #3ddc97; }}
    .card.breached {{ border-left-color: #ff6b6b; }}
    .status {{ position: absolute; right: 16px; top: 16px; font-size: 11px; letter-spacing: .08em; color: #9eb0c8; }}
    h2 {{ margin: 0 0 20px; font-size: 17px; color: #cbd8e9; }}
    .value {{ font-size: 31px; font-weight: 750; letter-spacing: -.03em; }}
    .unit {{ color: #8fb3de; margin-top: 4px; }}
    .threshold {{ margin-top: 18px; padding-top: 12px; border-top: 1px solid #25344d; color: #cbd8e9; font-size: 13px; }}
    .details {{ margin-top: 10px; color: #8fa3bd; font-size: 13px; line-height: 1.5; }}
    code {{ color: #9ed0ff; }}
    @media (max-width: 640px) {{ header {{ display: block; }} .meta {{ margin-top: 12px; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div><h1>{escape(str(payload['title']))}</h1><div class="meta">CP2 metrics dashboard</div></div>
      <div class="meta">Observation: {escape(str(payload['observation_window']))} · refresh {payload['refresh_seconds']}s<br>
      Source: <code>{escape(str(payload['source']))}</code><br>
      Updated: {escape(str(payload['generated_at']))}</div>
    </header>
    <div class="grid">{card_html}</div>
  </main>
  <script>window.setTimeout(() => window.location.reload(), {refresh_ms});</script>
</body>
</html>"""


def render_unavailable(detail: str) -> str:
    return f"""<!doctype html><html><body style="font-family:system-ui;padding:40px">
    <h1>Dashboard unavailable</h1>
    <p>Start the API on port 8000, then refresh this page.</p>
    <pre>{escape(detail)}</pre></body></html>"""


app = FastAPI(title="Day 13 CP2 Metrics Dashboard")


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        fetch_metrics()
    except (httpx.HTTPError, ValueError) as exc:
        return {"ok": False, "source": "/metrics", "detail": str(exc)}
    return {"ok": True, "source": "/metrics"}


@app.get("/api/metrics")
async def dashboard_metrics() -> dict[str, Any]:
    try:
        return build_dashboard_payload()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/", response_class=HTMLResponse)
async def dashboard_home() -> HTMLResponse:
    try:
        payload = build_dashboard_payload()
    except (httpx.HTTPError, ValueError) as exc:
        return HTMLResponse(render_unavailable(str(exc)), status_code=503)
    return HTMLResponse(render_dashboard(payload))
