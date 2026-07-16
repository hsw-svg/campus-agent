import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  ApiError,
  createConversation,
  deleteConversation,
  listAgents,
  listAttachments,
  listConversations,
  listMessages,
  uploadAttachment,
  type Agent,
  type Attachment,
  type AttachmentScope,
  type Conversation,
  type Message,
} from '../api/conversations'
import { streamMessage } from '../api/stream'
import type { WorkspaceRole } from '../workspaces'

// The shell shows in-flight replies before the server-side ids exist, so drafts
// are the same shape as ``Message`` with a synthetic id and a ``pending`` flag.
export interface DraftMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent_id: string | null
  artifacts: unknown[] | null
  pending?: boolean
}

export interface RouteConfirmation {
  content: string
  candidates: Agent[]
}

let draftCounter = 0
const nextDraftId = (): string => `draft-${(draftCounter += 1)}`

function toDraft(message: Message): DraftMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    agent_id: message.agent_id,
    artifacts: message.artifacts,
  }
}

export const useConversationStore = defineStore('conversation', () => {
  const token = ref<string | null>(null)
  const role = ref<WorkspaceRole | null>(null)
  const conversations = ref<Conversation[]>([])
  const messages = ref<DraftMessage[]>([])
  const attachments = ref<Attachment[]>([])
  const agents = ref<Agent[]>([])
  const autoAgentId = ref('auto')
  const activeConversationId = ref<string | null>(null)
  const selectedAgentId = ref<string>('auto')
  const isStreaming = ref(false)
  const streamError = ref<string | null>(null)
  const notice = ref<string | null>(null)
  const agentRunLabel = ref<string | null>(null)
  const activeAgentRunId = ref<string | null>(null)
  const routeConfirmation = ref<RouteConfirmation | null>(null)
  let activeAbort: AbortController | null = null

  const activeConversation = computed(
    () => conversations.value.find((item) => item.id === activeConversationId.value) ?? null,
  )
  const isDraftConversation = computed(() => activeConversationId.value === null)

  function reset(): void {
    // Wipe every slot so a role switch never leaks the previous role's context.
    token.value = null
    role.value = null
    conversations.value = []
    messages.value = []
    attachments.value = []
    agents.value = []
    autoAgentId.value = 'auto'
    activeConversationId.value = null
    selectedAgentId.value = 'auto'
    isStreaming.value = false
    streamError.value = null
    notice.value = null
    agentRunLabel.value = null
    activeAgentRunId.value = null
    routeConfirmation.value = null
  }

  async function activateRole(nextRole: WorkspaceRole, nextToken: string): Promise<void> {
    reset()
    token.value = nextToken
    role.value = nextRole
    await Promise.all([refreshConversations(), refreshAgents()])
  }

  async function refreshAgents(): Promise<void> {
    if (!token.value) return
    const response = await listAgents(token.value)
    agents.value = response.agents
    autoAgentId.value = response.auto_agent_id
    if (
      selectedAgentId.value !== autoAgentId.value &&
      !agents.value.some((agent) => agent.id === selectedAgentId.value)
    ) {
      selectedAgentId.value = autoAgentId.value
    }
  }

  async function refreshConversations(): Promise<void> {
    if (!token.value) return
    conversations.value = await listConversations(token.value)
  }

  async function openConversation(conversationId: string): Promise<void> {
    if (!token.value) return
    activeConversationId.value = conversationId
    streamError.value = null
    const history = await listMessages(token.value, conversationId)
    messages.value = history.map(toDraft)
    attachments.value = await listAttachments(token.value, conversationId)
    const conversation = conversations.value.find((item) => item.id === conversationId)
    selectedAgentId.value = conversation?.agent_id ?? autoAgentId.value
  }

  function beginDraftConversation(): void {
    activeConversationId.value = null
    messages.value = []
    attachments.value = []
    streamError.value = null
    selectedAgentId.value = autoAgentId.value
  }

  function resolveAgentSelection(): string | null {
    return selectedAgentId.value === autoAgentId.value ? null : selectedAgentId.value
  }

  async function sendMessage(rawContent: string): Promise<void> {
    const content = rawContent.trim()
    if (!content || !token.value || isStreaming.value) return

    let conversationId = activeConversationId.value
    if (!conversationId) {
      try {
        const created = await createConversation(token.value, resolveAgentSelection())
        conversations.value = [created, ...conversations.value]
        activeConversationId.value = created.id
        conversationId = created.id
      } catch (error) {
        streamError.value = error instanceof Error ? error.message : '无法创建对话。'
        return
      }
    }

    const agentId = resolveAgentSelection()
    const userDraft: DraftMessage = {
      id: nextDraftId(),
      role: 'user',
      content,
      agent_id: agentId,
      artifacts: null,
    }
    const assistantDraft: DraftMessage = {
      id: nextDraftId(),
      role: 'assistant',
      content: '',
      agent_id: agentId,
      artifacts: null,
      pending: true,
    }
    messages.value = [...messages.value, userDraft, assistantDraft]
    isStreaming.value = true
    streamError.value = null
    agentRunLabel.value = null
    activeAgentRunId.value = null
    routeConfirmation.value = null
    activeAbort = new AbortController()

    try {
      for await (const event of streamMessage({
        token: token.value,
        conversationId,
        content,
        agentId,
        signal: activeAbort.signal,
      })) {
        if (event.type === 'message_start') {
          if (typeof event.data.run_id === 'string') activeAgentRunId.value = event.data.run_id
          if (typeof event.data.agent_id === 'string') assistantDraft.agent_id = event.data.agent_id
          messages.value = [...messages.value]
        } else if (event.type === 'delta') {
          const text = typeof event.data.text === 'string' ? event.data.text : ''
          assistantDraft.content += text
          // Force the list reference to change so Vue re-renders the draft.
          messages.value = [...messages.value]
        } else if (event.type === 'tool_status') {
          const status = event.data.status
          if (status === 'agent_routed' && typeof event.data.agent_name === 'string') {
            agentRunLabel.value = `已调用：${event.data.agent_name}`
          } else if (status === 'route_confirmation_required') {
            const ids = Array.isArray(event.data.candidates)
              ? event.data.candidates.filter((id): id is string => typeof id === 'string')
              : []
            routeConfirmation.value = {
              content,
              candidates: agents.value.filter((agent) => ids.includes(agent.id)),
            }
          }
        } else if (event.type === 'error') {
          const code = event.data.code
          const message =
            typeof event.data.message === 'string' ? event.data.message : '生成回复时出错。'
          streamError.value = message
          if (code === 'route_confirmation_required' && !routeConfirmation.value) {
            const ids = Array.isArray(event.data.candidates)
              ? event.data.candidates.filter((id): id is string => typeof id === 'string')
              : []
            routeConfirmation.value = {
              content,
              candidates: agents.value.filter((agent) => ids.includes(agent.id)),
            }
          }
        } else if (event.type === 'artifact') {
          assistantDraft.artifacts = [event.data]
          messages.value = [...messages.value]
        }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        streamError.value = '已停止生成。'
      } else {
        streamError.value = error instanceof Error ? error.message : '生成回复时出错。'
      }
    } finally {
      assistantDraft.pending = false
      isStreaming.value = false
      activeAbort = null
      // Replace drafts with the server's persisted rows so ids and timestamps
      // reflect what other tabs would see after a refresh.
      await refreshConversations()
      if (activeConversationId.value === conversationId) {
        try {
          const history = await listMessages(token.value, conversationId)
          messages.value = history.map(toDraft)
          attachments.value = await listAttachments(token.value, conversationId)
        } catch {
          // A background refresh must never wipe a visible reply.
        }
      }
    }
  }

  async function confirmAgent(agentId: string): Promise<void> {
    const pending = routeConfirmation.value
    if (!pending || isStreaming.value) return
    routeConfirmation.value = null
    streamError.value = null
    selectedAgentId.value = agentId
    await sendMessage(pending.content)
  }

  async function uploadFile(file: File, scope: AttachmentScope): Promise<void> {
    if (!token.value) return
    let conversationId = activeConversationId.value
    if (!conversationId) {
      try {
        const created = await createConversation(token.value, resolveAgentSelection())
        conversations.value = [created, ...conversations.value]
        activeConversationId.value = created.id
        conversationId = created.id
      } catch (error) {
        streamError.value = error instanceof Error ? error.message : '无法创建对话。'
        return
      }
    }
    try {
      const attachment = await uploadAttachment(token.value, conversationId, file, scope)
      attachments.value = [...attachments.value, attachment]
      streamError.value = null
    } catch (error) {
      streamError.value = error instanceof Error ? error.message : '附件上传失败。'
    }
  }

  function stopStreaming(): void {
    activeAbort?.abort()
  }

  async function removeConversation(conversationId: string): Promise<void> {
    if (!token.value) return
    try {
      await deleteConversation(token.value, conversationId)
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 404) throw error
    }
    conversations.value = conversations.value.filter((item) => item.id !== conversationId)
    if (activeConversationId.value === conversationId) {
      beginDraftConversation()
    }
  }

  return {
    token,
    role,
    conversations,
    messages,
    attachments,
    agents,
    autoAgentId,
    activeConversationId,
    selectedAgentId,
    isStreaming,
    streamError,
    notice,
    agentRunLabel,
    activeAgentRunId,
    routeConfirmation,
    activeConversation,
    isDraftConversation,
    reset,
    activateRole,
    refreshAgents,
    refreshConversations,
    openConversation,
    beginDraftConversation,
    sendMessage,
    confirmAgent,
    stopStreaming,
    removeConversation,
    uploadFile,
  }
})
