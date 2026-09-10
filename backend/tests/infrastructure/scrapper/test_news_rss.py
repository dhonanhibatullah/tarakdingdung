import httpx

from tarakdingdung.infrastructure.scrapper.news.rss import HttpNewsSource


RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <item>
      <title>Bitcoin rallies</title>
      <link>https://example.com/1</link>
      <pubDate>Tue, 03 Sep 2026 10:00:00 GMT</pubDate>
      <description>BTC up 5%</description>
    </item>
    <item>
      <title>Regulation update</title>
      <link>https://example.com/2</link>
      <pubDate>Wed, 04 Sep 2026 10:00:00 GMT</pubDate>
      <description>New rules</description>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_items():
    source = HttpNewsSource.__new__(HttpNewsSource)
    articles = source._parse("https://example.com/feed", RSS)
    assert len(articles) == 2
    assert articles[0].title == "Bitcoin rallies"
    assert articles[0].url == "https://example.com/1"
    assert articles[0].source == "https://example.com/feed"
    assert articles[0].raw_text == "BTC up 5%"
    assert articles[0].published_ms > 0


async def test_fetch_follows_redirect():
    def handler(request):
        if str(request.url).endswith("/feed/"):
            return httpx.Response(
                308, headers={"location": "/feed"}
            )
        return httpx.Response(
            200, text=RSS, headers={"content-type": "application/rss+xml"}
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    )
    source = HttpNewsSource(client, ["https://example.com/feed/"])
    articles = await source.fetch()
    assert len(articles) == 2
