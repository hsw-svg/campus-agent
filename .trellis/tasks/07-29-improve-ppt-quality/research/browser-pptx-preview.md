# Research: Browser-Native PPTX Preview (Remove LibreOffice)

- **Query**: Evaluate removing LibreOffice entirely and previewing PPTX directly in React/Vite browser
- **Scope**: Mixed internal/external, primary sources only
- **Date**: 2026-07-29

## Current Architecture (LibreOffice Path)

The current implementation uses a server-side rendering pipeline:

1. `SlideDeckPptxSkill` generates PPTX bytes via `python-pptx`
2. `PptxPreviewRenderer` (apps/api/app/integrations/presentation_renderer.py) converts PPTX to PDF via LibreOffice headless mode, then rasterizes PDF pages to PNG via PyMuPDF
3. PNG previews are stored in ObjectStorage and served via authenticated API endpoints
4. Frontend `SlideDeckPreview.tsx` fetches PNG blobs and displays them

**Key files involved**:
- `apps/api/app/integrations/presentation_renderer.py` — LibreOffice + PyMuPDF renderer
- `apps/api/app/services/artifact_presentations.py` — orchestrates PPTX generation, storage, rendering
- `apps/api/app/api/artifacts.py` — preview manifest/page endpoints
- `apps/web/src/components/SlideDeckPreview.tsx` — frontend preview component
- `infra/docker/api.Dockerfile` — installs libreoffice-impress, libreoffice-core, fonts
- `docker-compose.yml` — PPTX_CONVERTER_PATH, PPTX_CONVERSION_TIMEOUT_SECONDS, PPTX_PREVIEW_DPI env vars
- `apps/api/app/core/config.py` — Settings with pptx_converter_path, pptx_conversion_timeout_seconds, pptx_preview_dpi

## Option 1: Browser-Native PPTX Rendering Libraries

### 1A. @aiden0z/pptx-renderer (v1.2.4)

- **npm**: @aiden0z/pptx-renderer
- **License**: Apache-2.0
- **Last published**: 2026-07-10 (2 weeks ago, actively maintained)
- **Size**: 2.6 MB unpackaged
- **Deps**: jszip ^3.10.1, echarts ^6.0.0
- **Optional**: pdfjs-dist (for SmartArt/EMF files with embedded PDF fallback)
- **Browser support**: Browser-only runtime, Node.js 20+ for development

**Features**:
- High-fidelity browser-native PPTX renderer
- Parses Office Open XML (.pptx) and renders slides as HTML/SVG DOM
- Supports: shapes, text, images, tables, charts, SmartArt, groups, backgrounds, gradients, pattern fills, full OOXML color pipeline
- 452+ visual regression test cases against PowerPoint ground truth
- Windowed rendering for large decks with lazy slide parsing and media decoding
- TypeScript-first

**API**:
```typescript
import { PptxViewer, RECOMMENDED_ZIP_LIMITS } from '@aiden0z/pptx-renderer';
const viewer = await PptxViewer.open(await resp.arrayBuffer(), container, {
  zipLimits: RECOMMENDED_ZIP_LIMITS,
  listOptions: { windowed: true },
});
```

**Evaluation**: This is the strongest candidate. Actively maintained, Apache-2.0 licensed, high-fidelity rendering with visual regression tests. Covers the vast majority of real-world PowerPoint content. Bundle includes ECharts for chart rendering.

### 1B. pptx-react-viewer (v2.6.0)

- **npm**: pptx-react-viewer
- **License**: Apache-2.0
- **Last published**: 2026-07-27 (yesterday, actively maintained)
- **Size**: 25.3 MB unpackaged (large)
- **Deps**: clsx, dompurify, html2canvas-pro, pptx-viewer-mcp, tailwind-merge
- **Optional deps**: three (3D models), yjs/y-websocket/y-webrtc (real-time collaboration)

**Features**:
- Drop-in React component for viewing/editing PPTX
- HTML/CSS rendering (not canvas), text is selectable and screen-reader accessible
- 16 element types: shapes, text, images, tables, 23 chart types, SmartArt, connectors, media, ink, OLE, 3D models
- Editing: insert/move/resize/delete elements, edit text inline
- Present: fullscreen slideshow with 40+ animations, 46 transitions, speaker notes
- Export: PNG/JPEG/SVG/PDF/GIF/video, save-as PPTX
- Real-time collaboration via Yjs
- Print, Annotate, Find & Replace, Accessibility features

