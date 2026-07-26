"""Web search integrations."""

from app.integrations.search.bing import (
    BingSearchProvider,
    SearchItem,
    SearchResult,
)

__all__ = ("BingSearchProvider", "SearchItem", "SearchResult")
