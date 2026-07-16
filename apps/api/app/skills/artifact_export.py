"""Side-effect-free artifact serialization shared by API adapters."""

import csv
import io
import json
from dataclasses import dataclass
from typing import Any

from app.core.errors import AppError


@dataclass(frozen=True)
class ExportedArtifact:
    content: str
    media_type: str
    extension: str


class ArtifactExporterSkill:
    id = "artifact_exporter"
    version = "1"
    input_type = "tuple[format, content]"
    output_type = "ExportedArtifact"
    error_codes = ()
    has_side_effects = False
    can_access_workspace = False

    def run(self, value: tuple[str, str]) -> ExportedArtifact:
        artifact_format, content = value
        if artifact_format == "markdown":
            return ExportedArtifact(content, "text/markdown", "md")
        if artifact_format == "text":
            return ExportedArtifact(content, "text/plain", "txt")
        raise AppError(
            code="artifact_export_format_invalid",
            message="不支持的成果导出格式。",
            status_code=422,
            details={"format": artifact_format},
        )

    def run_csv(self, data: dict[str, Any]) -> ExportedArtifact:
        """Export structured artifact data as a predictable two-column CSV."""

        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(("section", "value"))
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value, ensure_ascii=False)
            else:
                serialized = "" if value is None else str(value)
            writer.writerow((key, serialized))
        return ExportedArtifact(output.getvalue(), "text/csv; charset=utf-8", "csv")