**API**:
```tsx
import { PowerPointViewer } from 'pptx-react-viewer';
import 'pptx-react-viewer/styles';
<PowerPointViewer content={uint8Array} canEdit />
```

**Evaluation**: Very feature-rich but 25.3 MB is large. The editing capabilities exceed what's needed for preview-only. The React component API is convenient but adds many optional dependencies. More suitable if editing is needed in the future.

### 1C. pptx-viewer-core (v2.0.7)

- **npm**: pptx-viewer-core
- **License**: Apache-2.0
- **Last published**: 2026-07-26 (yesterday)
- **Size**: 12.2 MB unpackaged
- **Deps**: emf-converter, fast-xml-parser, jszip, mtx-decompressor

**Features**:
- Framework-agnostic TypeScript SDK (engine for pptx-react-viewer)
- Parse, edit, serialize, and convert .pptx files
- CLI tool available

**Evaluation**: This is the core engine used by pptx-react-viewer. Can be used standalone for framework-agnostic rendering. Smaller footprint than the full React wrapper.

### 1D. pptx-preview (v1.0.7)

- **npm**: pptx-preview
- **License**: ISC (but source code is NOT open; paid source access)
- **Last published**: 2025-10-17 (9 months ago)
- **Size**: 1.8 MB unpackaged
- **Deps**: jszip, lodash, tslib, uuid, echarts

**Features**:
- Pure frontend PPTX preview library
- Chinese documentation (maintainer is Chinese)
- Supports npm and ES Module import

**API**:
```javascript
import { init } from 'pptx-preview';
let pptxViewer = init(document.getElementById('pptx-wrapper'), { width: 960, height: 540 });
pptxViewer.preview(arrayBuffer);
```

**Evaluation**: Source code is not open (paid access). This is a significant risk for production use — cannot inspect, debug, or contribute fixes. Last published 9 months ago. Not recommended.

### 1E. pptxtojson (v2.1.0)

- **npm**: pptxtojson
- **License**: MIT
- **Last published**: 2026-07-19 (1 week ago)
- **Size**: 7.0 MB unpackaged
- **Deps**: jszip, tinycolor2, txml

**Features**:
- Parsing only (converts PPTX to JSON structure)
- Does NOT render — this is a parser, not a viewer

**Evaluation**: Useful as a parser component but requires building a custom renderer on top. Not a complete solution.

### 1F. pptxgenjs (v4.0.1)

- **npm**: pptxgenjs
- **License**: MIT
- **Last published**: 2025-06-26 (1 year ago)
- **Size**: 2.6 MB unpackaged

**Features**:
- Create/generate PPTX files (generation only, not parsing/rendering)

**Evaluation**: This is for creating presentations, not viewing them. Not relevant for preview.

## Option 2: Microsoft Office Web Viewer / Google Viewer

### Microsoft Office Online Viewer (view.officeapps.live.com)

**Constraints**:
- Requires a publicly accessible URL — private/authenticated URLs won't work
- The file must be accessible from Microsoft's servers
- Cannot be used for workspace-private artifacts without exposing them publicly
- CORS restrictions — the viewer is an iframe that loads from Microsoft's domain
- Availability depends on Microsoft's service — no SLA for free tier
- Rate limiting and potential blocking for high-volume use

**Evaluation**: NOT acceptable for workspace-private artifacts. The requirement is that preview meaningfully matches downloaded PPTX, and the artifacts are private workspace data. Exposing them publicly is a security violation.

### Google Docs Viewer (docs.google.com/gview)

**Constraints**:
- Same public URL requirement as Microsoft
- Requires Google account for some features
- Cannot be used for private/authenticated content
- The viewer adds Google branding and UI
- Limited control over rendering fidelity
- Rate limiting

**Evaluation**: NOT acceptable for the same reasons as Microsoft viewer. Private workspace data cannot be exposed to third-party services.

## Option 3: Non-LibreOffice Server Alternatives

### OnlyOffice Document Server

**Description**: Self-hosted document editing and viewing server. Can render PPTX in browser via its own JavaScript editor.

**Constraints**:
- Requires running a separate Docker container (onlyoffice/documentserver)
- Heavy resource usage (Node.js, PostgreSQL, Redis, RabbitMQ optional)
- The Document Server API requires integration work
- License: AGPL v3 for community edition — requires open-sourcing modifications or purchasing commercial license
- Adds significant operational complexity

**Evaluation**: Overkill for preview-only use. Adds more server complexity than LibreOffice, not less.

### Collabora Online

**Description**: LibreOffice-based online office suite. Essentially runs LibreOffice in a container and streams the UI to the browser.

