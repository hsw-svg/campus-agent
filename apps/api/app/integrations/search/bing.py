"""Bing Web Search v7 adapter with graceful degradation."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchItem:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class SearchResult:
    available: bool
    items: tuple[SearchItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BingSearchProvider:
    api_key: str | None = None
    endpoint: str = "https://api.bing.microsoft.com/v7.0/search"
    timeout_seconds: float = 6.0

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def search(
        self,
        query: str,
        count: int = 5,
        mkt: str = "zh-CN",
    ) -> SearchResult:
        """Return search results or a degraded, empty result on any failure.

        The provider must never raise: callers assume ``available=False`` when
        the key is missing or the upstream endpoint is unreachable.
        """

        if not self.is_configured:
            return SearchResult(available=False, items=())
        try:
            import httpx  # imported lazily to keep module light
        except Exception:  # noqa: BLE001
            return SearchResult(available=False, items=())
        params = {"q": query, "count": count, "mkt": mkt, "textDecorations": "false"}
        headers = {"Ocp-Apim-Subscription-Key": self.api_key or ""}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(self.endpoint, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except Exception:  # noqa: BLE001 - degrade silently
            return SearchResult(available=False, items=())
        items = _parse_items(payload)
        return SearchResult(available=True, items=items)


def _parse_items(payload: dict) -> tuple[SearchItem, ...]:
    web_pages = (payload or {}).get("webPages") or {}
    values = web_pages.get("value") or []
    items: list[SearchItem] = []
    for entry in values:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("name") or "").strip()
        url = str(entry.get("url") or "").strip()
        snippet = str(entry.get("snippet") or "").strip()
        if not title and not url:
            continue
        items.append(SearchItem(title=title, url=url, snippet=snippet))
    return tuple(items)
