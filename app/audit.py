"""Append-only audit records for operator and configuration changes.

Audit events intentionally use a separate file so that request telemetry can be
rotated independently and so this file stays small and reviewable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def audit_log_path() -> Path:
    return Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))


def write_audit_event(event: str, *, actor: str = "system", details: dict[str, Any] | None = None) -> None:
    """Write one important, JSONL-formatted operational event."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor": actor,
        "details": details or {},
    }
    path = audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
