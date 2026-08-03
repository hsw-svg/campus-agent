import type { WorkspaceRole } from './types'

export interface Workspace {
  id: string
  role: WorkspaceRole
}

export interface CourseContext {
  courseId: string | null
  courseName: string
  chapterId?: string | null
  chapterName?: string
  workflowId: string
  workflowName: string
}

export interface Course {
  id: string
  name: string
  description: string | null
  teacher_name: string | null
  starts_at: string | null
  thumbnail_key: string | null
  category: string | null
  created_at: string
  updated_at: string
}

export interface CourseSummary extends Course {
  chapter_count: number
  completed_chapter_count: number
  progress_percent: number
  started: boolean
  last_studied_at: string | null
}

export interface CourseChapter {
  id: string
  title: string
  summary: string | null
  position: number
  estimated_minutes: number | null
  knowledge_points: string[]
  completed: boolean
  current: boolean
}

export interface CourseWeakPoint {
  id: string
  chapter_id: string | null
  name: string
  recommendation: string
}

export interface CourseDetail extends CourseSummary {
  chapters: CourseChapter[]
  current_chapter_id: string | null
  weak_points: CourseWeakPoint[]
}

export interface CreatedWorkspace {
  workspace: Workspace
  token: string
}

export interface Conversation {
  id: string
  title: string
  agent_id: string | null
  course_id: string | null
  chapter_id: string | null
  created_at: string
  updated_at: string
}

export interface Agent {
  id: string
  name: string
  description: string
}

export interface ApiMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent_id: string | null
  tool_events: unknown[] | null
  artifacts: unknown[] | null
  created_at: string
}

export interface Attachment {
  id: string
  conversation_id: string | null
  course_id: string | null
  filename: string
  content_type: string
  size_bytes: number
  scope: 'conversation' | 'workspace'
  status: 'uploaded' | 'parsing' | 'indexed' | 'degraded' | 'failed'
  status_message: string | null
  extracted_chars: number
  created_at: string
  updated_at: string
}

export interface ArtifactReference {
  type: string
  artifact_id: string
  title: string
}

export interface Artifact {
  id: string
  workspace_id: string
  conversation_id: string
  type: string
  title: string
  content: string
  data: Record<string, unknown>
  format: string
  created_at: string
  updated_at: string
}

export interface AgentHistoryItem {
  run_id: string
  conversation_id: string
  conversation_title: string
  agent_id: string | null
  status: string
  summary: string | null
  artifact: Artifact | null
  created_at: string
  updated_at: string
}

export type ResumeIssueSeverity = 'high' | 'medium' | 'low'

export interface ResumeIssue {
  section: string
  severity: ResumeIssueSeverity
  problem: string
  evidence: string
  suggestion: string
}

export interface ResumeSectionSuggestion {
  section: string
  suggestions: string[]
  rewrite_examples: string[]
}

export interface ResumeCourseCapabilityMatch {
  course_name: string
  progress_evidence: string
  capability: string
  suggested_wording: string
}

export interface ResumeJobMatch {
  matched_keywords: string[]
  gap_keywords: string[]
  guidance: string
}

export interface OptimizedResumeSection {
  heading: string
  markdown: string
}

export interface ResumeAnalysisReport {
  overall_summary: string
  issues: ResumeIssue[]
  section_suggestions: ResumeSectionSuggestion[]
  course_capability_matches: ResumeCourseCapabilityMatch[]
  job_match: ResumeJobMatch
  optimized_resume_sections: OptimizedResumeSection[]
  evidence_notice: string
}

export interface ResumeCourseSnapshot {
  course_id: string
  name: string
  category: string | null
  progress_percent: number
  completed_chapters: Array<{ title: string; knowledge_points: string[] }>
  current_chapter: string | null
  weak_points: Array<{ name: string; recommendation: string }>
}

export interface ResumeAnalysisInputSnapshot {
  resume_attachment_id: string
  resume_filename: string
  target_role: string | null
  job_description: string | null
  selected_courses: ResumeCourseSnapshot[]
}

