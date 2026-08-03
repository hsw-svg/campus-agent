# Slide Deck Template Generation

## Scenario: Select and fill a registered PPTX template

### 1. Scope / Trigger

Apply this contract when changing course-iteration `slide_deck` generation, template selection, registered PPTX files, frame manifests, or `format=pptx` export.

The renderer must duplicate registered source slides and edit classified objects. Do not recreate a supplied template from blank layouts, and do not accept model/user-supplied file paths.

Current development templates are `development_only`; they must be replaced before competition submission or external distribution. This status is metadata and is not currently a runtime block.

### 2. Signatures

- Generation entry: `CourseIterationExecutor.execute(request: AgentRequest) -> AgentResult`
- JSON normalization: `SlideDeckJsonSkill.run(value: str | dict) -> dict`
- Export entry: `SlideDeckPptxSkill.run(data: dict) -> ExportedBinaryArtifact`
- HTTP export: `GET /api/artifacts/{artifact_id}/export?format=pptx`
- Template lookup: `get_template(template_id: str | None) -> PptxTemplateSpec`
- Manifest gate: `validate_template_manifest(spec: PptxTemplateSpec) -> None`

No database migration or environment key is required. Final template visuals are download-only; do not add PPTX-to-PNG or screenshot preview behavior under this contract.

### 3. Contracts

`slide_deck.data` keeps the existing topic/audience/objective/slides/sources fields and may add:

```json
{
  "template_id": "ai_tech",
  "template_name": "AI科技",
  "template_selection_source": "explicit|previous|llm|fallback",
  "template_license_scope": "development_only"
}
```

Selection order is executable behavior:

1. An explicit registered template name in the current user message.
2. A valid `template_id` from the previous deck in the same conversation.
3. The current LLM response, constrained by the injected template catalog.
4. `DEFAULT_TEMPLATE_ID` (`ai_tech`).

The model only selects an ID. The backend overwrites name, source, and license metadata from the catalog.

Each manifest owns:

- a local PPTX `file_name` (basename only),
- stable template ID, display name, description, aliases, and license scope,
- reusable source-slide frames,
- logical layouts and item capacity,
- every visible text object's `rewrite`, `delete`, or `keep` classification.

If `slides[0].layout == "title"`, it is the cover. Otherwise the exporter synthesizes exactly one cover. Existing API response and download headers stay unchanged.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Missing/unknown Artifact `template_id` | Use `ai_tech` for backward compatibility |
| Unknown LLM `template_id` | Store `ai_tech` with `template_selection_source=fallback` |
| Explicit registered name | Force that template, regardless of model value |
| Valid previous template and no explicit switch | Preserve previous template |
| Manifest file missing/malformed | `AppError(code="pptx_template_manifest_invalid", status=500)` |
| Manifest source slide/shape missing or text object unclassified | Same manifest error; do not generate a partial deck |
| Clone/render relationship failure | `AppError(code="pptx_template_render_failed", status=500)` |
| Entire chat model unconfigured | Keep existing course-generation failure; do not fabricate content |

Never silently fall back to a blank presentation or one of the old empty theme files.

### 5. Good / Base / Bad Cases

- Good: “使用商业计划书模板生成创业课程课件” forces `business_plan`; export copies registered business source pages and replaces only mapped text.
- Base: A historical `slide_deck` has no template metadata; export uses AI科技 and still produces a valid PPTX.
- Good continuation: “压缩到 6 页” keeps the previous template, while “改用 AI科技” switches it.
- Bad: LLM returns `../../custom.pptx`; catalog validation ignores it and uses the default ID.
- Bad: A template is manually re-saved and shape IDs drift; manifest validation fails before producing a half-filled file.

### 6. Tests Required

- Catalog contains unique IDs, local file names, aliases, and license scope; every template file exists.
- Manifest validation asserts every visible text-bearing object is classified and every source slide/shape exists.
- Executor tests explicit selection, LLM selection, previous-template preservation, explicit switch, and invalid-ID fallback.
- JSON normalization preserves optional `template_id` without changing historical payload behavior.
- Export tests both templates, title/no-title page counts, 16:9 size, valid ZIP, `python-pptx` reopen, absence of source sample text, and absence of empty structural placeholders.
- Frame planning tests that fitting alternatives avoid adjacent repetition.
- API export tests retain PPTX content type and download disposition.

### 7. Wrong vs Correct

#### Wrong

```python
# Model/user data chooses an arbitrary file and blank layouts discard source design.
presentation = Presentation(data["template_path"])
presentation.slides.add_slide(presentation.slide_layouts[1])
```

```python
# Broad clearing can delete brand chrome and still leave structural placeholders.
for shape in slide.shapes:
    if getattr(shape, "has_text_frame", False):
        shape.text = ""
```

#### Correct

```python
template = get_template(data.get("template_id"))
validate_template_manifest(template)
content = render_template_deck(template, data)
```

The manifest classifies exact shape IDs, the renderer clones exact source pages, and each target is rewritten or deleted intentionally while preserving the template's existing formatting.
