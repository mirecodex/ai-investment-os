from __future__ import annotations

from investment_os.pipelines.rss import TickerTagger, parse_feed
from investment_os.pipelines.sentiment import score_text
from tests.conftest import NOW

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Contoh Feed</title>
    <item>
      <title>Laba BCA tumbuh dua digit pada kuartal pertama</title>
      <link>https://example.com/a</link>
      <description>&lt;p&gt;Bank Central Asia mencatat laba bersih naik.&lt;/p&gt;</description>
      <pubDate>Mon, 13 Jul 2026 01:00:00 +0000</pubDate>
    </item>
    <item>
      <title>IHSG dibuka menguat</title>
      <link>https://example.com/b</link>
      <description>Indeks naik pada pembukaan.</description>
      <pubDate>tanggal-tidak-valid</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Feed Atom</title>
  <entry>
    <title>Saham Antam tertekan aksi jual asing</title>
    <summary>Harga nikel melemah.</summary>
    <updated>2026-07-12T22:00:00+00:00</updated>
    <link href="https://example.com/c"/>
  </entry>
</feed>
"""


def test_parse_rss_items_with_date_fallback() -> None:
    entries = parse_feed(RSS_SAMPLE, now=NOW)
    assert len(entries) == 2
    title, body, published, link = entries[0]
    assert title.startswith("Laba BCA")
    assert "<p>" not in body
    assert published.isoformat().startswith("2026-07-13")
    assert link == "https://example.com/a"
    assert entries[1][2] == NOW  # unparseable pubDate falls back to now


def test_parse_atom_entries() -> None:
    entries = parse_feed(ATOM_SAMPLE, now=NOW)
    assert len(entries) == 1
    assert entries[0][3] == "https://example.com/c"


def test_tagger_matches_aliases_not_substrings() -> None:
    tagger = TickerTagger(
        {"BBCA": ["BCA", "Bank Central Asia"], "ANTM": ["Antam", "Aneka Tambang"]}
    )
    assert tagger.tag("Laba BCA tumbuh dua digit") == ["BBCA"]
    assert tagger.tag("Saham Antam tertekan") == ["ANTM"]
    assert tagger.tag("Kombinasi ANTM dan Bank Central Asia") == ["BBCA", "ANTM"]
    # "BCA" must not fire inside another word
    assert tagger.tag("publikasi terbaru") == []


def test_sentiment_polarity_and_damping() -> None:
    positive = score_text("Laba naik, kinerja menguat dan tumbuh")
    negative = score_text("Saham anjlok, laba turun akibat tekanan jual")
    neutral = score_text("Rapat umum pemegang saham dijadwalkan pekan depan")

    assert positive > 0.3
    assert negative < -0.3
    assert neutral == 0.0
    # Negation flips polarity: "tidak naik" is not a positive signal.
    assert score_text("Penjualan tidak naik tahun ini") <= 0.0
    assert -1.0 <= negative <= positive <= 1.0