**Constraints**:
- Still uses LibreOffice under the hood
- Requires Docker container and WOPI protocol integration
- More complex than direct LibreOffice usage
- License: MPL 2.0

**Evaluation**: Does not actually remove LibreOffice — just wraps it in a more complex architecture. Contradicts the requirement.

### Commercial SDKs (Aspose, GroupDocs)

**Description**: Commercial libraries for PPTX rendering. Aspose.Slides for Java/.NET can render PPTX to images or HTML.

**Constraints**:
- Expensive licensing (thousands of dollars per year)
- Requires Java or .NET runtime
- Not compatible with the current Python/Node.js stack

**Evaluation**: Not practical for this project due to cost and runtime requirements.

## Option 4: Generation-Controlled Alternative

### Concept

Since `SlideDeckPptxSkill` generates PPTX via `python-pptx`, and the semantic slide deck JSON is the authoritative source, generate a deterministic preview representation at the same time as PPTX generation.

**Approach A**: Generate HTML/CSS from the same semantic JSON
- Use the existing `Slide` interface (layout, title, bullets, media, etc.) to render HTML/CSS in the frontend
- This is already partially implemented in `SlideDeckPreview.tsx` as the `SlideBody` component for non-authoritative artifacts
- The JSON/CSS preview is already the fallback for legacy artifacts

**Approach B**: Parse PPTX in the browser using @aiden0z/pptx-renderer
- Fetch the stored PPTX bytes from the server
- Parse and render in the browser using a browser-native library
- No server-side rendering needed

**Fidelity Analysis**:

The current `SlideDeckPptxSkill` generates PPTX using python-pptx with themed templates. The PPTX contains:
- Title slides with cover text
- Content slides with bullet lists
- Two-column layouts
- Speaker notes
- Media suggestions (in notes only, not embedded)

The semantic JSON (`Slide` interface) contains all the same information. The JSON/CSS rendering in `SlideBody` already covers:
- title, bullets, two_column, callout, summary layouts
- speaker notes
- media suggestions (displayed as links, not embedded)
- citations

**Key difference**: The JSON/CSS rendering uses browser fonts and CSS, while the PPTX uses python-pptx templates with specific fonts (Microsoft YaHei) and colors. The visual appearance will differ, but the semantic content is identical.

**Can this satisfy the requirement that preview meaningfully matches downloaded PPTX?**

If "meaningfully matches" means:
- Same number of slides: YES (both derived from same JSON)
- Same slide order: YES
- Same title/text content: YES
- Same bullet points: YES
- Same speaker notes: YES
- Same visual layout (fonts, colors, positioning): NO (CSS vs PPTX template differences)

The user's requirement (from PRD R4) is: "preview PNG 全部来自已存储的同一 PPTX". This means the preview must come from the actual PPTX file, not a separate rendering.

**Conclusion**: The generation-controlled alternative (Approach A) does NOT satisfy the requirement that preview comes from the stored PPTX. It would be a regression to the old JSON/CSS fallback.

**Approach B** (browser-side PPTX parsing) DOES satisfy the requirement because it renders the actual stored PPTX bytes.

## Option 5: Browser ArrayBuffer/Blob in iframe/object

### Can the browser directly open a PPTX ArrayBuffer/blob in an iframe or object?

**Short answer**: NO. Browsers cannot natively render PPTX files.

When you set an iframe's `src` to a blob URL of a PPTX file:
- Chrome/Edge: Offers to download the file or shows "This page couldn't load a plugin"
- Firefox: Offers to download the file
- Safari: Offers to download the file

The `<object>` and `<embed>` tags behave similarly — they delegate to plugins (which are deprecated) or offer downloads.

**Verification**: This is well-documented browser behavior. PPTX is not a web-native format. The browser has no built-in OOXML renderer.

**Workarounds that don't work**:
- `data:application/vnd.openxmlformats-officedocument.presentationml.presentation;base64,...` — same download behavior
- Setting MIME type correctly — browsers still don't render it
- Using `srcdoc` — only works for HTML

## Option 6: Security Implications

### Untrusted OOXML ZIP/XML

PPTX files are ZIP archives containing XML files. Processing untrusted PPTX in the browser requires:

1. **ZIP bomb protection**: Malicious ZIP files can expand to petabytes. Libraries like jszip have size limits but must be configured.
2. **XML injection**: PPTX XML can contain XXE (XML External Entity) attacks. Browser-side XML parsers are generally safe against XXE but libraries must not use `DOMParser` in dangerous ways.
3. **Script injection**: PPTX can contain embedded scripts (OLE objects, macros). The renderer must sanitize or skip these.
4. **Path traversal**: ZIP entries can have `../` paths. Libraries must validate entry paths.

