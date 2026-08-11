from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.dashboard import build_dashboard_payload, metrics_to_panels, render_dashboard


NOW = datetime(2026, 8, 11, 4, 30, tzinfo=timezone.utc)
METRICS = {
    "traffic": 5,
    "successful_requests": 3,
    "failed_requests": 2,
    "latency_p50": 100.0,
    "latency_p95": 200.0,
    "latency_p99": 300.0,
    "avg_cost_usd": 0.01,
    "total_cost_usd": 0.03,
    "tokens_in_total": 100,
    "tokens_out_total": 50,
    "error_rate_pct": 40.0,
    "error_breakdown": {"TimeoutError": 2},
    "quality_avg": 0.8,
}


def test_metrics_endpoint_snapshot_builds_all_six_panels() -> None:
    panels = metrics_to_panels(METRICS)

    assert set(panels) == {"latency", "traffic", "errors", "cost", "tokens", "quality"}
    assert panels["latency"] == {"p50": 100.0, "p95": 200.0, "p99": 300.0}
    assert panels["traffic"] == {"total": 5}
    assert panels["errors"] == {
        "error_rate_pct": 40.0,
        "breakdown": {"TimeoutError": 2},
    }
    assert panels["cost"] == {"total_cost_usd": 0.03, "avg_cost_usd": 0.01}
    assert panels["tokens"]["tokens_in_total"] == 100
    assert panels["tokens"]["tokens_out_total"] == 50
    assert panels["quality"] == {"quality_avg": 0.8}


def test_dashboard_payload_identifies_metrics_source() -> None:
    payload = build_dashboard_payload(METRICS, now=NOW)

    assert payload["source"] == "/metrics"
    assert payload["observation_window"] == "Since API startup"
    assert payload["refresh_seconds"] == 30
    assert len(payload["panels"]) == 6


def test_dashboard_html_exposes_source_units_and_thresholds() -> None:
    html = render_dashboard(build_dashboard_payload(METRICS, now=NOW))

    assert "Source: <code>/metrics</code>" in html
    assert "Observation: Since API startup" in html
    assert "Latency percentiles" in html
    assert "Error rate and breakdown" in html
    assert "Threshold:" in html


def test_missing_required_metric_is_rejected() -> None:
    invalid = dict(METRICS)
    invalid.pop("quality_avg")

    with pytest.raises(ValueError, match="quality_avg"):
        metrics_to_panels(invalid)
