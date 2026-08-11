from collections import Counter

from app import metrics
from app.metrics import percentile


def test_percentile_basic() -> None:
    assert percentile([100, 200, 300, 400], 50) == 200


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([100, 200, 300, 400, 500, 600], 50) == 300
    assert percentile([], 95) == 0.0


def test_snapshot_calculates_error_rate_from_successes_and_failures(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 3)
    monkeypatch.setattr(metrics, "ERRORS", Counter({"TimeoutError": 2}))

    result = metrics.snapshot()

    assert result["traffic"] == 5
    assert result["successful_requests"] == 3
    assert result["failed_requests"] == 2
    assert result["error_rate_pct"] == 40.0


def test_snapshot_error_rate_is_zero_without_requests(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 0)
    monkeypatch.setattr(metrics, "ERRORS", Counter())

    assert metrics.snapshot()["error_rate_pct"] == 0.0


def test_snapshot_error_rate_is_one_hundred_with_only_failures(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 0)
    monkeypatch.setattr(metrics, "ERRORS", Counter({"RuntimeError": 1}))

    result = metrics.snapshot()

    assert result["traffic"] == 1
    assert result["error_rate_pct"] == 100.0
    assert result["error_breakdown"] == {"RuntimeError": 1}


def test_snapshot_preserves_error_breakdown(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 9)
    monkeypatch.setattr(
        metrics,
        "ERRORS",
        Counter({"TimeoutError": 1, "RuntimeError": 1}),
    )

    result = metrics.snapshot()

    assert result["traffic"] == 11
    assert result["failed_requests"] == 2
    assert result["error_rate_pct"] == 18.18
    assert sum(result["error_breakdown"].values()) == result["failed_requests"]
