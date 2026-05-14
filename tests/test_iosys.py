from __future__ import annotations

from tracker.scrapers.iosys import parse, _is_target, _parse_memory, _parse_storage


def _card(title: str, price: str, href: str, condition: str = "中古Bランク") -> str:
    return f"""
    <li>
      <a href="{href}">
        <div class="item-list">
          <p class="name">{title}</p>
          <div class="wrap">
            <div class="rank b">
              <p class="condition">{condition}</p>
            </div>
            <div class="price"><p>{price}<span class="yen">円</span></p></div>
          </div>
        </div>
      </a>
    </li>
    """


def test_is_target_filters_chip_and_memory():
    assert _is_target("Mac mini MU9E3J/A 2024【Apple M4(24GB)/10コアGPU/512GB SSD】")
    assert _is_target("Mac mini MU9F3J/A 2024【Apple M4(32GB)/10コアGPU/1TB SSD】")
    assert not _is_target("Mac mini MU9D3J/A 2024【Apple M4(16GB)/10コアGPU/256GB SSD】")
    assert not _is_target("Mac mini MX0D3J/A 2024【Apple M4 Pro(24GB)/14コアGPU/512GB SSD】")
    assert not _is_target("Mac mini MRTR2J/A Late 2018【Core i3(3.6GHz)/8GB/256GB SSD】")
    assert not _is_target("MacBook Pro 2024【Apple M4(24GB)/10コアGPU/512GB SSD】")


def test_parse_memory_and_storage():
    assert _parse_memory("Mac mini 2024【Apple M4(24GB)/512GB SSD】") == 24
    assert _parse_storage("Mac mini 2024【Apple M4(24GB)/512GB SSD】") == 512
    assert _parse_storage("Mac mini 2024【Apple M4(32GB)/1TB SSD】") == 1024


def test_parse_extracts_matching_card():
    html = "<ul>" + _card(
        "Mac mini MU9E3J/A 2024【Apple M4(24GB)/10コアGPU/512GB SSD】",
        "129,800",
        "/items/deskpc/mac/apple/mac_mini_mu9e3j_a_2024/500001",
    ) + _card(
        "Mac mini MRTR2J/A Late 2018【Core i3(3.6GHz)/8GB/256GB SSD】",
        "29,800",
        "/items/deskpc/mac/apple/mac_mini_mrtr2j_a_late_2018/224022",
    ) + "</ul>"

    listings = parse(html)
    assert len(listings) == 1
    l = listings[0]
    assert l.source == "iosys"
    assert l.condition == "used"
    assert l.memory_gb == 24
    assert l.storage_gb == 512
    assert l.price_jpy == 129800
    assert l.sku == "500001"
    assert l.url == "https://iosys.co.jp/items/deskpc/mac/apple/mac_mini_mu9e3j_a_2024/500001"
    assert "中古Bランク" in l.title


def test_parse_deduplicates_same_href():
    card = _card(
        "Mac mini MU9F3J/A 2024【Apple M4(32GB)/10コアGPU/1TB SSD】",
        "169,800",
        "/items/deskpc/mac/apple/mac_mini_mu9f3j_a_2024/500002",
    )
    html = "<ul>" + card + card + "</ul>"
    assert len(parse(html)) == 1