export interface ResumeAnalysisArtifactData {
  schema_version: 'resume_analysis.v1'
  input: ResumeAnalysisInputSnapshot
  report: ResumeAnalysisReport
}

export interface ResumeAnalysisArtifact extends Omit<Artifact, 'data'> {
  data: ResumeAnalysisArtifactData
}

export interface ResumeProfile {
  current_resume: Attachment | null
}

export interface ResumeAnalysisHistoryItem {
  run_id: string
  conversation_id: string
  status: string
  error_message: string | null
  target_role: string | null
  resume_filename: string | null
  summary: string | null
  artifact: ResumeAnalysisArtifact | null
  created_at: string
  updated_at: string
}

export interface SourceCitation {
  attachment_id: string
  filename: string
  page_number: number | null
  excerpt: string
}

export interface StreamEvent {
  type: 'message_start' | 'route_decision' | 'delta' | 'tool_status' | 'artifact' | 'done' | 'error'
  data: Record<string, unknown>
}

export type CampusNewsCategory = 'news' | 'activity' | 'notice'

export interface CampusNewsItem {
  id: string
  category: CampusNewsCategory
  title: string
  published_at: string
  event_end_at: string | null
  source: string
  summary: string | null
  url: string | null
}

export interface CampusNewsResponse {
  mode: 'sample' | 'live'
  status: 'fresh' | 'stale' | 'degraded'
  refreshing: boolean
  last_success_at: string | null
  items: CampusNewsItem[]
}

export interface DeepTutorBook {
  id: string
  title: string
  description: string
  status: string | null
  chapterCount: number | null
  pageCount: number | null
  raw: Record<string, unknown>
}

export interface DeepTutorSpineItem {
  id: string
  title: string
  position: number
  raw: Record<string, unknown>
}

export interface DeepTutorPage {
  id: string
  title: string
  content: string
  blocks: DeepTutorBlock[]
  raw: Record<string, unknown>
}

export interface DeepTutorBlock {
  id: string
  type: string
  title: string
  content: string
  raw: Record<string, unknown>
}

export interface DeepTutorKnowledgeBase {
  name: string
  description: string
  raw: Record<string, unknown>
}

export interface DeepTutorChatEvent {
  type: string
  text: string
  raw: Record<string, unknown>
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function firstString(record: Record<string, unknown>, keys: string[], fallback: string): string {
  for (const key of keys) {
    if (typeof record[key] === 'string' && record[key].trim()) return record[key].trim()
  }
  return fallback
}

function firstNumber(record: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    if (typeof record[key] === 'number' && Number.isFinite(record[key])) return record[key]
    if (typeof record[key] === 'string' && record[key].trim() && Number.isFinite(Number(record[key]))) {
      return Number(record[key])
    }
  }
  return null
}

function responseRecords(value: unknown, keys: string[]): Record<string, unknown>[] {
  if (Array.isArray(value)) return value.filter(isRecord)
  if (!isRecord(value)) return []
  for (const key of keys) {
    if (Array.isArray(value[key])) return value[key].filter(isRecord)
  }
  if (isRecord(value.data)) return responseRecords(value.data, keys)
  return []
}

export function deepTutorBooksFromResponse(value: unknown): DeepTutorBook[] {
  return responseRecords(value, ['books', 'items', 'data']).flatMap((raw) => {
    const id = firstString(raw, ['id', 'book_id'], '')
    return id ? [{
      id,
      title: firstString(raw, ['title', 'name'], '未命名交互教材'),
      description: firstString(raw, ['description', 'summary'], 'DeepTutor 交互式教材'),
      status: firstString(raw, ['status', 'state'], '') || null,
      chapterCount: firstNumber(raw, ['chapter_count', 'chapters_count', 'chaptersCount'])
        ?? (Array.isArray(raw.chapters) ? raw.chapters.length : null),
      pageCount: firstNumber(raw, ['page_count', 'pages_count', 'pagesCount'])
        ?? (Array.isArray(raw.pages) ? raw.pages.length : null),
      raw,
    }] : []
  })
}

