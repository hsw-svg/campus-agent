import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ApiError,
  createConversation,
  deleteConversation,
  listArtifacts,
  listConversationAttachments,
  listConversations,
  listMessages,
  listWorkspaceAttachments,
  streamMessage,
  sourceCitationsFromEvent,
  uploadAttachment,
  uploadWorkspaceAttachment,
  type ApiMessage,
  type Artifact,
  type Attachment,
  type Conversation,
  type StreamEvent,
  type SourceCitation,
} from '../api'
import type { Message } from '../types'

export type RunStatus = 'idle' | 'running' | 'completed' | 'needs_input' | 'failed' | 'stopped'

export interface RouteState {
  agentId: string | null
  agentName: string | null
  confidence: number
  reason: string
  selectionSource: string
  missingInputs: string[]
  candidates: string[]
  runId: string | null
}

function displayTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.valueOf())
    ? ''
    : date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function toUiMessage(message: ApiMessage): Message {
  return {
    id: message.id,
    sender: message.role,
    content: message.content,
    timestamp: displayTime(message.created_at),
    type: 'text',
    metadata: message.artifacts,
  }
}

function mergeAttachments(current: Attachment[], incoming: Attachment[]): Attachment[] {
  const byId = new Map(current.map((item) => [item.id, item]))
  incoming.forEach((item) => byId.set(item.id, item))
  return [...byId.values()].sort((left, right) => left.created_at.localeCompare(right.created_at))
}

function eventError(event: StreamEvent): ApiError {
  const message = typeof event.data.message === 'string' ? event.data.message : '生成回复时出错。'
  const details = event.data.details && typeof event.data.details === 'object'
    ? event.data.details as Record<string, unknown>
    : null
  return new ApiError(
    422,
    message,
    typeof event.data.code === 'string' ? event.data.code : undefined,
    details,
  )
}

