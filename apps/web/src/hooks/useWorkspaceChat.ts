import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ApiError,
  createConversation,
  deleteConversation,
  deleteCourseAgentHistory,
  getArtifact,
  listArtifacts,
  listConversationAttachments,
  listCourseAgentHistory,
  listConversations,
  listMessages,
  listWorkspaceAttachments,
  progressStepFromEvent,
  streamMessage,
  sourceCitationsFromEvent,
  uploadAttachment,
  uploadWorkspaceAttachment,
  type ApiMessage,
  type AgentHistoryItem,
  type Artifact,
  type Attachment,
  type AgentProgressStep,
  type Conversation,
  type CourseContext,
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

export interface PreparedTaskRequest {
  content: string
  agentId: string
  files: File[]
  courseContext: CourseContext
  onStarted?: () => void
}

interface RunMessageOptions {
  rawContent: string
  requestedAgentId: string | null
  initialConversationId: string | null
  initialAttachmentIds: string[]
  artifactIds: string[]
  requestCourseContext?: CourseContext
  createCourseId?: string | null
  createChapterId?: string | null
  parentRunId?: string | null
  stagedFiles?: File[]
  rollbackCreatedConversationOnFailure?: boolean
  onStarted?: () => void
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

function artifactIdsFromMessages(messages: ApiMessage[]): string[] {
  const ids = messages.flatMap((message) => (
    Array.isArray(message.artifacts)
      ? message.artifacts.flatMap((item) => {
        if (!item || typeof item !== 'object' || Array.isArray(item)) return []
        const artifactId = (item as Record<string, unknown>).artifact_id
        return typeof artifactId === 'string' ? [artifactId] : []
      })
      : []
  ))
  return [...new Set(ids)]
}

function mergeAttachments(current: Attachment[], incoming: Attachment[]): Attachment[] {
  const byId = new Map(current.map((item) => [item.id, item]))
  incoming.forEach((item) => byId.set(item.id, item))
  return [...byId.values()].sort((left, right) => left.created_at.localeCompare(right.created_at))
}

function isAttachmentVisibleForCourse(attachment: Attachment, courseId: string | null): boolean {
  return attachment.course_id === null || attachment.course_id === courseId
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

const MAX_PROGRESS_STEPS = 8

function mergeProgressStep(current: AgentProgressStep[], incoming: AgentProgressStep): AgentProgressStep[] {
  const index = current.findIndex((step) => step.id === incoming.id)
  if (index < 0) return [...current, incoming].slice(-MAX_PROGRESS_STEPS)
  return current.map((step, stepIndex) => stepIndex === index ? incoming : step)
}

function completeProgressSteps(
  current: AgentProgressStep[],
  state: 'completed' | 'failed',
  label?: string,
): AgentProgressStep[] {
  return current.map((step) => step.state === 'active'
    ? { ...step, state, label: label ?? step.label }
    : step)
}

export function useWorkspaceChat(token: string | null, courseContext?: CourseContext) {
  const [chatMessages, setChatMessages] = useState<Message[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationsLoaded, setConversationsLoaded] = useState(false)
  const [workspaceAttachments, setWorkspaceAttachments] = useState<Attachment[]>([])
  const [conversationAttachments, setConversationAttachments] = useState<Attachment[]>([])
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [agentHistory, setAgentHistory] = useState<AgentHistoryItem[]>([])
  const [citations, setCitations] = useState<SourceCitation[]>([])
  const [selectedAttachmentIds, setSelectedAttachmentIds] = useState<string[]>([])
  const [selectedArtifactIds, setSelectedArtifactIds] = useState<string[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [isAiTyping, setIsAiTyping] = useState(false)
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [route, setRoute] = useState<RouteState | null>(null)
  const [toolStatus, setToolStatus] = useState<string | null>(null)
  const [progressSteps, setProgressSteps] = useState<AgentProgressStep[]>([])
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const loadVersionRef = useRef(0)
  const streamFailedRef = useRef(false)
  const streamCompletedRef = useRef(false)
  const lastPromptRef = useRef('')
  const activeRequestSignatureRef = useRef<string | null>(null)
  const resourceVersionRef = useRef(0)
  const workspaceResourceVersionRef = useRef(0)
  const agentHistoryVersionRef = useRef(0)
  const currentCourseIdRef = useRef<string | null>(courseContext?.courseId ?? null)
  currentCourseIdRef.current = courseContext?.courseId ?? null

  const refreshConversations = useCallback(async () => {
    if (!token) return
    try {
      setConversations(await listConversations(token))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法读取对话列表。')
    } finally {
      setConversationsLoaded(true)
    }
  }, [token])

  const refreshWorkspaceAttachments = useCallback(async () => {
    if (!token) return
    const resourceVersion = ++workspaceResourceVersionRef.current
    try {
      const resources = await listWorkspaceAttachments(token, courseContext?.courseId)
      if (resourceVersion !== workspaceResourceVersionRef.current) return
      setWorkspaceAttachments(resources)
      if (courseContext?.courseId) {
        setSelectedAttachmentIds(resources.map((resource) => resource.id))
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法读取工作区资料库。')
    }
  }, [token, courseContext?.courseId])

  const refreshAgentHistory = useCallback(async () => {
    const courseId = courseContext?.courseId
    const historyVersion = ++agentHistoryVersionRef.current
    if (!token || !courseId) {
      setAgentHistory([])
      return
    }
    try {
      const history = await listCourseAgentHistory(token, courseId)
      if (historyVersion !== agentHistoryVersionRef.current) return
      setAgentHistory(history)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法读取课程智能体历史。')
    }
  }, [token, courseContext?.courseId])

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
    setProgressSteps([])
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
      const latestAgentId = [...history].reverse().find((message) => message.agent_id)?.agent_id
        ?? conversations.find((item) => item.id === conversationId)?.agent_id
        ?? null
      setRoute(latestAgentId ? {
        agentId: latestAgentId,
        agentName: null,
        confidence: 0,
        reason: '从历史任务恢复最近一次调用的智能体',
        selectionSource: 'history',
        missingInputs: [],
        candidates: [],
        runId: null,
      } : null)
      const referencedArtifactIds = artifactIdsFromMessages(history)
      if (referencedArtifactIds.length > 0) {
        const referencedArtifacts = await Promise.all(
          referencedArtifactIds.map((artifactId) => getArtifact(token, artifactId).catch(() => null)),
        )
        if (loadVersion !== loadVersionRef.current) return
        setArtifacts((current) => {
          const byId = new Map(current.map((artifact) => [artifact.id, artifact]))
          referencedArtifacts.forEach((artifact) => {
            if (artifact) byId.set(artifact.id, artifact)
          })
          return [...byId.values()]
        })
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法读取对话内容。')
    }
  }, [conversations, token, refreshResources])

  useEffect(() => {
    loadVersionRef.current += 1
    resourceVersionRef.current += 1
    workspaceResourceVersionRef.current += 1
    agentHistoryVersionRef.current += 1
    abortRef.current?.abort()
    setChatMessages([])
    setConversations([])
    setConversationsLoaded(!token)
    setWorkspaceAttachments([])
    setConversationAttachments([])
    setArtifacts([])
    setAgentHistory([])
    setCitations([])
    setSelectedAttachmentIds([])
    setSelectedArtifactIds([])
    setActiveConversationId(null)
    setRoute(null)
    setRunStatus('idle')
    setProgressSteps([])
    setError(null)
    if (token) {
      void refreshConversations()
    }
    return () => abortRef.current?.abort()
  }, [token, refreshConversations])

  useEffect(() => {
    loadVersionRef.current += 1
    resourceVersionRef.current += 1
    workspaceResourceVersionRef.current += 1
    agentHistoryVersionRef.current += 1
    abortRef.current?.abort()
    setChatMessages([])
    setWorkspaceAttachments([])
    setConversationAttachments([])
    setArtifacts([])
    setAgentHistory([])
    setCitations([])
    setSelectedAttachmentIds([])
    setSelectedArtifactIds([])
    setActiveConversationId(null)
    setRoute(null)
    setRunStatus('idle')
    setToolStatus(null)
    setProgressSteps([])
    setError(null)
    if (token) {
      void refreshWorkspaceAttachments()
      void refreshAgentHistory()
    }
  }, [token, courseContext?.courseId, refreshWorkspaceAttachments, refreshAgentHistory])

  const clearChat = useCallback(() => {
    loadVersionRef.current += 1
    resourceVersionRef.current += 1
    abortRef.current?.abort()
    setActiveConversationId(null)
    setChatMessages([])
    setConversationAttachments([])
    setArtifacts([])
    setCitations([])
    setSelectedAttachmentIds(courseContext?.courseId
      ? workspaceAttachments.filter((attachment) => isAttachmentVisibleForCourse(attachment, courseContext.courseId)).map((attachment) => attachment.id)
      : [])
    setSelectedArtifactIds([])
    setRoute(null)
    setRunStatus('idle')
    setToolStatus(null)
    setProgressSteps([])
    setError(null)
  }, [courseContext?.courseId, workspaceAttachments])

  const attachments = useMemo(
    () => mergeAttachments(conversationAttachments, workspaceAttachments)
      .filter((attachment) => isAttachmentVisibleForCourse(attachment, courseContext?.courseId ?? null)),
    [conversationAttachments, courseContext?.courseId, workspaceAttachments],
  )

  useEffect(() => {
    if (!courseContext?.courseId) return
    const allAttachmentIds = attachments.map((attachment) => attachment.id)
    setSelectedAttachmentIds((current) => {
      if (current.length === allAttachmentIds.length && current.every((id, index) => id === allAttachmentIds[index])) {
        return current
      }
      return allAttachmentIds
    })
  }, [attachments, courseContext?.courseId, courseContext?.workflowId])

  const runMessage = useCallback(async ({
    rawContent,
    requestedAgentId,
    initialConversationId,
    initialAttachmentIds,
    artifactIds,
    requestCourseContext,
    createCourseId,
    createChapterId,
    parentRunId,
    stagedFiles = [],
    rollbackCreatedConversationOnFailure = false,
    onStarted,
  }: RunMessageOptions): Promise<boolean> => {
    const content = rawContent.trim()
    let requestAttachmentIds = [...initialAttachmentIds]
    const requestSignature = [
      content,
      requestCourseContext?.courseId ?? '',
      requestCourseContext?.chapterId ?? '',
      requestCourseContext?.workflowId ?? '',
      requestedAgentId ?? '',
      ...requestAttachmentIds.slice().sort(),
      ...artifactIds.slice().sort(),
      ...stagedFiles.map((file) => `${file.name}:${file.size}:${file.lastModified}`),
    ].join('|')
    if (!token || !content || isAiTyping || activeRequestSignatureRef.current === requestSignature) return false
    activeRequestSignatureRef.current = requestSignature
    lastPromptRef.current = content
    setError(null)
    setRunStatus('running')
    setToolStatus('正在连接智能体')
    setProgressSteps([{
      id: 'connection',
      phase: 'routing',
      state: 'active',
      label: '正在连接智能体',
      detail: null,
      count: null,
    }])
    setCitations([])
    let conversationId = initialConversationId
    let createdConversationId: string | null = null
    let executionStarted = false
    try {
      if (!conversationId) {
        const created = await createConversation(token, createCourseId, createChapterId)
        conversationId = created.id
        createdConversationId = created.id
        setConversations((current) => [created, ...current])
        setActiveConversationId(conversationId)
        setConversationAttachments([])
        setArtifacts([])
      }

      if (stagedFiles.length > 0) {
        setToolStatus(`正在上传资料（0/${stagedFiles.length}）`)
        const uploaded: Attachment[] = []
        for (const [index, file] of stagedFiles.entries()) {
          const attachment = await uploadAttachment(token, conversationId, file, 'conversation')
          if (attachment.status === 'failed') {
            throw new Error(attachment.status_message || `“${file.name}”上传后解析失败。`)
          }
          uploaded.push(attachment)
          setToolStatus(`正在上传资料（${index + 1}/${stagedFiles.length}）`)
        }
        requestAttachmentIds = uploaded.map((attachment) => attachment.id)
        setConversationAttachments(uploaded)
        setSelectedAttachmentIds(requestAttachmentIds)
      }

      executionStarted = true
      onStarted?.()

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
        agentId: requestedAgentId,
        selectedAttachmentIds: requestAttachmentIds,
        selectedArtifactIds: artifactIds,
        courseContext: requestCourseContext,
        parentRunId,
        inputRefs: [
          ...requestAttachmentIds.map((id) => `attachment:${id}`),
          ...artifactIds.map((id) => `artifact:${id}`),
        ],
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
          refreshAgentHistory(),
        ])
        setChatMessages(history.map(toUiMessage))
        await refreshConversations()
      }
      return true
    } catch (reason) {
      if (!executionStarted && rollbackCreatedConversationOnFailure && createdConversationId) {
        try {
          await deleteConversation(token, createdConversationId)
        } catch {
          await refreshConversations()
        }
        setConversations((current) => current.filter((item) => item.id !== createdConversationId))
        setActiveConversationId(null)
        setConversationAttachments([])
        setSelectedAttachmentIds([])
      }
      if (reason instanceof DOMException && reason.name === 'AbortError') {
        setRunStatus('stopped')
        setProgressSteps((current) => completeProgressSteps(current, 'failed', '已停止，已保留当前内容'))
        setToolStatus('已停止，已保留当前内容')
      } else {
        const needsInput = reason instanceof ApiError && (reason.code === 'agent_input_incomplete' || reason.code === 'needs_input' || reason.code?.includes('input') || reason.code === 'route_confirmation_required')
        setProgressSteps((current) => completeProgressSteps(current, 'failed', needsInput ? '需要补充资料' : '任务执行失败'))
        setRunStatus(needsInput ? 'needs_input' : 'failed')
        setError(reason instanceof Error ? reason.message : '生成回复时出错。')
      }
      return false
    } finally {
      setIsAiTyping(false)
      abortRef.current = null
      activeRequestSignatureRef.current = null
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
        const progressStep = progressStepFromEvent(event)
        if (progressStep) {
          setProgressSteps((current) => mergeProgressStep(current, progressStep))
          setToolStatus(progressStep.label)
        } else {
          setToolStatus(typeof event.data.status === 'string' ? event.data.status : '处理中')
        }
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
        setProgressSteps((current) => completeProgressSteps(current, 'failed', '任务执行失败'))
        setRunStatus(failure.code === 'agent_input_incomplete' || failure.code?.includes('input') ? 'needs_input' : 'failed')
        const missingInputs = Array.isArray(event.data.missing_inputs)
          ? event.data.missing_inputs.filter((item): item is string => typeof item === 'string')
          : []
        setError(missingInputs.length > 0 ? `${failure.message} 缺少：${missingInputs.join('、')}` : failure.message)
      } else if (event.type === 'done') {
        if (!streamFailedRef.current) {
          streamCompletedRef.current = true
          setProgressSteps((current) => completeProgressSteps(current, 'completed'))
          setRunStatus('completed')
          setToolStatus('已完成')
        }
      }
    }
  }, [isAiTyping, refreshAgentHistory, refreshConversations, refreshResources, refreshWorkspaceAttachments, token])

  const sendMessage = useCallback(async (rawContent: string, requestedAgentId: string | null = null) => {
    const requestAttachmentIds = courseContext?.courseId
      ? attachments.map((attachment) => attachment.id)
      : selectedAttachmentIds
    return runMessage({
      rawContent,
      requestedAgentId,
      initialConversationId: activeConversationId,
      initialAttachmentIds: requestAttachmentIds,
      artifactIds: selectedArtifactIds,
      requestCourseContext: courseContext,
      createCourseId: courseContext?.courseId,
      createChapterId: courseContext?.chapterId,
      parentRunId: route?.runId ?? null,
    })
  }, [activeConversationId, attachments, courseContext, route?.runId, runMessage, selectedArtifactIds, selectedAttachmentIds])

  const startPreparedTask = useCallback(async (request: PreparedTaskRequest) => runMessage({
    rawContent: request.content,
    requestedAgentId: request.agentId,
    initialConversationId: null,
    initialAttachmentIds: [],
    artifactIds: [],
    requestCourseContext: request.courseContext,
    createCourseId: null,
    createChapterId: null,
    parentRunId: null,
    stagedFiles: request.files,
    rollbackCreatedConversationOnFailure: true,
    onStarted: request.onStarted,
  }), [runMessage])

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      setRunStatus('stopped')
      setProgressSteps((current) => completeProgressSteps(current, 'failed', '已停止，已保留当前内容'))
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

  const uploadFile = useCallback(async (
    file: File,
    scope: 'conversation' | 'workspace' = 'conversation',
    workspaceCourseId: string | null = courseContext?.courseId ?? null,
  ): Promise<Attachment | null> => {
    if (!token) return null
    try {
      let attachment: Attachment
      if (scope === 'workspace') {
        attachment = await uploadWorkspaceAttachment(token, file, workspaceCourseId)
        if (currentCourseIdRef.current === workspaceCourseId) {
          setWorkspaceAttachments((current) => mergeAttachments(current, [attachment]))
          if (workspaceCourseId) {
            setSelectedAttachmentIds((current) => current.includes(attachment.id) ? current : [...current, attachment.id])
          }
        }
      } else {
        let conversationId = activeConversationId
        if (!conversationId) {
          const created = await createConversation(token, courseContext?.courseId, courseContext?.chapterId)
          conversationId = created.id
          setConversations((current) => [created, ...current])
          setActiveConversationId(conversationId)
        }
        attachment = await uploadAttachment(token, conversationId, file, 'conversation')
        setConversationAttachments((current) => mergeAttachments(current, [attachment]))
        if (courseContext?.courseId) {
          setSelectedAttachmentIds((current) => current.includes(attachment.id) ? current : [...current, attachment.id])
        }
      }
      setError(null)
      return attachment
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '附件上传失败。')
      return null
    }
  }, [token, activeConversationId, courseContext?.courseId, courseContext?.chapterId])

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

  const removeAgentHistory = useCallback(async (runId: string) => {
    const courseId = courseContext?.courseId
    if (!token || !courseId) return
    try {
      await deleteCourseAgentHistory(token, courseId, runId)
      setAgentHistory((current) => current.filter((item) => item.run_id !== runId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '删除智能体记录失败。')
    }
  }, [token, courseContext?.courseId])

  return {
    chatMessages,
    setChatMessages,
    conversations,
    conversationsLoaded,
    attachments,
    workspaceAttachments,
    conversationAttachments,
    artifacts,
    agentHistory,
    citations,
    selectedAttachmentIds,
    selectedArtifactIds,
    activeConversationId,
    isAiTyping,
    runStatus,
    route,
    toolStatus,
    progressSteps,
    setIsAiTyping,
    clearChat,
    sendMessage,
    startPreparedTask,
    retryLastMessage,
    stopStreaming,
    uploadFile,
    toggleAttachment,
    toggleArtifact,
    openConversation,
    removeConversation,
    removeAgentHistory,
    refreshResources,
    refreshWorkspaceAttachments,
    error,
  }
}