export function deepTutorSpineFromResponse(value: unknown): DeepTutorSpineItem[] {
  if (isRecord(value) && isRecord(value.spine)) {
    const chapters = Array.isArray(value.spine.chapters) ? value.spine.chapters.filter(isRecord) : []
    const expandedPages = chapters.flatMap((chapter, chapterIndex) => {
      const pageIds = Array.isArray(chapter.page_ids)
        ? chapter.page_ids.filter((pageId): pageId is string => typeof pageId === 'string' && pageId.trim().length > 0)
        : []
      if (pageIds.length === 0) return [chapter]
      const chapterTitle = firstString(chapter, ['title', 'name'], `第 ${chapterIndex + 1} 章`)
      return pageIds.map((pageId, pageIndex) => ({
        id: pageId,
        title: `${chapterTitle} · 第 ${pageIndex + 1} 页`,
        position: chapterIndex * 1000 + pageIndex,
      }))
    })
    return expandedPages.flatMap((raw, index) => {
      const id = firstString(raw, ['id', 'page_id', 'chapter_id'], '')
      return id ? [{
        id,
        title: firstString(raw, ['title', 'name'], `第 ${index + 1} 节`),
        position: typeof raw.position === 'number' ? raw.position : index,
        raw,
      }] : []
    })
  }
  return responseRecords(value, ['spine', 'items', 'pages', 'chapters', 'data']).flatMap((raw, index) => {
    const id = firstString(raw, ['id', 'page_id', 'chapter_id'], '')
    return id ? [{
      id,
      title: firstString(raw, ['title', 'name'], `第 ${index + 1} 节`),
      position: typeof raw.position === 'number' ? raw.position : index,
      raw,
    }] : []
  })
}

function deepTutorBlockRecords(raw: Record<string, unknown>): Record<string, unknown>[] {
  const candidates = [raw.blocks, raw.content_blocks, raw.sections]
  for (const candidate of candidates) {
    if (Array.isArray(candidate)) return candidate.filter(isRecord)
  }
  return []
}

export function deepTutorBlocksFromRecord(raw: Record<string, unknown>): DeepTutorBlock[] {
  return deepTutorBlockRecords(raw).flatMap((block, index) => {
    const payload = isRecord(block.payload) ? block.payload : block
    const params = isRecord(block.params) ? block.params : block
    const content = firstString(payload, ['content', 'markdown', 'body', 'text', 'description', 'html', 'code'], '')
    return [{
      id: firstString(block, ['id', 'block_id'], `block-${index + 1}`),
      type: firstString(block, ['type', 'block_type', 'kind'], 'text').toLowerCase(),
      title: firstString(block, ['title', 'name', 'heading'], firstString(params, ['title', 'heading', 'label'], '')),
      content,
      raw: block,
    }]
  })
}

export function deepTutorPageFromResponse(value: unknown): DeepTutorPage | null {
  if (!isRecord(value)) return null
  const raw = isRecord(value.page)
    ? value.page
    : isRecord(value.data) && !Array.isArray(value.data)
      ? value.data
      : value
  const id = firstString(raw, ['id', 'page_id'], '')
  if (!id) return null
  const blocks = deepTutorBlocksFromRecord(raw)
  const content = firstString(raw, ['content', 'markdown', 'body', 'text'], '本页暂无可显示内容。')
  return {
    id,
    title: firstString(raw, ['title', 'name'], '交互教材页面'),
    content,
    blocks,
    raw,
  }
}

export function deepTutorKnowledgeBasesFromResponse(value: unknown): DeepTutorKnowledgeBase[] {
  return responseRecords(value, ['knowledge_bases', 'knowledgeBases', 'items', 'data']).flatMap((raw) => {
    const name = firstString(raw, ['name', 'kb_name', 'id'], '')
    return name ? [{
      name,
      description: firstString(raw, ['description', 'summary'], '可用于 DeepTutor 检索的知识库'),
      raw,
    }] : []
  })
}

