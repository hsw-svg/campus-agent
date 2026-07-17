import type { WorkspaceRole } from './types'

export interface Workspace {
  id: string
  role: WorkspaceRole
}

export interface CreatedWorkspace {
  workspace: Workspace
  token: string
}

export interface Conversation {
  id: string
  title: string
  agent_id: string | null
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

export function getCurrentWorkspace(token: string): Promise<Workspace> {
  return request<Workspace>('/workspaces/current', undefined, token)
}

export function listConversations(token: string): Promise<Conversation[]> {
  return request<Conversation[]>('/conversations', undefined, token)
}

export function createConversation(token: string): Promise<Conversation> {
  return request<Conversation>('/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: null }),
  }, token)
}

export function listMessages(token: string, conversationId: string): Promise<ApiMessage[]> {
  return request<ApiMessage[]>(`/conversations/${conversationId}/messages`, undefined, token)
}

export function listConversationAttachments(token: string, conversationId: string): Promise<Attachment[]> {
  return request<Attachment[]>(`/conversations/${conversationId}/attachments`, undefined, token)
}

export function listWorkspaceAttachments(token: string): Promise<Attachment[]> {
  return request<Attachment[]>('/workspaces/current/attachments', undefined, token)
}

export function listArtifacts(token: string, conversationId: string): Promise<Artifact[]> {
  return request<Artifact[]>(`/conversations/${conversationId}/artifacts`, undefined, token)
}

export function getArtifact(token: string, artifactId: string): Promise<Artifact> {
  return request<Artifact>(`/artifacts/${artifactId}`, undefined, token)
}

export async function exportArtifact(
  token: string,
  artifactId: string,
  format: 'markdown' | 'csv' = 'markdown',
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

export async function uploadWorkspaceAttachment(token: string, file: File): Promise<Attachment> {
  const form = new FormData()
  form.append('file', file)
  return request<Attachment>('/workspaces/current/attachments', {
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
    }),
    signal: options.signal,
  })

  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null) as { error?: { code?: string; message?: string; details?: Record<string, unknown> | null } } | null
    throw new ApiError(
      response.status,
      body?.error?.message ?? '无法开始流式回复。',
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
