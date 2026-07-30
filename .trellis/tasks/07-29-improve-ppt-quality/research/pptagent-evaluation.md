# Research: PPTAgent integration evaluation

- **Query**: Evaluate whether `icip-cas/PPTAgent` can be borrowed from or integrated into campus-agent to prevent DeepSeek one-shot 8-12-slide JSON truncation, including the proposed architecture of retaining campus-agent routing and calling PPTAgent directly for PPT intent.
- **Scope**: Mixed internal/external, primary sources only
- **Date**: 2026-07-29
- **PPTAgent revision inspected**: `2419d30b134a71486523e95ded60b32489fd3c61` (`main`)

## Executive conclusion

PPTAgent materially demonstrates the right anti-monolith ideas, but direct adoption is not the smallest reliable fix for campus-agent's observed `finish_reason=length` failure.

The strongest reusable idea is its staged flow: produce/research a manuscript or outline, then generate slides independently or page by page, validate locally, and assemble the final deck. Legacy PPTAgent makes this explicit as one outline call followed by concurrent per-slide calls; DeepPresenter v2 adds research-manuscript and design phases plus context folding. Neither path asks one LLM completion to emit a complete 8-12-slide campus `slide_deck` JSON.

For campus-agent, the smallest reliable design is still a native staged pipeline behind the existing router and executor contract: (1) compact outline, (2) batches of 2-3 page-detail JSON objects, (3) validate and checkpoint each batch, (4) retry only failed/truncated batches, (5) local merge and `SlideDeckJsonSkill`, and (6) existing preview and `SlideDeckPptxSkill`. Borrow the architecture and prompt decomposition, not the runtime.

The user's proposed direct route is technically possible: retain campus-agent routing, detect PPT intent, invoke DeepPresenter's `AgentLoop`, and receive a `.pptx` path. However, PPTAgent returns a binary file path rather than campus-agent's stable semantic JSON artifact. Direct routing therefore requires a new binary-object contract and preview adapter, or a lossy PPTX-to-`slide_deck` conversion. It also adds Linux/WSL, Docker, Node, Chromium/Playwright, MCP processes, model configuration, and workspace lifecycle requirements. It should run as an isolated subprocess/container service, not as an in-process dependency of the current Windows/FastAPI API.

## Sources and files inspected

### PPTAgent primary sources