function nestedText(value: unknown, depth = 0): string {
  if (typeof value === 'string') return value
  if (!isRecord(value) || depth > 2) return ''
  for (const key of ['text', 'content', 'delta', 'answer', 'message', 'result']) {
    const text = nestedText(value[key], depth + 1)
    if (text) return text
  }
  return ''
}

export function parseDeepTutorChatEvent(value: unknown): DeepTutorChatEvent {
  if (typeof value === 'string') return { type: 'stream', text: value, raw: {} }
  if (!isRecord(value)) return { type: 'stream', text: '', raw: {} }
  return {
    type: firstString(value, ['type', 'event', 'kind'], 'stream'),
    text: nestedText(value),
    raw: value,
  }
}

export function sourceCitationsFromEvent(event: StreamEvent): SourceCitation[] {
  if (event.type !== 'artifact' || event.data.type !== 'sources' || !Array.isArray(event.data.sources)) {
    return []
  }
  return event.data.sources.flatMap((item): SourceCitation[] => {
    if (!item || typeof item !== 'object') return []
    const source = item as Record<string, unknown>
    if (typeof source.attachment_id !== 'string' || typeof source.filename !== 'string' || typeof source.excerpt !== 'string') {
      return []
    }
    return [{
      attachment_id: source.attachment_id,
      filename: source.filename,
      page_number: typeof source.page_number === 'number' ? source.page_number : null,
      excerpt: source.excerpt,
    }]
  })
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
    public readonly details?: Record<string, unknown> | null,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      ...(token ? { 'X-Workspace-Token': token } : {}),
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: { code?: string; message?: string; details?: Record<string, unknown> | null } } | null
    throw new ApiError(
      response.status,
      body?.error?.message ?? '请求失败，请稍后重试。',
      body?.error?.code,
      body?.error?.details,
    )
  }
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>
}

export function createWorkspace(role: WorkspaceRole): Promise<CreatedWorkspace> {
  return request<CreatedWorkspace>('/workspaces', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  })
}

export function listCampusNews(): Promise<CampusNewsResponse> {
  return request<CampusNewsResponse>('/campus-news')
}

export function getCurrentWorkspace(token: string): Promise<Workspace> {
  return request<Workspace>('/workspaces/current', undefined, token)
}

export function listConversations(token: string): Promise<Conversation[]> {
  return request<Conversation[]>('/conversations', undefined, token)
}

export function listCourses(token: string): Promise<CourseSummary[]> {
  return request<CourseSummary[]>('/courses', undefined, token)
}

export function initializeDefaultCourses(token: string): Promise<CourseSummary[]> {
  return request<CourseSummary[]>('/courses/defaults', { method: 'POST' }, token)
}

export function getCourseDetail(token: string, courseId: string): Promise<CourseDetail> {
  return request<CourseDetail>(`/courses/${courseId}`, undefined, token)
}

export function startCourse(token: string, courseId: string): Promise<CourseDetail> {
  return request<CourseDetail>(`/courses/${courseId}/start`, { method: 'POST' }, token)
}

export function startCourseChapter(token: string, courseId: string, chapterId: string): Promise<CourseDetail> {
  return request<CourseDetail>(`/courses/${courseId}/chapters/${chapterId}/start`, { method: 'POST' }, token)
}

export function completeCourseChapter(token: string, courseId: string, chapterId: string): Promise<CourseDetail> {
  return request<CourseDetail>(`/courses/${courseId}/chapters/${chapterId}/complete`, { method: 'POST' }, token)
}

export function createCourse(token: string, name: string, description?: string): Promise<Course> {
  return request<Course>('/courses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: description ?? null }),
  }, token)
}

