"""Side-effect-free artifact serialization shared by API adapters."""

from dataclasses import dataclass


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
        return ExportedArtifact(content, "text/plain", "txt")
