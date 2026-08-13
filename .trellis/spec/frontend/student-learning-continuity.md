# Student Learning Continuity

## 1. Scope / Trigger

Use this contract when changing anonymous role selection, student course entry, recent conversation navigation, course/chapter chat restoration, or AI companion recommendations.

## 2. Signatures

- `sessionStorage["campus-agent.active-role"] -> "teacher" | "student" | "admin" | null`
- `localStorage["campus-agent.workspace-token.<role>"] -> workspace token`
- `GET /api/workspaces/current` validates a stored token before restoring a role.
- `GET /api/conversations -> Conversation[]`, ordered by `updated_at` descending.
- `GET /api/courses/{course_id} -> CourseDetail` restores course and chapter display data.
- `GET /api/conversations/{conversation_id}/messages -> Message[]` restores the transcript.
- `startedStudentCourses(courses) -> CourseSummary[]` filters `started=true` and sorts by `last_studied_at` descending.
- `firstCourseTextbookPage(course, chapter?) -> { bookId, pageId } | null` resolves only persisted Tutor bindings.
- `buildTutorRecommendedQuestions(role, course, chapter) -> TutorRecommendedQuestion[3]` owns deterministic recommendation generation.

## 3. Contracts

- Store only the active role in `sessionStorage`; keep the existing per-role anonymous token in `localStorage`. A full-page refresh resumes the same role and workspace, while an explicit “切换角色” removes the active-role marker.
- Do not render a workspace from an unchecked stored token. Validate it with `GET /api/workspaces/current`; remove a token only when the API returns `401`, then create a replacement anonymous workspace through the existing endpoint.
- `useWorkspaceChat` distinguishes conversation-list readiness from an empty list. Token changes reset and reload conversations; course/chapter changes clear active chat resources but must not discard the server conversation list.
- Student restoration always resolves the target `Conversation.course_id` and `Conversation.chapter_id` first, loads its owned `CourseDetail`, then opens its messages. An incrementing restore version prevents an older course request from overwriting a later selection.
- A workspace refresh restores the student role, workspace token, course list, and conversation list, but the learning-center route opens at the course-orbit overview. It must not automatically restore the last course/chapter transcript; the student explicitly selects a course and chapter or a recent conversation.
- The learning overview renders only `started=true` courses around the central planet. Selecting a course loads its server-owned chapters; selecting a chapter enters the exact course/chapter conversation context without navigating away from the learning center.
- Tutor reader navigation is a separate explicit action. Build it only from `Course.deeptutor_book_id + CourseChapter.deeptutor_page_ids`; never invent an ID or use a display position as a page ID.
- Entering a course/chapter selects the most recently updated exact `course_id + chapter_id` conversation. No match means an empty learning session; the first send creates exactly one bound conversation through the existing `POST /api/conversations` contract.
- Recent conversations include every non-`resume_helper` student chat. Course items show course/chapter context and use the same restoration path as automatic resume.
- AI companion recommendations are local deterministic projections. Four roles use distinct question styles; selected course, chapter, and the first available knowledge point refine the text. With no selected course, render role-aware generic questions and do not infer context from the merely featured course card.
- Legacy assistant messages pass through `normalizeStudentVisibleText` at the student rendering boundary. New messages are already normalized by the backend stream contract.
- `streamMessage` sends both current `course_id` and `chapter_id`; names and knowledge points remain display-only because backend resolves trusted metadata from the Conversation.
- In a selected course, upload uses `uploadFile(file, 'workspace', course.id)`, shows course/KB feedback, and `useWorkspaceChat` automatically selects all course attachments.

## 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Stored active role is absent or invalid | Show the role selector. |
| Stored token is valid | Resume the same role and anonymous workspace. |
| Stored token returns `401` | Remove it and create a replacement workspace for that role. |
| Course detail restoration fails | Keep navigation usable, show `courseError`, and do not open a different conversation. |
| Conversation chapter no longer belongs to the course | Report that the historical chapter is unavailable. |
| No exact course/chapter conversation exists | Show the course arrival empty state; create on first send only. |
| No course has `started=true` | Show the course-orbit empty state and a course-center action. |
| Selected course has no chapters | Keep course actions available and direct the student to create a Tutor textbook. |
| Course or selected chapter has no persisted Tutor page mapping | Hide the direct reader action; keep chapter chat available. |
| Rapid course/history selections overlap | Only the latest restore version may update learning context. |
| Course or chapter data is missing | Recommendation templates degrade to course-level or generic role text. |

## 5. Good / Base / Bad Cases

- Good: ask in course A/chapter A1, switch to course B, return to A/A1, and see the same transcript.
- Good: reload the browser and resume the same student workspace at the course-orbit overview without creating a workspace or conversation; selecting the previous course/chapter restores its transcript.
- Good: switch from peer to research-assistant and immediately see different questions grounded in the same chapter.
- Base: a student with no conversations sees a normal empty learning center and generic role-aware recommendations.
- Bad: clear `conversations` whenever `courseContext` changes; this destroys the lookup source needed to restore course history.
- Bad: open a message history before restoring its course/chapter context; subsequent sends can attach the wrong course metadata.
- Bad: use the first visible course card as recommendation context before the student selects or starts that course.
- Bad: auto-open the most recent course conversation on refresh; it bypasses the required learning overview.
- Bad: upload a textbook with conversation scope; textbook lifecycle belongs to the course, not one chat.

## 6. Tests Required

- Pure frontend test: exclude `resume_helper`, sort by `updated_at`, and select the latest exact course/chapter conversation.
- Pure frontend test: all four roles return three distinct contextual questions; no-course fallback does not invent a course.
- Pure frontend test: learning overview filters unstarted courses and orders started courses by recent study time.
- Pure frontend test: direct Tutor navigation returns `null` unless both a real book ID and a real chapter page ID exist.
- Browser regression: create a bound course message, switch courses, return, reload, and assert the same user message and course heading remain visible.
- Browser regression: recent-dialog context includes course and chapter; desktop and `< 640px` keep history, AI companion, and composer controls reachable.
- Browser regression: desktop and 390px layouts expose course textbook upload and show KB queued/degraded feedback.
- Run `npm.cmd run test`, `npm.cmd run lint`, `npm.cmd run build`, and the Impeccable detector for changed student UI targets.

## 7. Wrong vs Correct

```tsx
// Wrong: message history loads under whatever course happened to be active.
void openConversation(conversation.id)

// Correct: one restoration path establishes course/chapter before messages.
void restoreStudentConversation(conversation)
```

```tsx
// Wrong: a refreshed student workspace skips the learning overview.
void restoreStudentConversation(latestStudentCourseConversation(conversations))

// Correct: refresh loads lists; explicit course/chapter selection restores chat.
setLearningCourse(null)
setLearningChapterId(null)
```

```tsx
// Wrong: refresh forgets which anonymous role was active.
const [activeRole] = useState<WorkspaceRole | null>(null)

// Correct: validate the existing per-role token before resuming the session role.
const storedRole = sessionStorage.getItem('campus-agent.active-role')
if (isWorkspaceRole(storedRole)) void activateRole(storedRole)
```