export function updateCourse(token: string, courseId: string, name: string, description?: string | null): Promise<Course> {
  return request<Course>(`/courses/${courseId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: description ?? null }),
  }, token)
}

export function deleteCourse(token: string, courseId: string): Promise<void> {
  return request<void>(`/courses/${courseId}`, { method: 'DELETE' }, token)
}

export function listDeepTutorBooks(token: string): Promise<unknown> {
  return request<unknown>('/deeptutor/books', undefined, token)
}

export function getDeepTutorSpine(token: string, bookId: string): Promise<unknown> {
  return request<unknown>(`/deeptutor/books/${encodeURIComponent(bookId)}/spine`, undefined, token)
}

export function getDeepTutorPage(token: string, bookId: string, pageId: string): Promise<unknown> {
  return request<unknown>(
    `/deeptutor/books/${encodeURIComponent(bookId)}/pages/${encodeURIComponent(pageId)}`,
    undefined,
    token,
  )
}

export function listDeepTutorKnowledgeBases(token: string): Promise<unknown> {
  return request<unknown>('/deeptutor/knowledge-bases', undefined, token)
}

export function createDeepTutorBook(
  token: string,
  payload: Record<string, unknown>,
): Promise<unknown> {
  return request<unknown>('/deeptutor/books', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, token)
}

export function getDeepTutorChatWebSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/deeptutor/chat`
}

export function createConversation(token: string, courseId?: string | null, chapterId?: string | null): Promise<Conversation> {
  return request<Conversation>('/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: null, course_id: courseId ?? null, chapter_id: chapterId ?? null }),
  }, token)
}

export function listMessages(token: string, conversationId: string): Promise<ApiMessage[]> {
  return request<ApiMessage[]>(`/conversations/${conversationId}/messages`, undefined, token)
}

export function listConversationAttachments(token: string, conversationId: string): Promise<Attachment[]> {
  return request<Attachment[]>(`/conversations/${conversationId}/attachments`, undefined, token)
}

export function listWorkspaceAttachments(token: string, courseId?: string | null): Promise<Attachment[]> {
  return request<Attachment[]>(`/workspaces/current/attachments${courseId ? `?course_id=${encodeURIComponent(courseId)}` : ''}`, undefined, token)
}

export function listArtifacts(token: string, conversationId: string): Promise<Artifact[]> {
  return request<Artifact[]>(`/conversations/${conversationId}/artifacts`, undefined, token)
}

export function listCourseAgentHistory(token: string, courseId: string): Promise<AgentHistoryItem[]> {
  return request<AgentHistoryItem[]>(`/courses/${courseId}/agent-history`, undefined, token)
}

export function deleteCourseAgentHistory(token: string, courseId: string, runId: string): Promise<void> {
  return request<void>(`/courses/${courseId}/agent-history/${runId}`, { method: 'DELETE' }, token)
}

export function getResumeProfile(token: string): Promise<ResumeProfile> {
  return request<ResumeProfile>('/resume-assistant/profile', undefined, token)
}

export function setCurrentResume(token: string, attachmentId: string): Promise<ResumeProfile> {
  return request<ResumeProfile>('/resume-assistant/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ attachment_id: attachmentId }),
  }, token)
}

export function listResumeAnalyses(token: string): Promise<ResumeAnalysisHistoryItem[]> {
  return request<ResumeAnalysisHistoryItem[]>('/resume-assistant/analyses', undefined, token)
}

export function deleteResumeAnalysis(token: string, runId: string): Promise<void> {
  return request<void>(`/resume-assistant/analyses/${runId}`, { method: 'DELETE' }, token)
}

export function getArtifact(token: string, artifactId: string): Promise<Artifact> {
  return request<Artifact>(`/artifacts/${artifactId}`, undefined, token)
}

