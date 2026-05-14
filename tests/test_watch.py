from __future__ import annotations

from tracker.models import Listing
from tracker.watch import diff_new


def _l(sku: str, mem: int = 24, price: int = 159800) -> Listing:
    return Listing(
        source="apple_refurb",
        condition="refurb",
        title=f"Mac mini (M4, {mem}GB) [整備済]",
        chip="M4",
        memory_gb=mem,
        storage_gb=512,
        price_jpy=price,
        url=f"https://example.com/{sku}",
        sku=sku,
    )


def test_first_run_returns_all_as_new():
    fetched = [_l("FA001"), _l("FA002", mem=32)]
    signals, updated = diff_new(fetched, seen={}, today="2026-05-15")
    assert {s.title for s in signals} == {f.title for f in fetched}
    assert set(updated.keys()) == {"FA001", "FA002"}


def test_second_run_with_same_skus_returns_no_signals():
    seen = {"FA001": {"first_seen": "2026-05-15"}}
    fetched = [_l("FA001")]
    signals, updated = diff_new(fetched, seen, today="2026-05-15")
    assert signals == []
    assert updated == seen  # unchanged


def test_new_sku_added_alongside_existing():
    seen = {"FA001": {"first_seen": "2026-05-15"}}
    fetched = [_l("FA001"), _l("FA002", mem=32, price=189800)]
    signals, updated = diff_new(fetched, seen, today="2026-05-16")
    assert len(signals) == 1
    assert signals[0].title.endswith("[整備済]")
    assert "FA002" in updated and updated["FA002"]["first_seen"] == "2026-05-16"


def test_listing_without_sku_is_skipped():
    fetched = [Listing(source="apple_refurb", condition="refurb", title="x", chip="M4",
                       memory_gb=24, storage_gb=512, price_jpy=1, url="u", sku=None)]
    signals, updated = diff_new(fetched, seen={}, today="2026-05-15")
    assert signals == [] and updated == {}
