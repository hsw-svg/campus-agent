"""Bing search tool for nanobot integration.

Wraps the existing BingSearchProvider as a nanobot tool.
"""

from __future__ import annotations

from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.schema import IntegerSchema, StringSchema, tool_parameters_schema

from app.integrations.search.bing import BingSearchProvider


@tool_parameters(
    tool_parameters_schema(
        query=StringSchema("Search query"),
        count=IntegerSchema(5, description="Number of results (1-10)", minimum=1, maximum=10),
        required=["query"],
    )
)
class BingSearchTool(Tool):
    """Search the web using Bing Search API."""

    name = "bing_search"
    description = (
        "Search the web using Bing Search API. Returns titles, URLs, and snippets. "
        "Useful for finding industry cases, job skills, and educational resources."
    )

    def __init__(self, bing_provider: BingSearchProvider) -> None:
        self._bing_provider = bing_provider

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        bing_provider = getattr(ctx, "bing_provider", None)
        if not isinstance(bing_provider, BingSearchProvider):
            raise ValueError("bing_provider is required to create BingSearchTool")
        return cls(bing_provider=bing_provider)

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        count = kwargs.get("count", 5)

        if not self._bing_provider.is_configured:
            return ToolResult.error(
                "Bing search is not configured. Please set BING_SEARCH_API_KEY."
            )

        try:
            result = await self._bing_provider.search(query, count=count)
            if not result.available:
                return ToolResult.error("Bing search is temporarily unavailable.")

            if not result.items:
                return ToolResult(f"No results found for: {query}")

            # Format results
            lines = [f"Search results for: {query}\n"]
            for i, item in enumerate(result.items, 1):
                lines.append(f"{i}. {item.title}")
                lines.append(f"   URL: {item.url}")
                if item.snippet:
                    lines.append(f"   {item.snippet}")
                lines.append("")

            return ToolResult("\n".join(lines))
        except Exception as error:
            return ToolResult.error(f"Search error: {error}")
