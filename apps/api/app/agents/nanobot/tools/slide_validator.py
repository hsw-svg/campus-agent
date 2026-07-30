"""Slide deck validation tool for nanobot integration.

Wraps the existing SlideDeckJsonSkill as a nanobot tool.
"""

from __future__ import annotations

from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.schema import StringSchema, tool_parameters_schema

from app.skills.slide_deck_json import SlideDeckJsonSkill


@tool_parameters(
    tool_parameters_schema(
        json_content=StringSchema("Slide deck JSON content to validate"),
        required=["json_content"],
    )
)
class SlideDeckValidatorTool(Tool):
    """Validate and normalize slide deck JSON structure."""

    name = "slide_deck_validator"
    description = (
        "Validate and normalize a slide deck JSON structure. "
        "Use this to ensure your generated slide deck JSON is valid before returning it."
    )

    def __init__(self) -> None:
        self._json_skill = SlideDeckJsonSkill()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls()

    async def execute(self, **kwargs: Any) -> ToolResult:
        json_content = kwargs.get("json_content", "")

        if not json_content:
            return ToolResult.error("No JSON content provided.")

        try:
            # Validate and normalize
            normalized = self._json_skill.run(json_content)

            # Check quality
            slides = normalized.get("slides", [])
            issues = []

            if len(slides) < 8:
                issues.append(f"Only {len(slides)} slides (recommended: 8+)")

            # Check layout diversity
            layouts = set(s.get("layout") for s in slides)
            if len(layouts) < 3:
                issues.append(f"Only {len(layouts)} different layouts (recommended: 3+)")

            # Check for media suggestions
            has_media = any(s.get("media") for s in slides)
            if not has_media:
                issues.append("No media suggestions found")

            # Check for citations
            has_citations = any(s.get("citations") for s in slides)
            if not has_citations:
                issues.append("No citations found")

            if issues:
                return ToolResult(
                    "Validation passed with warnings:\n"
                    + "\n".join(f"- {issue}" for issue in issues)
                )
            return ToolResult("Validation passed. Slide deck structure is good.")

        except Exception as error:
            return ToolResult.error(f"Validation failed: {error}")
