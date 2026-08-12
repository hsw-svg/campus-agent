## Scope and mode

- Surface: `apps/web/src/components/StudentWorkspace.tsx` and student-only child surfaces.
- Mode: Experience + Operate.
- Teacher and admin surfaces remain separate mature campus SaaS interfaces.

## Audience, job, and constraints

- Audience: university students using an anonymous student workspace.
- Job: resume a course, read interactive material, ask AI questions, practice, review mistakes, and understand progress.
- Preserve current API, SSE, DeepTutor, course, news, resume, conversation, and workspace behavior.
- Never expose teacher or admin navigation inside the student workspace.

## Chosen direction

- World: 星图学习舱.
- Approved comp: `.impeccable/mocks/student-orbit-comp-1.webp`.
- Memorable moment: a course planet surrounded by chapter orbits; the active chapter glows warm gold while the AI study companion and today's learning route remain immediately actionable.
- Do not literalize the planet as a game level or hide content behind spatial effects. Every orbit node maps to a real chapter state.

## System inventory

| Ingredient | Approved-comp commitment | Implementation medium |
|---|---|---|
| App shell | Deep-navy full viewport; slim icon rail, content rail, central stage, companion rail, bottom route | Semantic React + CSS grid |
| Primary navigation | Six student-only destinations with consistent line icons and cyan active capsule | React + lucide-react |
| Course rail | Three compact course cards plus two interactive-material progress cards | Existing course data + `CourseArtwork` + semantic HTML/CSS |
| Course planet | Large shaded blue planet covering roughly one-third of the first viewport | Generated raster/WebP asset; never a flat CSS gradient |
| Orbital chapter system | 6–7 elliptical rings/nodes; complete cyan, active gold, locked slate | Responsive SVG with semantic HTML controls and keyboard parity |
| Star field | Dense but quiet deep-space texture over most of the central stage | Generated raster/WebP background with dark overlay |
| AI study companion | Clearly synthetic stylized 3D companion, visually dominant but secondary to the current course action | Generated raster/WebP with explicit AI label; no real identity |
| AI Q&A dock | Three suggested questions and a clear input/action | Semantic React form, existing chat behavior |
| Today route | Five stages spanning the full lower workspace; one active, completed and future states distinct | Semantic ordered list + CSS/SVG connector |
| Primary action | Cyan-to-teal “继续学习” control anchored on the course planet | Semantic button; existing course/resume behavior |
| Type | Compact workhorse Chinese sans; display 20–28px, section 14–18px, body 12–14px | Existing font stack; no rasterized text |
| Geometry | 12–18px dark glass panels, 1px blue hairlines, restrained inner glow, no generic bento shadows | CSS tokens and reusable classes |
| Motion | Slow orbital drift, node focus bloom, companion idle motion; content visible without motion | Motion + SVG/CSS; reduced-motion locks all drift |

## Responsive commitments

- Desktop preserves the three-rail composition and large planet.
- Tablet reduces the course rail and keeps course planet plus AI dock.
- Mobile replaces free orbit with a chapter carousel; AI companion becomes a collapsible sheet; primary learning action stays above the fold.