export async function exportArtifact(
  token: string,
  artifactId: string,
  format: 'markdown' | 'csv' | 'pptx' = 'markdown',
): Promise<Blob> {
  const response = await fetch(`/api/artifacts/${artifactId}/export?format=${format}`, {
    headers: { 'X-Workspace-Token': token },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: { code?: string; message?: string; details?: Record<string, unknown> | null } } | null
    throw new ApiError(
      response.status,
      body?.error?.message ?? '成果导出失败，请稍后重试。',
      body?.error?.code,
      body?.error?.details,
    )
  }
  return response.blob()
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function deleteConversation(token: string, conversationId: string): Promise<void> {
  return request<void>(`/conversations/${conversationId}`, { method: 'DELETE' }, token)
}

export async function uploadAttachment(
  token: string,
  conversationId: string,
  file: File,
  scope: 'conversation' | 'workspace' = 'workspace',
): Promise<Attachment> {
  const form = new FormData()
  form.append('file', file)
  form.append('scope', scope)
  return request<Attachment>(`/conversations/${conversationId}/attachments`, {
    method: 'POST',
    body: form,
  }, token)
}

export async function uploadWorkspaceAttachment(token: string, file: File, courseId?: string | null): Promise<Attachment> {
  const form = new FormData()
  form.append('file', file)
  return request<Attachment>(`/workspaces/current/attachments${courseId ? `?course_id=${encodeURIComponent(courseId)}` : ''}`, {
    method: 'POST',
    body: form,
  }, token)
}

export async function* streamMessage(options: {
  token: string
  conversationId: string
  content: string
  agentId?: string | null
  selectedAttachmentIds: string[]
  selectedArtifactIds: string[]
  courseContext?: CourseContext
  parentRunId?: string | null
  inputRefs?: string[]
  signal: AbortSignal
}): AsyncGenerator<StreamEvent> {
  const response = await fetch(`/api/conversations/${options.conversationId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Workspace-Token': options.token,
    },
    body: JSON.stringify({
      content: options.content,
      agent_id: options.agentId ?? null,
      selected_attachment_ids: options.selectedAttachmentIds,
      selected_artifact_ids: options.selectedArtifactIds,
      course_id: options.courseContext?.courseId ?? null,
      workflow_id: options.courseContext?.workflowId ?? null,
      parent_run_id: options.parentRunId ?? null,
      input_refs: options.inputRefs ?? [],
    }),
    signal: options.signal,
  })
  yield* streamEventsFromResponse(response, '无法开始流式回复。')
}

export async function* streamResumeAnalysis(options: {
  token: string
  attachmentId: string
  targetRole: string
  jobDescription: string
  selectedCourseIds: string[]
  signal: AbortSignal
}): AsyncGenerator<StreamEvent> {
  const response = await fetch('/api/resume-assistant/analyses/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Workspace-Token': options.token,
    },
    body: JSON.stringify({
      attachment_id: options.attachmentId,
      target_role: options.targetRole.trim() || null,
      job_description: options.jobDescription.trim() || null,
      selected_course_ids: options.selectedCourseIds,
    }),
    signal: options.signal,
  })
  yield* streamEventsFromResponse(response, '无法开始简历分析。')
}

async function* streamEventsFromResponse(
  response: Response,
  fallbackMessage: string,
): AsyncGenerator<StreamEvent> {
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null) as { error?: { code?: string; message?: string; details?: Record<string, unknown> | null } } | null
    throw new ApiError(
      response.status,
      body?.error?.message ?? fallbackMessage,
      body?.error?.code,
      body?.error?.details,
    )
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split(/\r?\n\r?\n/)
      buffer = chunks.pop() ?? ''
      for (const chunk of chunks) {
        const event = parseSseEvent(chunk)
        if (event) yield event
      }
    }
    buffer += decoder.decode()
    const trailingEvent = parseSseEvent(buffer)
    if (trailingEvent) yield trailingEvent
  } finally {
    reader.releaseLock()
  }
}

function parseSseEvent(chunk: string): StreamEvent | null {
  let type: StreamEvent['type'] | null = null
  const dataLines: string[] = []
  for (const line of chunk.split(/\r?\n/)) {
    if (line.startsWith('event:')) type = line.slice(6).trim() as StreamEvent['type']
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!type || dataLines.length === 0) return null
  try {
    return { type, data: JSON.parse(dataLines.join('\n')) as Record<string, unknown> }
  } catch {
    return null
  }
}
