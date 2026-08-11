from collections import Counter

from app import metrics
from app.metrics import percentile


def test_percentile_basic() -> None:
    assert percentile([100, 200, 300, 400], 50) >= 100


def test_snapshot_calculates_error_rate_from_successes_and_failures(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 3)
    monkeypatch.setattr(metrics, "ERRORS", Counter({"TimeoutError": 2}))

    assert metrics.snapshot()["error_rate_pct"] == 40.0


def test_snapshot_error_rate_is_zero_without_requests(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 0)
    monkeypatch.setattr(metrics, "ERRORS", Counter())

    assert metrics.snapshot()["error_rate_pct"] == 0.0
