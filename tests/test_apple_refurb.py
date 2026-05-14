from __future__ import annotations

from tracker.scrapers.apple_refurb import parse, _parse_memory, _parse_storage


def _wrap(*products: dict) -> str:
    import json as _json
    blocks = "".join(
        f'<script type="application/ld+json">{_json.dumps(p, ensure_ascii=False)}</script>'
        for p in products
    )
    return f"<html><body>{blocks}</body></html>"


def _product(name: str, price: int, sku: str = "FXXX/A") -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "url": f"https://www.apple.com/jp/shop/product/{sku}/x",
        "offers": [{"@type": "Offer", "priceCurrency": "JPY", "price": price, "sku": sku}],
    }


def test_parse_memory_picks_first_low_value():
    assert _parse_memory("Mac mini（M4チップ、24GB、512GB SSD）[整備済製品]") == 24
    assert _parse_memory("Mac mini（M4チップ、32GB、1TB SSD）[整備済製品]") == 32


def test_parse_storage_handles_tb_and_gb():
    assert _parse_storage("Mac mini（M4チップ、24GB、512GB SSD）[整備済製品]") == 512
    assert _parse_storage("Mac mini（M4チップ、32GB、1TB SSD）[整備済製品]") == 1024


def test_parse_picks_m4_mini_with_target_memory():
    html = _wrap(
        _product("Mac mini（M4チップ、24GB、512GB SSD）[整備済製品]", 159800, "FA001/A"),
        _product("Mac mini（M4チップ、32GB、1TB SSD）[整備済製品]", 199800, "FA002/A"),
        _product("Mac mini（M4チップ、16GB、256GB SSD）[整備済製品]", 99800, "FA003/A"),
        _product("Mac mini（M4 Proチップ、48GB、1TB SSD）[整備済製品]", 249800, "FA004/A"),
        _product("MacBook Pro（M4チップ、24GB、512GB SSD）[整備済製品]", 249800, "FA005/A"),
    )
    listings = parse(html)
    skus = sorted(l.sku for l in listings)
    assert skus == ["FA001/A", "FA002/A"]
    by_sku = {l.sku: l for l in listings}
    assert by_sku["FA001/A"].memory_gb == 24
    assert by_sku["FA001/A"].storage_gb == 512
    assert by_sku["FA001/A"].price_jpy == 159800
    assert by_sku["FA002/A"].memory_gb == 32


def test_parse_ignores_non_product_blocks():
    html = (
        '<script type="application/ld+json">{"@type":"BreadcrumbList"}</script>'
        '<script type="application/ld+json">not json</script>'
    )
    assert parse(html) == []
