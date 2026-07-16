from dataclasses import dataclass

from app.core.errors import AppError


@dataclass(frozen=True)
class ParsedTable:
    text: str
    filename: str


class TableParserSkill:
    id = "table_parser"
    version = "1"
    input_type = "tuple[text, filename]"
    output_type = "ParsedTable"
    error_codes = ("learning_analysis_input_invalid",)
    has_side_effects = False
    can_access_workspace = False

    def run(self, value: tuple[str, str]) -> ParsedTable:
        text, filename = value
        if not text.strip():
            raise AppError(
                code="learning_analysis_input_invalid",
                message="The selected table has no indexed text.",
                status_code=422,
            )
        return ParsedTable(text=text, filename=filename)
