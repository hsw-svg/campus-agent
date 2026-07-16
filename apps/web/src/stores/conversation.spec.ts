import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useConversationStore } from './conversation'

const createDeferred = <T>() => {
  let resolve!: (value: T | PromiseLike<T>) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

vi.mock('../api/conversations', () => {
  const conversation = {
    id: 'conversation-1',
    title: '新对话',
    agent_id: null,
    created_at: '2026-07-16T00:00:00Z',
    updated_at: '2026-07-16T00:00:00Z',
  }
  return {
    ApiError: class ApiError extends Error {},
    listAgents: vi.fn(async () => ({ role: 'teacher', auto_agent_id: 'auto', agents: [] })),
    listConversations: vi.fn(async () => []),
    createConversation: vi.fn(async () => conversation),
    listMessages: vi.fn(async () => []),
    listAttachments: vi.fn(async () => []),
    deleteConversation: vi.fn(async () => undefined),
    uploadAttachment: vi.fn(),
    routeMessage: vi.fn(),
    getConversation: vi.fn(),
  }
})

vi.mock('../api/stream', () => ({
  streamMessage: vi.fn(async function* () {}),
}))

describe('conversation store', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('does not restore a pending upload into a new draft conversation', async () => {
    setActivePinia(createPinia())
    const store = useConversationStore()
    store.token = 'workspace-token'
    store.selectedAgentId = 'auto'

    const deferred = createDeferred<unknown>()
    const { uploadAttachment } = await import('../api/conversations')
    vi.mocked(uploadAttachment).mockReturnValueOnce(deferred.promise as never)

    const uploadPromise = store.uploadFile(
      new File(['hello'], '学情研判_Python课程_测试数据.xlsx'),
      'workspace',
    )

    await Promise.resolve()
    store.beginDraftConversation()
    deferred.resolve({
      id: 'attachment-1',
      conversation_id: 'conversation-1',
      filename: '学情研判_Python课程_测试数据.xlsx',
      content_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      size_bytes: 12,
      scope: 'workspace',
      status: 'parsing',
      status_message: null,
      extracted_chars: 0,
      created_at: '2026-07-16T00:00:00Z',
      updated_at: '2026-07-16T00:00:00Z',
    })

    await uploadPromise

    expect(store.activeConversationId).toBeNull()
    expect(store.attachments).toEqual([])
  })
})