**@aiden0z/pptx-renderer** has `RECOMMENDED_ZIP_LIMITS` configuration for ZIP bomb protection. It uses fast-xml-parser (not DOMParser) which is safer.

**pptx-react-viewer** includes `dompurify` dependency for HTML sanitization.

### Remote Media

The current semantic JSON can contain media URLs (video, gif, embed, animation, image). These are displayed as links in the frontend, not embedded. If a browser-native renderer were to fetch these:
- CORS restrictions may block cross-origin media
- Privacy concerns with fetching external URLs from the user's browser
- Content Security Policy (CSP) restrictions

The current implementation stores media suggestions in PPTX notes only, not as embedded media. This is safe.

## Comparison Matrix

| Option | Removes LibreOffice | Fidelity | Bundle Size | Maintenance | License | Security | Complexity |
|--------|---------------------|----------|-------------|-------------|---------|----------|------------|
| @aiden0z/pptx-renderer | YES | HIGH (452+ visual regression tests) | ~2.6 MB + echarts | Active (last: 2026-07-10) | Apache-2.0 | ZIP limits, safe XML | Low-Medium |
| pptx-react-viewer | YES | HIGH (16 element types) | ~25.3 MB | Active (last: 2026-07-27) | Apache-2.0 | DOMPurify | Low (drop-in) |
| pptx-viewer-core | YES | HIGH | ~12.2 MB | Active (last: 2026-07-26) | Apache-2.0 | Safe | Medium (SDK only) |
| pptx-preview | YES | Unknown (closed source) | ~1.8 MB | Stale (9 months) | ISC (closed) | Unknown | Low |
| Microsoft/Google Viewer | YES | HIGH | 0 (external) | External | N/A | Requires public URL | Low |
| OnlyOffice | NO (wraps LibreOffice) | HIGH | 0 (server) | Active | AGPL-3.0 | Server-side | Very High |
| Collabora | NO (wraps LibreOffice) | HIGH | 0 (server) | Active | MPL-2.0 | Server-side | Very High |
| JSON/CSS (existing fallback) | YES | LOW (different rendering) | 0 (existing) | Existing | N/A | Safe | None |
| iframe/object | NO (doesn't render) | N/A | 0 | N/A | N/A | N/A | None |

## Decisive Recommendation

### Recommended: @aiden0z/pptx-renderer

**Rationale**:
1. **Highest fidelity** with 452+ visual regression tests against PowerPoint ground truth
2. **Reasonable bundle size** (2.6 MB + echarts) — much smaller than pptx-react-viewer
3. **Actively maintained** — published 2 weeks ago, TypeScript-first, CI/CD pipeline
4. **Apache-2.0 license** — permissive, no copyleft concerns
5. **Security-conscious** — `RECOMMENDED_ZIP_LIMITS` for ZIP bomb protection, uses fast-xml-parser
6. **Browser-native** — completely removes server-side rendering dependency
7. **Covers needed features** — shapes, text, images, tables, charts, SmartArt, backgrounds, gradients
8. **Windowed rendering** — supports large decks with lazy loading

### Alternative: pptx-react-viewer

If editing capabilities are desired in the future, pptx-react-viewer is a drop-in React component. However, its 25.3 MB size and many optional dependencies make it heavier than needed for preview-only.

### Not Recommended

- **Microsoft/Google Viewer**: Requires public URLs, unacceptable for private workspace data
- **OnlyOffice/Collabora**: Does not remove LibreOffice, adds complexity
- **JSON/CSS fallback**: Does not satisfy requirement that preview comes from stored PPTX
- **iframe/object**: Browsers cannot render PPTX natively

## Migration Plan

### Phase 1: Add Browser-Side PPTX Rendering (Non-Breaking)

1. **Install @aiden0z/pptx-renderer** in apps/web:
   ```bash
   cd apps/web && npm install @aiden0z/pptx-renderer
   ```

2. **Create new component** `PptxNativePreview.tsx`:
   - Fetches stored PPTX bytes from `/api/artifacts/{id}/export?format=pptx`
   - Uses `PptxViewer.open()` to render in a container div
   - Supports slide navigation via the viewer's API
   - Handles loading states and errors

3. **Modify `SlideDeckPreview.tsx`**:
   - For authoritative artifacts, use `PptxNativePreview` instead of PNG images
   - Remove the PNG blob fetching logic (`getArtifactPreviewManifest`, `getArtifactPreviewPage`)
   - Keep the JSON/CSS fallback for legacy artifacts

### Phase 2: Remove Server-Side Rendering (Breaking)

4. **Remove `PptxPreviewRenderer`** (apps/api/app/integrations/presentation_renderer.py):
   - Delete the entire file
   - Remove `pymupdf` from pyproject.toml dependencies

5. **Remove LibreOffice from Docker** (infra/docker/api.Dockerfile):
   - Remove `libreoffice-impress libreoffice-core` from apt-get install
   - Keep `fonts-noto-cjk fonts-dejavu-core` if needed elsewhere

6. **Simplify `ArtifactPresentationService`** (apps/api/app/services/artifact_presentations.py):
   - Remove renderer parameter and rendering logic
   - Keep PPTX generation and storage
   - Remove preview manifest/page generation and storage

7. **Simplify artifact model** (apps/api/app/artifacts/models.py):
   - Remove `preview_status`, `preview_manifest` fields (or keep for backward compat)
   - Keep `object_key`, `mime_type`, `sha256`, `size_bytes`, `page_count`

8. **Simplify API endpoints** (apps/api/app/api/artifacts.py):
   - Remove `/previews` and `/previews/{page}` endpoints
   - Keep `/export?format=pptx` endpoint (still serves stored PPTX bytes)

9. **Remove config** (apps/api/app/core/config.py):
   - Remove `pptx_converter_path`, `pptx_conversion_timeout_seconds`, `pptx_preview_dpi`
   - Remove from docker-compose.yml environment

10. **Update tests**:
    - Remove test_presentation_renderer.py
    - Update test_artifact_previews.py
    - Update test_artifact_presentation_migration.py

### Phase 3: Optimize Frontend

11. **Lazy load @aiden0z/pptx-renderer**:
    - Use dynamic import to avoid adding 2.6 MB to initial bundle
    - Load only when user opens a PPTX preview

12. **Add slide thumbnail sidebar**:
    - Use the viewer's API to generate thumbnail previews
    - Replace the current PNG-based thumbnail sidebar

13. **Preserve speaker notes**:
    - Extract notes from parsed PPTX and display in the existing notes panel

### Files to Remove/Rework

**Remove**:
- `apps/api/app/integrations/presentation_renderer.py`
- `apps/api/tests/integrations/test_presentation_renderer.py`

**Rework**:
- `apps/web/src/components/SlideDeckPreview.tsx` — replace PNG rendering with PptxNativePreview
- `apps/api/app/services/artifact_presentations.py` — remove rendering, keep PPTX generation/storage
- `apps/api/app/api/artifacts.py` — remove preview endpoints
- `apps/api/app/artifacts/models.py` — optionally remove preview fields
- `apps/api/app/core/config.py` — remove LibreOffice config
- `infra/docker/api.Dockerfile` — remove LibreOffice packages
- `docker-compose.yml` — remove PPTX_CONVERTER_PATH, PPTX_CONVERSION_TIMEOUT_SECONDS, PPTX_PREVIEW_DPI
- `apps/api/app/main.py` — remove PptxPreviewRenderer initialization
- `apps/api/app/artifacts/dependencies.py` — remove get_artifact_presentation_service

**Add**:
- `apps/web/src/components/PptxNativePreview.tsx` — new browser-side PPTX renderer component

### Risk Assessment

**Low risk**:
- @aiden0z/pptx-renderer is well-tested with visual regression suite
- The frontend already has the JSON/CSS fallback for legacy artifacts
- The API contract for `/export?format=pptx` remains unchanged

**Medium risk**:
- Bundle size increase (~2.6 MB + echarts) — mitigated by lazy loading
- Browser compatibility — the library targets modern browsers, which aligns with Vite/React requirements

**Mitigations**:
- Keep the JSON/CSS fallback for legacy artifacts
- Add feature flag to toggle between PNG and browser-native rendering
- Test with the actual themed PPTX files generated by SlideDeckPptxSkill

## Caveats / Not Found

- No primary source was found for pptx-preview's rendering quality (closed source)
- The @aiden0z/pptx-renderer's chart rendering depends on ECharts — need to verify compatibility with python-pptx's chart output
- The migration plan assumes the frontend can fetch PPTX bytes via the existing `/export?format=pptx` endpoint — this is authenticated and should work
- The @aiden0z/pptx-renderer's TypeScript types and React integration need to be verified in the actual Vite/React setup
