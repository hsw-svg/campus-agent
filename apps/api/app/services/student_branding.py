from __future__ import annotations


_BRAND_REPLACEMENTS = (
    ("deep tutor助手", "AI 学伴"),
    ("deeptutor助手", "AI 学伴"),
    ("deep tutor助教", "AI 学伴"),
    ("deeptutor助教", "AI 学伴"),
    ("deep tutor", "智汇校园"),
    ("deeptutor", "智汇校园"),
)


class StudentBrandStreamFilter:
    """Remove internal provider branding without leaking split stream prefixes."""

    def __init__(self) -> None:
        self._pending = ""

    def feed(self, text: str) -> str:
        self._pending += text
        return self._drain(final=False)

    def finish(self) -> str:
        return self._drain(final=True)

    def _drain(self, *, final: bool) -> str:
        visible: list[str] = []
        while self._pending:
            lowered = self._pending.lower()
            matches = [
                (brand, replacement)
                for brand, replacement in _BRAND_REPLACEMENTS
                if lowered.startswith(brand)
            ]
            longer_prefix_exists = any(
                brand.startswith(lowered)
                for brand, _ in _BRAND_REPLACEMENTS
                if len(brand) > len(lowered)
            )
            if matches and (final or not longer_prefix_exists):
                brand, replacement = max(matches, key=lambda item: len(item[0]))
                visible.append(replacement)
                self._pending = self._pending[len(brand):]
                continue
            if not final and any(brand.startswith(lowered) for brand, _ in _BRAND_REPLACEMENTS):
                break
            visible.append(self._pending[0])
            self._pending = self._pending[1:]
        return "".join(visible)


def normalize_student_visible_text(text: str) -> str:
    stream_filter = StudentBrandStreamFilter()
    return stream_filter.feed(text) + stream_filter.finish()
