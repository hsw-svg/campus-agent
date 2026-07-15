import type { WorkspaceRole } from '../workspaces'

export interface Agent {
  id: string
  name: string
  description: string
}

export interface AgentList {
  role: WorkspaceRole
  auto_agent_id: string
  agents: Agent[]
}

export interface Conversation {
  id: string
  title: string
  agent_id: string | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent_id: string | null
  tool_events: unknown[] | null
  artifacts: unknown[] | null
  created_at: string
}

export type AttachmentScope = 'conversation' | 'workspace'

export interface Attachment {
  id: string
  conversation_id: string | null
  filename: string
  content_type: string
  size_bytes: number
  scope: AttachmentScope
  status: 'uploaded' | 'parsing' | 'indexed' | 'degraded' | 'failed'
  status_message: string | null
  extracted_chars: number
  created_at: string
  updated_at: string
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string | null,
    message: string,
  ) {
    super(message)
  }
}

function authHeaders(token: string): Record<string, string> {
  return { 'X-Workspace-Token': token }
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { ...authHeaders(token), ...(init?.headers ?? {}) },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      error?: { code?: string; message?: string }
    } | null
    throw new ApiError(
      response.status,
      body?.error?.code ?? null,
      body?.error?.message ?? 'Request failed.',
    )
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

export function listAgents(token: string): Promise<AgentList> {
  return request<AgentList>('/agents', token)
}

export function listConversations(token: string): Promise<Conversation[]> {
  return request<Conversation[]>('/conversations', token)
}

export function createConversation(token: string, agentId: string | null): Promise<Conversation> {
  return request<Conversation>('/conversations', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: agentId }),
  })
}

export function getConversation(token: string, conversationId: string): Promise<Conversation> {
  return request<Conversation>(`/conversations/${conversationId}`, token)
}

export function listMessages(token: string, conversationId: string): Promise<Message[]> {
  return request<Message[]>(`/conversations/${conversationId}/messages`, token)
}

export function deleteConversation(token: string, conversationId: string): Promise<void> {
  return request<void>(`/conversations/${conversationId}`, token, { method: 'DELETE' })
}

export function listAttachments(token: string, conversationId: string): Promise<Attachment[]> {
  return request<Attachment[]>(`/conversations/${conversationId}/attachments`, token)
}

export async function uploadAttachment(
  token: string,
  conversationId: string,
  file: File,
  scope: AttachmentScope,
): Promise<Attachment> {
  const form = new FormData()
  form.append('file', file)
  form.append('scope', scope)
  return request<Attachment>(`/conversations/${conversationId}/attachments`, token, {
    method: 'POST',
    body: form,
  })
}
