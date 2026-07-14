from __future__ import annotations

import datetime as dt

import pytest

from investment_os.pipelines.market import PriceFeedError, parse_yahoo_chart


def payload(timestamps: list[int], closes: list[float | None]) -> dict[str, object]:
    n = len(timestamps)
    quote = {
        "open": [c if c is None else c * 0.99 for c in closes],
        "high": [c if c is None else c * 1.01 for c in closes],
        "low": [c if c is None else c * 0.98 for c in closes],
        "close": closes,
        "volume": [1_000_000] * n,
    }
    return {
        "chart": {
            "error": None,
            "result": [{"timestamp": timestamps, "indicators": {"quote": [quote]}}],
        }
    }


def ts(day: int) -> int:
    return int(dt.datetime(2026, 7, day, 9, 0, tzinfo=dt.UTC).timestamp())


def test_parses_bars_in_order() -> None:
    bars = parse_yahoo_chart(payload([ts(1), ts(2), ts(3)], [100.0, 101.0, 99.5]))
    assert [b.close for b in bars] == [100.0, 101.0, 99.5]
    assert bars[0].date == dt.date(2026, 7, 1)
    assert all(b.net_foreign_bn_idr == 0.0 for b in bars)


def test_null_rows_are_skipped() -> None:
    bars = parse_yahoo_chart(payload([ts(1), ts(2), ts(3)], [100.0, None, 99.5]))
    assert [b.close for b in bars] == [100.0, 99.5]


def test_api_error_raises() -> None:
    with pytest.raises(PriceFeedError):
        parse_yahoo_chart({"chart": {"error": {"code": "Not Found"}, "result": None}})


def test_empty_result_raises() -> None:
    with pytest.raises(PriceFeedError):
        parse_yahoo_chart({"chart": {"error": None, "result": []}})
