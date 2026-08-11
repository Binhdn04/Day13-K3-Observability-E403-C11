"""Detect PII leaks and latency SLO violations in structured application logs.

Run after a load test, or schedule it periodically with Task Scheduler:
    python scripts/detect_anomalies.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

PII_DETECTORS = {
    "email": re.compile(r"[\w.-]+@[\w.-]+\.\w+"),
    "phone_vn": re.compile(r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)"),
    "cccd": re.compile(r"\b\d{12}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
}


def load_records(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON at line {line_number}", file=sys.stderr)
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def detect(records: list[dict[str, Any]], latency_slo_ms: float) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for record in records:
        raw = json.dumps(record, ensure_ascii=False)
        pii_types = [name for name, pattern in PII_DETECTORS.items() if pattern.search(raw)]
        if pii_types:
            alerts.append({
                "kind": "pii_leak",
                "severity": "critical",
                "correlation_id": record.get("correlation_id"),
                "details": {"types": pii_types, "event": record.get("event")},
            })

        latency = record.get("latency_ms")
        if record.get("event") == "response_sent" and isinstance(latency, (int, float)) and latency > latency_slo_ms:
            alerts.append({
                "kind": "latency_slo_breach",
                "severity": "warning",
                "correlation_id": record.get("correlation_id"),
                "details": {"latency_ms": latency, "threshold_ms": latency_slo_ms, "feature": record.get("feature")},
            })
    return alerts


def append_alerts(path: Path, alerts: list[dict[str, Any]]) -> None:
    if not alerts:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for alert in alerts:
            alert["ts"] = datetime.now(timezone.utc).isoformat()
            file.write(json.dumps(alert, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Detect PII leaks and latency SLO breaches from JSONL logs.")
    parser.add_argument("--log-path", type=Path, default=REPO_ROOT / "data/logs.jsonl")
    parser.add_argument("--alerts-path", type=Path, default=REPO_ROOT / "data/anomaly_alerts.jsonl")
    parser.add_argument("--slo-path", type=Path, default=REPO_ROOT / "config/slo.yaml")
    args = parser.parse_args()

    if not args.log_path.exists():
        raise SystemExit(f"Log file not found: {args.log_path}")
    slo = yaml.safe_load(args.slo_path.read_text(encoding="utf-8"))
    latency_slo_ms = float(slo["slis"]["latency_p95_ms"]["objective"])
    alerts = detect(load_records(args.log_path), latency_slo_ms)
    append_alerts(args.alerts_path, alerts)
    print(f"Analyzed logs: {args.log_path}")
    print(f"Alerts: {len(alerts)}")
    for alert in alerts:
        print(json.dumps(alert, ensure_ascii=False))


if __name__ == "__main__":
    main()
