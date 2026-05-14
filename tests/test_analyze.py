from __future__ import annotations

from datetime import date, timedelta

from tracker.analyze import detect_signals


def _row(date_str: str, source: str, memory: int, price: int, sku: str = "", title: str = "", url: str = "") -> dict:
    return {
        "date": date_str,
        "source": source,
        "memory_gb": memory,
        "price_jpy": price,
        "sku": sku,
        "title": title,
        "url": url,
    }


def test_apple_refurb_new_sku_triggers_in_stock_signal():
    today = [_row(date.today().isoformat(), "apple_refurb", 24, 159800, sku="FX-NEW")]
    history = [
        _row((date.today() - timedelta(days=2)).isoformat(), "apple_refurb", 24, 162000, sku="FX-OLD"),
    ]
    signals = detect_signals(today, history)
    kinds = {s.kind for s in signals}
    assert "new_refurb_in_stock" in kinds


def test_window_low_triggers_when_below_prior_min():
    today_str = date.today().isoformat()
    today = [_row(today_str, "iosys", 24, 119800)]
    history = [
        _row((date.today() - timedelta(days=d)).isoformat(), "iosys", 24, p)
        for d, p in [(1, 124800), (5, 122800), (10, 128000)]
    ]
    signals = detect_signals(today, history)
    lows = [s for s in signals if s.kind == "new_window_low"]
    assert len(lows) == 1
    assert lows[0].price_jpy == 119800
    assert lows[0].prev_low_jpy == 122800


def test_window_low_does_not_trigger_when_equal_or_higher():
    today_str = date.today().isoformat()
    today = [_row(today_str, "iosys", 24, 122800)]
    history = [
        _row((date.today() - timedelta(days=1)).isoformat(), "iosys", 24, 122800),
    ]
    assert [s for s in detect_signals(today, history) if s.kind == "new_window_low"] == []


def test_signals_partitioned_per_memory():
    today_str = date.today().isoformat()
    today = [
        _row(today_str, "iosys", 24, 119800),
        _row(today_str, "iosys", 32, 165000),
    ]
    history = [
        _row((date.today() - timedelta(days=1)).isoformat(), "iosys", 24, 120000),
        _row((date.today() - timedelta(days=1)).isoformat(), "iosys", 32, 159000),
    ]
    signals = detect_signals(today, history)
    lows = [s for s in signals if s.kind == "new_window_low"]
    # Only 24GB should be a window-low (32GB went UP)
    assert len(lows) == 1
    assert lows[0].memory_gb == 24
