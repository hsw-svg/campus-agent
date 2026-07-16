import type { Message } from './conversations'

// The fixed event vocabulary shared with the backend streaming contract.
export type StreamEventType =
  | 'message_start'
  | 'route_decision'
  | 'delta'
  | 'tool_status'
  | 'artifact'
  | 'done'
  | 'error'

export interface StreamEvent {
  type: StreamEventType
  data: Record<string, unknown>
}

export interface StreamMessageOptions {
  token: string
  conversationId: string
  content: string
  agentId: string | null
  selectedAttachmentIds?: string[]
  selectedArtifactIds?: string[]
  signal?: AbortSignal
}

/**
 * Parse a raw SSE buffer into complete events, returning the events found and
 * the trailing partial chunk that has not terminated with a blank line yet.
 */
export function parseSseChunk(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = []
  const segments = buffer.split('\n\n')
  const rest = segments.pop() ?? ''

  for (const segment of segments) {
    let eventType: string | null = null
    const dataLines: string[] = []
    for (const line of segment.split('\n')) {
      if (line.startsWith('event:')) {
        eventType = line.slice('event:'.length).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).trim())
      }
    }
    if (!eventType) continue
    let data: Record<string, unknown> = {}
    if (dataLines.length > 0) {
      try {
        data = JSON.parse(dataLines.join('\n')) as Record<string, unknown>
      } catch {
        data = {}
      }
    }
    events.push({ type: eventType as StreamEventType, data })
  }

  return { events, rest }
}

/**
 * POST a user turn and yield streaming events as the model responds. Uses the
 * fetch body reader rather than EventSource because the stream is a POST that
 * must carry the workspace token and message payload.
 */
export async function* streamMessage(
  options: StreamMessageOptions,
): AsyncGenerator<StreamEvent, void, void> {
  const response = await fetch(
    `/api/conversations/${options.conversationId}/messages/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Workspace-Token': options.token,
      },
      body: JSON.stringify({
        content: options.content,
        agent_id: options.agentId,
        selected_attachment_ids: options.selectedAttachmentIds,
        selected_artifact_ids: options.selectedArtifactIds,
      }),
      signal: options.signal,
    },
  )

  if (!response.ok || !response.body) {
    const body = (await response.json().catch(() => null)) as {
      error?: { code?: string; message?: string }
    } | null
    yield {
      type: 'error',
      data: {
        code: body?.error?.code ?? 'stream_request_failed',
        message: body?.error?.message ?? '无法开始流式回复。',
        retryable: true,
      },
    }
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const { events, rest } = parseSseChunk(buffer)
      buffer = rest
      for (const event of events) yield event
    }
  } finally {
    reader.releaseLock()
  }
}

export function isMessage(value: unknown): value is Message {
  return typeof value === 'object' && value !== null && 'id' in value && 'role' in value
}
