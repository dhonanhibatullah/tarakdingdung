import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from tarakdingdung.domain.contracts.scrapper.news_source import NewsSource
from tarakdingdung.domain.models.news import NewsArticle


class HttpNewsSource(NewsSource):
    def __init__(self, client: httpx.AsyncClient, urls: list[str]) -> None:
        self._client = client
        self._urls = urls

    async def fetch(self) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        for url in self._urls:
            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
                articles.extend(self._parse(url, resp.text))
            except Exception:
                continue
        return articles

    def _parse(self, source: str, text: str) -> list[NewsArticle]:
        root = ET.fromstring(text)
        articles: list[NewsArticle] = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            pub_date = item.findtext("pubDate") or ""
            if not title:
                continue
            articles.append(
                NewsArticle(
                    id="",
                    source=source,
                    url=link,
                    title=title,
                    published_ms=self._parse_date(pub_date),
                    raw_text=description,
                )
            )
        return articles

    def _parse_date(self, value: str) -> int:
        try:
            return int(parsedate_to_datetime(value).timestamp() * 1000)
        except Exception:
            return 0