| File / URL | Description |
|---|---|
| [`README.md`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/README.md) | Current v2 installation, CLI, Docker, platform, model and output guidance |
| [`pyproject.toml`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pyproject.toml) | Python/package dependencies and console entrypoints |
| [`LICENSE`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/LICENSE) | MIT license text |
| [`deeppresenter/main.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/main.py) | `AgentLoop`, stage orchestration, per-session workspace and final output path |
| [`deeppresenter/cli/commands.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/cli/commands.py) | Exact `generate` CLI request construction and output copying |
| [`deeppresenter/utils/typings.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/utils/typings.py) | `InputRequest`, conversion modes and request fields |
| [`deeppresenter/utils/config.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/utils/config.py) | OpenAI-compatible/LiteLLM endpoints, retries, concurrency and context folding |
| [`deeppresenter/config.yaml.example`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/config.yaml.example) | Separate research, design, long-context, optional vision and T2I models |
| [`deeppresenter/agents/env.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/agents/env.py) | MCP/tool processes, Docker workspace mapping and request-local tool state |
| [`deeppresenter/roles/Research.yaml`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/roles/Research.yaml) | Research-to-Markdown manuscript stage |
| [`deeppresenter/roles/Design.yaml`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/roles/Design.yaml) | Page-by-page HTML design and inspect/fix loop |
| [`deeppresenter/roles/PPTAgent.yaml`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/roles/PPTAgent.yaml) | Template-mode manuscript-to-PPT tool workflow |
| [`deeppresenter/utils/constants.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/deeppresenter/utils/constants.py) | Retry, context, MCP timeout, workspace and subagent defaults |
| [`pptagent/pptgen.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pptagent/pptgen.py) | Legacy two-stage outline/per-slide template generation |
| [`pptagent/response/outline.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pptagent/response/outline.py) | Typed outline contract and document indexes |
| [`pptagent/response/pptgen.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pptagent/response/pptgen.py) | Typed per-slide element and layout contracts |
| [`pptagent/roles/planner.yaml`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pptagent/roles/planner.yaml) | Compact outline prompt |
| [`pptagent/roles/editor.yaml`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pptagent/roles/editor.yaml) | One-slide element-generation prompt |
| [`pptagent/llms.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pptagent/llms.py) | OpenAI-compatible sync/async model wrapper, image inputs, structured parsing |
| [`pptagent/litellm.py`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pptagent/litellm.py) | Optional LiteLLM provider adapter |
| [`pptagent/DOC.md`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/pptagent/DOC.md) | Legacy requirements, MCP tools and programmatic-generation pointer |
| [`docker-compose.yml`](https://github.com/icip-cas/PPTAgent/blob/2419d30b134a71486523e95ded60b32489fd3c61/docker-compose.yml) | Host/sandbox deployment topology and workspace mounts |
| [Release v2.0.0](https://github.com/icip-cas/PPTAgent/releases/tag/v2.0.0) | DeepPresenter integration and new runtime features |
| [Release v0.1.0](https://github.com/icip-cas/PPTAgent/releases/tag/v0.1.0) | Async ordering, retries, template induction and per-slide generation history |
| [Repository metadata](https://api.github.com/repos/icip-cas/PPTAgent) | MIT declaration and project metadata |

### Campus-agent files

| File | Description |
|---|---|
| `.trellis/tasks/07-29-improve-ppt-quality/prd.md:9-75` | Confirmed length truncation and stable-contract requirements |
| `apps/api/app/agents/router.py:264-267` | Existing explicit PPT intent routing |
| `apps/api/app/agents/executors/course_iteration_v2.py:59-101` | Current PPT intent branch and stable artifact normalization |
| `apps/api/app/agents/nanobot/runner.py:78-141` | Current monolithic full-deck JSON prompt |
| `apps/api/app/agents/nanobot/runner.py:194-224` | JSON parse and artifact construction |
| `apps/api/app/skills/slide_deck_json.py:69-122` | Stable semantic slide-deck normalization contract |
| `apps/api/app/skills/slide_deck_pptx.py:132-223` | Existing `python-pptx` renderer returning bytes |
| `apps/api/app/api/artifacts.py:61-99` | Existing export endpoint regenerates PPTX from artifact JSON |
| `apps/api/app/artifacts/models.py:12-40` | Artifact persists text and JSON only, no binary locator |
| `apps/api/app/services/conversations.py:394-437` | Artifact persistence and SSE artifact event contract |
| `apps/web/src/components/SlideDeckPreview.tsx:56-64` | Frontend's semantic `SlideDeckData` contract |
| `apps/web/src/components/SlideDeckPreview.tsx:139-184` | Preview reads `artifact.data.slides`; download delegates to export endpoint |
| `apps/api/app/integrations/storage/base.py:1-11` | Existing byte-object storage protocol that could store generated PPTX |

## 1. PPTAgent architectures and actual data flow

The repository now contains two related systems.

### DeepPresenter v2, the current CLI path

The installed `pptagent` console command is `deeppresenter.cli:main` (`pyproject.toml:109-111`), not the legacy `pptagent.pptgen.PPTAgent` class.

`pptagent generate` constructs `InputRequest` and runs `AgentLoop` (`deeppresenter/cli/commands.py:310-419`). The actual flow in `AgentLoop.run` is:

1. Create or receive a unique workspace and copy attachments into it (`deeppresenter/main.py:21-41`, `64-67`).
2. Optionally run `Planner` and persist an outline path (`86-110`).
3. Run `Research` to collect/parse sources and write a Markdown manuscript (`112-139`). The manuscript prompt requires `---` between pages and local image paths (`deeppresenter/roles/Research.yaml:14-23`).
4. Render using one of two branches:
   - `convert_type=pptagent`: template-oriented `PPTAgent` repeatedly invokes MCP tools until they return a `.pptx` path (`deeppresenter/main.py:141-168`; `deeppresenter/agents/pptagent.py:17-29`).
   - Default `convert_type=deeppresenter`: `Design` generates independent HTML slide files, calls `inspect_slide` after each, then Node/Playwright conversion assembles PPTX (`deeppresenter/main.py:169-224`; `deeppresenter/roles/Design.yaml:11-17`). It can fall back to PDF if HTML-to-PPTX fails (`main.py:195-218`).
5. Persist `intermediate_output.json` containing outline/manuscript/HTML/PPTX/final paths (`main.py:226-233`).

The default renderer is therefore HTML/CSS -> Node `html2pptx` -> PPTX, with Playwright also producing PDF. Template mode uses the PPTAgent MCP server and its custom PowerPoint editing model.

### Legacy PPTAgent two-stage path

The legacy class described by the paper is `pptagent.pptgen.PPTAgent`:

1. A reference `.pptx` is analyzed (template induction) into functional types, layout schemas and example slides.
2. `generate_pres` creates one typed `Outline` from a structured source `Document` if no outline was supplied (`pptagent/pptgen.py:140-183`, `239-256`).
3. It adds opening, TOC, section and ending functional slides according to layouts found in the reference deck (`267-318`).
4. It launches one `generate_slide` coroutine per outline item and optionally limits concurrency via `max_at_once` (`198-211`).
5. Each slide independently retrieves only its indexed document subsections/images, organizes key points, selects a reference layout, emits typed element content, validates/rewrites lengths, then asks a coder model for edit API calls (`392-529`).
6. Local edit APIs mutate cloned template slides. Failed content/edit actions retry at slide level (`507-570`). Successful slides are assembled into a `Presentation` (`213-237`).

This is a typed outline + per-slide generation architecture, not full-deck JSON generation.

## 2. How it avoids monolithic output

PPTAgent avoids the campus failure mode in several concrete ways:

- The legacy planner outputs only `purpose`, `topic`, document indexes and image paths per slide, not full slide prose (`pptagent/response/outline.py:30-98`).
- Every legacy slide gets separate content-organization, layout-selection, element-generation and edit calls (`pptagent/pptgen.py:392-529`). `asyncio.gather` assembles local results after those calls (`203-237`).
- Each per-slide output is constrained to the selected template's element names (`pptagent/response/pptgen.py:6-33`) and then locally validated.
- DeepPresenter first writes a Markdown manuscript and then generates slide files/tools page by page. The design prompt explicitly says “Generate only one slide at a time” and inspect/fix it before proceeding (`deeppresenter/roles/Design.yaml:13-17`). Multi-agent mode can delegate independent slides after defining global CSS (`deeppresenter/utils/constants.py:101-110`).
- DeepPresenter context folding summarizes agent context when configured, avoiding indefinitely growing chat history (`deeppresenter/utils/config.py:403-443`).

Important limitation: DeepPresenter's research agent may still write the entire Markdown manuscript in an agent session. Its tooling and context folding reduce context pressure, but the source does not establish a hard guarantee that manuscript creation itself is emitted in bounded page batches. Legacy PPTAgent provides the clearest hard decomposition because each slide is a separate model call.

## 3. Runtime and provider assumptions

### Models and APIs

- Both legacy and current code support OpenAI-compatible `base_url`, `api_key`, and model names (`pptagent/llms.py:23-31`; `deeppresenter/config.yaml.example:6-19`). LiteLLM is optional (`pptagent[litellm]`).
- Legacy code explicitly special-cases model identifiers containing `deepseek` by combining the system text into the user message (`pptagent/llms.py:170-175`). A DeepSeek OpenAI-compatible endpoint is therefore structurally usable.
- Current DeepPresenter config expects distinct `research_agent`, `design_agent`, and `long_context_model` endpoints, plus optional `vision_model` and `t2i_model` (`deeppresenter/utils/config.py:418-427`). Reusing one DeepSeek chat endpoint for all required roles is syntactically possible, but the repository's example uses different model families and the README strongly recommends its fine-tuned DeepPresenter model (`README.md:50-55`).
- Tool calling is central to DeepPresenter: agents must call MCP/sandbox/finalize/inspection tools. Provider compatibility therefore requires reliable OpenAI-style tool calls, not only plain chat completion.
- Vision is optional at the configuration level. Heavy rendered-slide reflection requires a multimodal design model; without one, reflection is textual only (`deeppresenter/main.py:58-61`). Legacy reference-template induction and image understanding recommend a VLM (`pptagent/DOC.md:40-45`).

### Search and external services

- DeepPresenter's primary-source configuration offers Tavily and SerpAPI search through MCP, optional MinerU for PDF parsing, and optional T2I (`README.md:84-93`; `deeppresenter/cli/commands.py:233-258`).
- It does not expose a direct adapter for campus-agent's `BingSearchProvider`. Preserving Bing requires either supplying campus research results as an attachment/manuscript or implementing/registering an MCP tool compatible with DeepPresenter's `AgentEnv`.
- Offline mode removes network tools (`deeppresenter/utils/typings.py`, `AgentEnv`; `README.md:93`).

### System dependencies

- Current README explicitly states Windows is unsupported and directs Windows users to WSL (`README.md:70-73`). This directly conflicts with the current native Windows development environment.
- Python 3.11+ matches campus-agent, but PPTAgent's package introduces a large dependency graph: Docker SDK, Gradio, FastAPI “all”, MCP/FastMCP, OpenAI, Playwright, ModelScope, image/PDF parsing, `numpy<2`, and `pptagent-pptx` (`pyproject.toml:31-89`).
- Source installation also requires Chromium/Playwright, Node packages under `deeppresenter/html2pptx`, model assets, and sandbox/host Docker images (`README.md:141-166`).
- Legacy docs list LibreOffice, Chrome, poppler-utils and NodeJS (`pptagent/DOC.md:47-55`). LibreOffice/soffice is used for PPTX image rendering in legacy utilities. DeepPresenter's default HTML path primarily uses Node/Chromium/Playwright and Docker sandbox.
- Template mode requires a selected/bundled reference template and induced layout data. Default free-form design can work without a reference PPTX but uses HTML/CSS generation and browser conversion.

### Output

The public CLI and Python orchestration return a path to `.pptx` (or, on conversion failure in default mode, `.pdf`). They do not return campus-agent's slide JSON, notes/citations/media schema, or PPTX bytes directly.

## 4. License implications

PPTAgent is MIT licensed (`LICENSE:1-21`).

- **Direct dependency**: allowed for commercial/private use and modification. Distribution must retain the copyright and MIT permission notice for PPTAgent portions. Transitive dependencies and models/services have their own licenses and must be checked separately; the MIT file does not relicense them.
- **Vendoring/copying modules or prompts**: allowed, but copied substantial portions must retain the MIT copyright and permission notice. Vendoring also transfers maintenance burden for a rapidly changing agent/tool stack.
- **Borrowing architecture only**: the abstract staged idea (outline -> independent slides -> validation -> assembly) is not a copied code artifact and does not require source-code attribution. Exact prompt/code copying should still carry the MIT notice.
- **Model weights/templates/assets**: their licenses are not established by the repository's root MIT source license. A production decision must inspect each selected model/template/asset license separately.

## 5. Reusable concepts and coupling

| Concept/module | Reuse value | Coupling |
|---|---|---|
| Typed outline (`Outline`, `OutlineItem`) | High: compact, validated first stage | Low conceptually; source model is coupled to `Document` section indexes and media paths |
| One-slide editor schema (`EditorOutput`) | High: bounded response per slide | Medium: element names come from induced template schemas |
| Concurrent per-slide generation with semaphore | High: bounded calls and controllable throughput | Low conceptually; legacy implementation mutates instance state and template objects |
| Per-slide targeted retry | High: retries only the failed unit | Low conceptually; exact retry history is tied to PPTAgent `Agent` roles |
| Functional slide insertion | Medium: opening/TOC/section/ending rules | Medium: detection depends on reference-layout induction |
| Layout selection and content-length validation | Medium/high for quality | High: tied to custom `Presentation`, `Layout`, template schemas, VLM-derived induction and `pptagent-pptx` |
| Edit API / `CodeExecutor` | Low for campus's current renderer | High: generated code actions target PPTAgent's custom slide object model |
| DeepPresenter research manuscript | High as an architectural pattern | High implementation coupling to MCP, sandbox, tools and workspace files |
| HTML per-slide design + inspect/fix | High visual ceiling | High: Node, Playwright, sandbox, multimodal inspection and custom converter |
| Context folding | Useful for long agent sessions | Medium/high: implemented inside DeepPresenter's agent runtime, not as a standalone utility |

The directly portable pieces are therefore algorithms/contracts, not drop-in isolated modules.

## 6. Compatibility with campus-agent

### Stable `slide_deck` JSON and frontend preview

Campus persists one semantic `slide_deck` artifact with `topic`, metadata, `slides[]`, citations/media/sources. The frontend reads `artifact.data.slides` directly (`SlideDeckPreview.tsx:56-64`, `139-166`). PPTAgent only returns files and internal workspace intermediates. There is no compatible returned JSON.

A direct PPTAgent result cannot be placed into the current artifact unchanged:

- `Artifact.data` must be JSON and `content` must be text (`artifacts/models.py:30-35`).
- SSE emits that JSON to the frontend (`services/conversations.py:394-437`).
- The current PPTX download endpoint ignores stored binary files and re-renders `artifact.data` through `SlideDeckPptxSkill` (`api/artifacts.py:69-85`).

### NanobotRunner and DeepSeek

PPTAgent would bypass `NanobotRunner` for PPT intent. That is compatible with keeping campus-agent's top-level routing but not with the PRD decision that nanobot remains the PPT runtime. It duplicates provider, tool, retry and runtime configuration.

PPTAgent's provider layer can point to DeepSeek's OpenAI-compatible endpoint. However, direct DeepPresenter quality and completion depend on tool calling, long-context research, and potentially vision/design behavior beyond campus's current plain DeepSeek JSON generation. Compatibility must be established by an integration test; it is not guaranteed by endpoint shape alone.

### Bing

PPTAgent's current search stack is MCP + Tavily/SerpAPI, not campus Bing. Calling it directly means Bing is not used unless campus pre-research is injected into attachments/manuscript or a Bing MCP adapter is added.

### Existing `python-pptx` renderer

PPTAgent replaces the renderer and produces its own PPTX. Keeping `SlideDeckPptxSkill` would discard PPTAgent's visual output and regenerate a simpler deck from JSON, defeating direct integration. A direct integration should serve PPTAgent's binary instead, while the native staged option keeps the current renderer unchanged.

## 7. Explicit evaluation of “keep campus routing, call PPTAgent directly”

### Exact callable entrypoints

**CLI, current supported path**

```bash
uvx pptagent generate "<instruction>" \
  -f <attachment> \
  -p "8-12" \
  -a "16:9" \
  -l zh \
  -o <absolute-output>.pptx
```

Entrypoint: `pptagent = deeppresenter.cli:main`; subcommand: `deeppresenter.cli.commands.generate` (`pyproject.toml:109-111`, `cli/__init__.py:15-28`, `cli/commands.py:310-336`). Inputs are instruction, zero or more attachment paths, page count/range string, aspect ratio, language, planner flag and required output path. Success copies the generated file and returns/prints the requested absolute output path (`commands.py:394-419`). Process exit is nonzero on failure.

**Python, current orchestration API**

```python
config = DeepPresenterConfig.load_from_file(config_path)
config.mcp_config_file = mcp_path
loop = AgentLoop(
    config=config,
    session_id=run_id,
    workspace=isolated_workspace,
    language="zh",
)
request = InputRequest(
    instruction=prompt,
    attachments=[...],
    num_pages="8-12",
    powerpoint_type="16:9",
    convert_type="deeppresenter",  # or "pptagent" for template mode
    enable_planner=False,
)
final_path = None
async for event in loop.run(request):
    if isinstance(event, (str, Path)):
        final_path = Path(event)
```

The final yielded path is recorded in `loop.intermediate_output["final"]`; intermediate messages are `ChatMessage` objects. There is no stable function that simply returns `bytes` or a semantic deck object (`deeppresenter/main.py:43-57`, `220-224`).

**Legacy Python API**

`pptagent.pptgen.PPTAgent(...).set_reference(...).generate_pres(document, num_slides, max_at_once=...)` returns `(Presentation, history)` (`pptagent/pptgen.py:140-166`). It requires a parsed source `Document`, reference `Presentation`, induced layout JSON, language and vision models. Callers then save the returned custom `Presentation`. It is not a direct prompt-to-PPT entrypoint.

**Service/MCP entrypoints**

- `pptagent serve` starts the CLI's local inference service, not a documented prompt-to-PPT REST contract (`README.md:124-130`).
- `python webui.py` exposes a Gradio UI on 7861, not a stable campus-facing generation API (`README.md:168-199`; `webui.py:418-436`).
- `pptagent-mcp = pptagent.mcp_server:main` exposes low-level template/slide tools (`list_templates`, `create_slide`, `write_slide`, `generate_slide`, `save_generated_slides`), not one high-level prompt-to-PPT RPC (`pptagent/DOC.md:66-109`).

### Concurrency and state isolation

- `AgentLoop` creates a UUID-derived workspace by default and writes all attachments/intermediates/history there (`deeppresenter/main.py:24-39`, `64-67`). Campus should pass its own unique run ID and workspace per request.
- `AgentEnv` passes `WORKSPACE`, `HOST_WORKSPACE`, and `WORKSPACE_ID` to MCP processes rather than globally changing workspace environment variables (`deeppresenter/agents/env.py:72-97`). This supports request isolation.
- Legacy slide generation runs concurrently and accepts `max_at_once`; model endpoints also hold semaphores (`pptagent/pptgen.py:198-211`; `deeppresenter/utils/config.py:215-226`).
- DeepPresenter agents and tool histories are loop/request instances. The Gradio app creates a user session/loop per session.
- Remaining shared-process concerns include package/global config files, package tool cache, global logging setup, Docker daemon/sandbox resources and class-global Playwright lifecycle. CLI calls `PlaywrightConverter.shutdown()` in a `finally` block (`cli/commands.py:423-425`), which is unsuitable for unrelated concurrent in-process runs sharing that converter.
- `intermediate_output.json` records progress paths, but no public resume API reconstructs an interrupted `AgentLoop` from those checkpoints. Legacy `asyncio.gather` also has no durable per-slide resume. Workspace outputs aid diagnosis, not guaranteed restart.

### In-process versus subprocess/service

**Recommendation for direct adoption: subprocess/container service.**

Reasons grounded in source/runtime requirements:

- Native Windows is explicitly unsupported.
- The runtime expects Linux/WSL, Docker sandbox access, MCP child processes, Node, Chromium/Playwright and model/config files.
- Its dependency graph is much larger than campus API's and includes overlapping FastAPI/OpenAI/httpx/python-pptx concerns.
- Generation is long-running and resource-heavy; cancellation, timeouts, process cleanup and concurrency quotas are easier to enforce outside the FastAPI process.
- Shared Playwright/config/logging/tool-cache lifecycle creates avoidable cross-request risk in-process.

A production wrapper should launch either a pinned Linux container per job or a separately deployed worker service with a queue. A subprocess invoking `pptagent generate` is the smallest proof of concept. The Gradio UI is not the service API to integrate. An in-process `AgentLoop` adapter is callable, but should be limited to controlled Linux experiments, not the current native Windows API deployment.

### Required campus adapters

A direct integration needs all of the following:

1. **Request adapter**: map `AgentRequest.content`, selected attachments, language, 8-12 page range and optional template/aspect ratio into `InputRequest` or CLI arguments. Materialize campus attachment bytes as run-local files.
2. **Provider/config adapter**: create pinned `config.yaml` and `mcp.json`; map DeepSeek base URL/key/model to all required model roles; decide vision/T2I providers; disable or configure Tavily/Serp/MinerU. Bing cannot be injected without another adapter.
3. **Job/workspace adapter**: unique directory per agent run, Linux/container path translation, deadline/cancellation, bounded concurrency, log capture, cleanup and retention.
4. **Output adapter**: verify final suffix is `.pptx` rather than fallback `.pdf`, validate/open the file, read bytes and put them into campus `ObjectStorage` under a run/artifact-scoped key.
5. **Artifact contract extension**: add a JSON-safe binary locator and metadata (storage key, MIME type, size, optional checksum) because current artifacts cannot persist PPTX bytes.
6. **Preview adapter**: choose one of two incompatible approaches:
   - Preserve current frontend semantic preview by parsing PPTX text/notes/layout into a synthetic `slide_deck` JSON. This is lossy: arbitrary PPTAgent HTML/template designs, citations, source semantics, media and positioning do not map to five campus layouts.
   - Preserve PPTAgent fidelity by generating/storing per-slide preview images and extending the frontend to display them. This changes the existing artifact and frontend contract.
7. **Download adapter**: for PPTAgent-backed artifacts, stream the stored PPTX bytes instead of calling `SlideDeckPptxSkill`; retain current re-rendering for native JSON-backed artifacts.
8. **Fallback adapter**: if the worker is unavailable, emits PDF, times out or returns invalid PPTX, fall back to the native staged JSON pipeline without persisting partial normal artifacts.

Thus a direct call can preserve the user-facing ability to preview/download, but it cannot preserve the current implementation contracts without extending them.

## 8. Option comparison

| Option | Indicative implementation | Risk | Fit for length truncation |
|---|---:|---|---|
| Direct DeepPresenter/PPTAgent integration | 3-6 engineer-weeks for a production worker, config/secrets, binary storage, API/artifact/frontend adapters, cancellation/observability and deployment; 3-7 days for a non-production CLI proof of concept | High: platform/runtime footprint, model/tool compatibility, output-contract mismatch, no documented resumable high-level service API | Avoids one-shot JSON, but solves much more than the observed failure and introduces new failure modes |
| Selectively port architecture/algorithms | 4-8 engineer-days for outline/batch contracts, orchestrator, retries/checkpoints, merge and focused tests; visual quality work is separate | Low/medium: stays inside existing provider/artifact/render paths | Directly addresses `finish_reason=length` with bounded completions and targeted retries |
| Do not adopt and keep current one-shot path | 0 immediate; perhaps 1-2 days for token-limit tweaks | High operational failure remains | Does not reliably fix truncation; larger token limits only move the boundary |

Estimates assume the current campus code and one backend engineer familiar with it; they are comparative, not commitments.

## 9. Smallest reliable design for campus-agent

Retain campus routing and the stable artifact contract, but replace the monolithic prompt inside the PPT executor with a small native orchestration layer:

1. **Outline stage**: one bounded structured response containing deck metadata plus exactly 8-12 lightweight slide plans: `index`, `teaching_role`, `title`, intended layout, source IDs/search queries and content budget. No notes, bullet prose, citations or media details.
2. **Research stage**: reuse campus Bing once before page generation, normalize results into a bounded source catalog with stable IDs. Do not let every batch independently search the same topic.
3. **Page stage**: generate 2 slides per call by default (at most 3 for simple slides), returning only `slides[]`. Include the global outline, relevant source subset and preceding/following slide summaries, not the growing full JSON deck.
4. **Validation stage**: validate every batch immediately with a stage-specific Pydantic/JSON contract, then normalize each slide. Check expected indexes, title/content presence, allowed layouts, citation IDs and local content-size budgets.
5. **Retry behavior**: retry a failed batch once with the parse error, expected indexes and the truncated/raw response. On `finish_reason=length`, halve the batch to one slide and retry. Never restart already valid batches.
6. **Checkpointing**: store internal run-state under the agent run/workspace, keyed by input hash, mode, outline revision and batch range. Persist outline, source catalog, accepted slide batches, attempts and status atomically. Do not create a normal `slide_deck` artifact until all required batches merge and pass final validation.
7. **Merge**: locally sort/deduplicate indexes, merge sources and context signals, then run the existing `SlideDeckJsonSkill`; render Markdown and persist the existing `AgentArtifact` exactly as today.
8. **Mode behavior**: keep ReAct/Plan-and-Solve/Reflection as strategy flags. ReAct affects research/tool use; plan-and-solve strengthens outline planning; reflection performs a compact post-merge defect list and regenerates only named slides, not the full deck.
9. **Fallback**: if one batch remains unavailable after targeted retry, fail the run with a retryable error and preserve internal checkpoints. Do not expose a silently incomplete normal artifact. An explicit product decision could later permit partial decks, but that is outside the current requirement.
10. **Concurrency**: initially generate batches sequentially or with concurrency 2 to respect DeepSeek rate/time limits and preserve narrative coherence. Parallel batches are possible because the outline is immutable, but bounded concurrency and deterministic merge are required.

This design directly implements the most relevant PPTAgent lesson while keeping `NanobotRunner`, DeepSeek, Bing, `SlideDeckJsonSkill`, `python-pptx`, SSE, frontend preview and downloads intact.

## Caveats / not found

- No primary-source high-level REST API was found that accepts a prompt and returns PPTX bytes. The documented server is Gradio; the MCP server exposes low-level slide tools.
- No public resume-from-`intermediate_output.json` API was found. Intermediate files are persisted, but automatic durable restart is not established.
- No PPTAgent-native `slide_deck` JSON exporter matching campus-agent was found.
- No campus Bing integration was found in PPTAgent.
- The direct DeepSeek + DeepPresenter combination was not executed because it requires credentials, onboarding/model configuration, Linux/WSL, Docker sandbox, Node/Chromium and external services. Source compatibility does not prove output quality.
- Dependency and model/template license review beyond PPTAgent's root MIT license was not completed; each chosen transitive artifact must be reviewed before distribution.