export function useWorkspaceChat(token: string | null) {
  const [chatMessages, setChatMessages] = useState<Message[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [workspaceAttachments, setWorkspaceAttachments] = useState<Attachment[]>([])
  const [conversationAttachments, setConversationAttachments] = useState<Attachment[]>([])
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [citations, setCitations] = useState<SourceCitation[]>([])
  const [selectedAttachmentIds, setSelectedAttachmentIds] = useState<string[]>([])
  const [selectedArtifactIds, setSelectedArtifactIds] = useState<string[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [isAiTyping, setIsAiTyping] = useState(false)
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [route, setRoute] = useState<RouteState | null>(null)
  const [toolStatus, setToolStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const loadVersionRef = useRef(0)
  const streamFailedRef = useRef(false)
  const streamCompletedRef = useRef(false)
  const lastPromptRef = useRef('')
  const resourceVersionRef = useRef(0)
  const workspaceResourceVersionRef = useRef(0)

  const refreshConversations = useCallback(async () => {
    if (!token) return
    try {
      setConversations(await listConversations(token))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法读取对话列表。')
    }
  }, [token])

  const refreshWorkspaceAttachments = useCallback(async () => {
    if (!token) return
    const resourceVersion = ++workspaceResourceVersionRef.current
    try {
      const resources = await listWorkspaceAttachments(token)
      if (resourceVersion !== workspaceResourceVersionRef.current) return
      setWorkspaceAttachments(resources)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法读取工作区资料库。')
    }
  }, [token])

  const refreshResources = useCallback(async (conversationId: string) => {
    if (!token) return
    const resourceVersion = ++resourceVersionRef.current
    const [current, conversationArtifacts] = await Promise.all([
      listConversationAttachments(token, conversationId),
      listArtifacts(token, conversationId),
    ])
    if (resourceVersion !== resourceVersionRef.current) return
    setConversationAttachments(current)
    setArtifacts(conversationArtifacts)
  }, [token])

  const openConversation = useCallback(async (conversationId: string) => {
    if (!token) return
    const loadVersion = ++loadVersionRef.current
    abortRef.current?.abort()
    setIsAiTyping(false)
    setError(null)
    setActiveConversationId(conversationId)
    setChatMessages([])
    setConversationAttachments([])
    setArtifacts([])
    setToolStatus(null)
    setCitations([])
    setSelectedAttachmentIds([])
    setSelectedArtifactIds([])
    setRoute(null)
    setRunStatus('idle')
    try {
      const [history] = await Promise.all([
        listMessages(token, conversationId),
        refreshResources(conversationId),
      ])
      if (loadVersion !== loadVersionRef.current) return
      setChatMessages(history.map(toUiMessage))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法读取对话内容。')
    }
  }, [token, refreshResources])

  useEffect(() => {
    loadVersionRef.current += 1
    resourceVersionRef.current += 1
    workspaceResourceVersionRef.current += 1
    abortRef.current?.abort()
    setChatMessages([])
    setConversations([])
    setWorkspaceAttachments([])
    setConversationAttachments([])
    setArtifacts([])
    setCitations([])
    setSelectedAttachmentIds([])
    setSelectedArtifactIds([])
    setActiveConversationId(null)
    setRoute(null)
    setRunStatus('idle')
    setError(null)
    if (token) {
      void refreshConversations()
      void refreshWorkspaceAttachments()
    }
    return () => abortRef.current?.abort()
  }, [token, refreshConversations, refreshWorkspaceAttachments])

  const clearChat = useCallback(() => {
    loadVersionRef.current += 1
    resourceVersionRef.current += 1
    abortRef.current?.abort()
    setActiveConversationId(null)
    setChatMessages([])
    setConversationAttachments([])
    setArtifacts([])
    setCitations([])
    setSelectedAttachmentIds([])
    setSelectedArtifactIds([])
    setRoute(null)
    setRunStatus('idle')
    setToolStatus(null)
    setError(null)
  }, [])

  const sendMessage = useCallback(async (rawContent: string) => {
    const content = rawContent.trim()
    if (!token || !content || isAiTyping) return
    lastPromptRef.current = content
    setError(null)
    setRunStatus('running')
    setToolStatus('正在连接智能体')
    setCitations([])
    let conversationId = activeConversationId
    try {
      if (!conversationId) {
        const created = await createConversation(token)
        conversationId = created.id
        setConversations((current) => [created, ...current])
        setActiveConversationId(conversationId)
        setConversationAttachments([])
        setArtifacts([])
      }

      const userMessage: Message = {
        id: `draft-user-${Date.now()}`,
        sender: 'user',
        content,
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      }
      const assistantMessage: Message = {
        id: `draft-assistant-${Date.now()}`,
        sender: 'assistant',
        content: '',
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      }
      setChatMessages((current) => [...current, userMessage, assistantMessage])
      setIsAiTyping(true)
      const controller = new AbortController()
      abortRef.current = controller
      streamFailedRef.current = false
      streamCompletedRef.current = false

      for await (const event of streamMessage({
        token,
        conversationId,
        content,
        selectedAttachmentIds,
        selectedArtifactIds,
        signal: controller.signal,
      })) {
        handleStreamEvent(event, assistantMessage.id, conversationId)
      }

      if (!controller.signal.aborted && !streamCompletedRef.current && !streamFailedRef.current) {
        streamFailedRef.current = true
        setRunStatus('failed')
        setError('流式连接中断，已保留当前内容，请重试。')
      }

      if (conversationId && !controller.signal.aborted) {
        const [history] = await Promise.all([
          listMessages(token, conversationId),
          refreshResources(conversationId),
          refreshWorkspaceAttachments(),
        ])
        setChatMessages(history.map(toUiMessage))
        await refreshConversations()
      }
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === 'AbortError') {
        setRunStatus('stopped')
        setToolStatus('已停止，已保留当前内容')
      } else {
        const needsInput = reason instanceof ApiError && (reason.code === 'agent_input_incomplete' || reason.code === 'needs_input' || reason.code?.includes('input') || reason.code === 'route_confirmation_required')
        setRunStatus(needsInput ? 'needs_input' : 'failed')
        setError(reason instanceof Error ? reason.message : '生成回复时出错。')
      }
    } finally {
      setIsAiTyping(false)
      abortRef.current = null
    }

    function handleStreamEvent(event: StreamEvent, assistantId: string, currentConversationId: string) {
      if (event.type === 'message_start') {
        setRoute((current) => ({
          agentId: typeof event.data.agent_id === 'string' ? event.data.agent_id : current?.agentId ?? null,
          agentName: typeof event.data.agent_name === 'string' ? event.data.agent_name : current?.agentName ?? null,
          confidence: typeof event.data.confidence === 'number' ? event.data.confidence : current?.confidence ?? 0,
          reason: current?.reason ?? '',
          selectionSource: typeof event.data.selection_source === 'string' ? event.data.selection_source : current?.selectionSource ?? '',
          missingInputs: current?.missingInputs ?? [],
          candidates: current?.candidates ?? [],
          runId: typeof event.data.run_id === 'string' ? event.data.run_id : null,
        }))
      } else if (event.type === 'route_decision') {
        setRoute({
          agentId: typeof event.data.agent_id === 'string' ? event.data.agent_id : null,
          agentName: typeof event.data.agent_name === 'string' ? event.data.agent_name : null,
          confidence: typeof event.data.confidence === 'number' ? event.data.confidence : 0,
          reason: typeof event.data.reason === 'string' ? event.data.reason : '',
          selectionSource: typeof event.data.selection_source === 'string' ? event.data.selection_source : '',
          missingInputs: Array.isArray(event.data.missing_inputs) ? event.data.missing_inputs.filter((item): item is string => typeof item === 'string') : [],
          candidates: Array.isArray(event.data.candidates) ? event.data.candidates.filter((item): item is string => typeof item === 'string') : [],
          runId: typeof event.data.run_id === 'string' ? event.data.run_id : null,
        })
      } else if (event.type === 'tool_status') {
        setToolStatus(typeof event.data.status === 'string' ? event.data.status : '处理中')
      } else if (event.type === 'delta' && typeof event.data.text === 'string') {
        setChatMessages((current) => current.map((message) =>
          message.id === assistantId ? { ...message, content: message.content + event.data.text } : message,
        ))
      } else if (event.type === 'artifact') {
        const eventCitations = sourceCitationsFromEvent(event)
        if (eventCitations.length > 0) {
          setCitations(eventCitations)
          setToolStatus(`已读取 ${eventCitations.length} 条实际引用`)
          return
        }
        const artifactId = typeof event.data.artifact_id === 'string' ? event.data.artifact_id : null
        if (artifactId) {
          const now = new Date().toISOString()
          const liveArtifact: Artifact = {
            id: artifactId,
            workspace_id: '',
            conversation_id: currentConversationId,
            type: typeof event.data.type === 'string' ? event.data.type : 'artifact',
            title: typeof event.data.title === 'string' ? event.data.title : '课堂成果',
            content: '',
            data: event.data.data && typeof event.data.data === 'object' ? event.data.data as Record<string, unknown> : {},
            format: 'markdown',
            created_at: now,
            updated_at: now,
          }
          setArtifacts((current) => current.some((item) => item.id === artifactId)
            ? current.map((item) => item.id === artifactId ? { ...item, ...liveArtifact } : item)
            : [...current, liveArtifact])
        }
        setToolStatus('结构化成果已生成')
      } else if (event.type === 'error') {
        const failure = eventError(event)
        streamFailedRef.current = true
        setRunStatus(failure.code === 'agent_input_incomplete' || failure.code?.includes('input') ? 'needs_input' : 'failed')
        const missingInputs = Array.isArray(event.data.missing_inputs)
          ? event.data.missing_inputs.filter((item): item is string => typeof item === 'string')
          : []
        setError(missingInputs.length > 0 ? `${failure.message} 缺少：${missingInputs.join('、')}` : failure.message)
      } else if (event.type === 'done') {
        if (!streamFailedRef.current) {
          streamCompletedRef.current = true
          setRunStatus('completed')
          setToolStatus('已完成')
        }
      }
    }
  }, [activeConversationId, isAiTyping, refreshConversations, refreshResources, refreshWorkspaceAttachments, selectedArtifactIds, selectedAttachmentIds, token])

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      setRunStatus('stopped')
      setToolStatus('已停止，已保留当前内容')
    }
  }, [])

  const retryLastMessage = useCallback(() => {
    if (lastPromptRef.current) void sendMessage(lastPromptRef.current)
  }, [sendMessage])

  const toggleAttachment = useCallback((attachmentId: string) => {
    setSelectedAttachmentIds((current) => current.includes(attachmentId)
      ? current.filter((id) => id !== attachmentId)
      : [...current, attachmentId])
  }, [])

  const toggleArtifact = useCallback((artifactId: string) => {
    setSelectedArtifactIds((current) => current.includes(artifactId)
      ? current.filter((id) => id !== artifactId)
      : [...current, artifactId])
  }, [])

  const uploadFile = useCallback(async (file: File, scope: 'conversation' | 'workspace' = 'conversation') => {
    if (!token) return
    try {
      if (scope === 'workspace') {
        const attachment = await uploadWorkspaceAttachment(token, file)
        setWorkspaceAttachments((current) => mergeAttachments(current, [attachment]))
      } else {
        let conversationId = activeConversationId
        if (!conversationId) {
          const created = await createConversation(token)
          conversationId = created.id
          setConversations((current) => [created, ...current])
          setActiveConversationId(conversationId)
        }
        const attachment = await uploadAttachment(token, conversationId, file, 'conversation')
        setConversationAttachments((current) => mergeAttachments(current, [attachment]))
      }
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '附件上传失败。')
    }
  }, [token, activeConversationId])

  const removeConversation = useCallback(async (conversationId: string) => {
    if (!token) return
    try {
      await deleteConversation(token, conversationId)
      setConversations((current) => current.filter((item) => item.id !== conversationId))
      if (activeConversationId === conversationId) clearChat()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '删除对话失败。')
    }
  }, [token, activeConversationId, clearChat])

  const attachments = mergeAttachments(conversationAttachments, workspaceAttachments)

  return {
    chatMessages,
    setChatMessages,
    conversations,
    attachments,
    workspaceAttachments,
    conversationAttachments,
    artifacts,
    citations,
    selectedAttachmentIds,
    selectedArtifactIds,
    activeConversationId,
    isAiTyping,
    runStatus,
    route,
    toolStatus,
    setIsAiTyping,
    clearChat,
    sendMessage,
    retryLastMessage,
    stopStreaming,
    uploadFile,
    toggleAttachment,
    toggleArtifact,
    openConversation,
    removeConversation,
    refreshResources,
    refreshWorkspaceAttachments,
    error,
  }
}
