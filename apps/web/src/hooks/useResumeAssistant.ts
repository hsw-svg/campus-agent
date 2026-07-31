import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ApiError,
  deleteResumeAnalysis,
  getResumeProfile,
  initializeDefaultCourses,
  listResumeAnalyses,
  setCurrentResume,
  streamResumeAnalysis,
  uploadWorkspaceAttachment,
  type Attachment,
  type CourseSummary,
  type ResumeAnalysisHistoryItem,
} from '../api'

export type ResumeAnalysisStatus = 'idle' | 'running' | 'completed' | 'failed' | 'stopped'

interface AnalysisRequestSnapshot {
  attachmentId: string
  targetRole: string
  jobDescription: string
  selectedCourseIds: string[]
}

export function useResumeAssistant(token: string | null) {
  const [currentResume, setCurrentResumeState] = useState<Attachment | null>(null)
  const [uploadResult, setUploadResult] = useState<Attachment | null>(null)
  const [courses, setCourses] = useState<CourseSummary[]>([])
  const [selectedCourseIds, setSelectedCourseIds] = useState<string[]>([])
  const [history, setHistory] = useState<ResumeAnalysisHistoryItem[]>([])
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [targetRole, setTargetRole] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [status, setStatus] = useState<ResumeAnalysisStatus>('idle')
  const [toolStatus, setToolStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const selectionInitializedRef = useRef(false)
  const lastRequestRef = useRef<AnalysisRequestSnapshot | null>(null)

  const activeHistory = useMemo(
    () => history.find((item) => item.run_id === activeRunId)
      ?? history.find((item) => item.artifact)
      ?? history[0]
      ?? null,
    [activeRunId, history],
  )

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const [profile, courseItems, analysisItems] = await Promise.all([
        getResumeProfile(token),
        initializeDefaultCourses(token),
        listResumeAnalyses(token),
      ])
      setCurrentResumeState(profile.current_resume)
      setCourses(courseItems)
      setHistory(analysisItems)
      const latest = analysisItems.find((item) => item.artifact) ?? analysisItems[0] ?? null
      setActiveRunId(latest?.run_id ?? null)
      if (!selectionInitializedRef.current) {
        setSelectedCourseIds(courseItems.filter((course) => course.started).map((course) => course.id))
        selectionInitializedRef.current = true
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '简历助手加载失败。')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    selectionInitializedRef.current = false
    abortRef.current?.abort()
    setCurrentResumeState(null)
    setUploadResult(null)
    setCourses([])
    setSelectedCourseIds([])
    setHistory([])
    setActiveRunId(null)
    setTargetRole('')
    setJobDescription('')
    setStatus('idle')
    setToolStatus(null)
    setError(null)
    if (token) void load()
    return () => abortRef.current?.abort()
  }, [load, token])

  const uploadResume = useCallback(async (file: File) => {
    if (!token || uploading) return
    setUploading(true)
    setError(null)
    setUploadResult(null)
    try {
      const attachment = await uploadWorkspaceAttachment(token, file)
      setUploadResult(attachment)
      if (
        !['indexed', 'degraded'].includes(attachment.status)
        || attachment.extracted_chars <= 0
      ) {
        setError(attachment.status_message ?? '该文件没有可用于分析的文本。')
        return
      }
      const profile = await setCurrentResume(token, attachment.id)
      setCurrentResumeState(profile.current_resume)
      setUploadResult(profile.current_resume)
      setStatus('idle')
      setToolStatus('简历解析完成，请确认分析设置。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '简历上传失败。')
    } finally {
      setUploading(false)
    }
  }, [token, uploading])

  const refreshHistory = useCallback(async (preferredRunId?: string | null) => {
    if (!token) return []
    const items = await listResumeAnalyses(token)
    setHistory(items)
    const preferred = preferredRunId
      ? items.find((item) => item.run_id === preferredRunId)
      : null
    const next = preferred ?? items.find((item) => item.artifact) ?? items[0] ?? null
    setActiveRunId(next?.run_id ?? null)
    return items
  }, [token])

  const runAnalysis = useCallback(async (snapshot?: AnalysisRequestSnapshot) => {
    if (!token || !currentResume || status === 'running') return
    const request = snapshot ?? {
      attachmentId: currentResume.id,
      targetRole,
      jobDescription,
      selectedCourseIds,
    }
    lastRequestRef.current = request
    setError(null)
    setStatus('running')
    setToolStatus('正在核对简历与课程学习证据')
    const controller = new AbortController()
    abortRef.current = controller
    let completedRunId: string | null = null
    let streamFailed = false
    try {
      for await (const event of streamResumeAnalysis({
        token,
        attachmentId: request.attachmentId,
        targetRole: request.targetRole,
        jobDescription: request.jobDescription,
        selectedCourseIds: request.selectedCourseIds,
        signal: controller.signal,
      })) {
        if (event.type === 'message_start' && typeof event.data.run_id === 'string') {
          completedRunId = event.data.run_id
          setActiveRunId(completedRunId)
        } else if (event.type === 'tool_status') {
          setToolStatus(toolStatusLabel(event.data.status))
        } else if (event.type === 'error') {
          streamFailed = true
          setStatus('failed')
          setError(typeof event.data.message === 'string' ? event.data.message : '简历分析失败。')
        } else if (event.type === 'done') {
          setStatus('completed')
          setToolStatus('简历优化报告已生成')
        }
      }
      await refreshHistory(completedRunId)
      if (!streamFailed && !controller.signal.aborted) setStatus('completed')
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === 'AbortError') {
        setStatus('stopped')
        setToolStatus('已停止本次分析')
      } else {
        setStatus('failed')
        setError(reason instanceof ApiError || reason instanceof Error ? reason.message : '简历分析失败。')
      }
      await refreshHistory(completedRunId).catch(() => [])
    } finally {
      abortRef.current = null
    }
  }, [
    currentResume,
    jobDescription,
    refreshHistory,
    selectedCourseIds,
    status,
    targetRole,
    token,
  ])

  const retryAnalysis = useCallback(() => {
    if (lastRequestRef.current) void runAnalysis(lastRequestRef.current)
    else void runAnalysis()
  }, [runAnalysis])

  const stopAnalysis = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const toggleCourse = useCallback((course: CourseSummary) => {
    if (!course.started) return
    setSelectedCourseIds((current) => current.includes(course.id)
      ? current.filter((id) => id !== course.id)
      : [...current, course.id])
  }, [])

  const openHistory = useCallback((item: ResumeAnalysisHistoryItem) => {
    setActiveRunId(item.run_id)
    const input = item.artifact?.data.input
    if (!input) return
    setTargetRole(input.target_role ?? '')
    setJobDescription(input.job_description ?? '')
    setSelectedCourseIds(input.selected_courses.map((course) => course.course_id))
  }, [])

  const removeHistory = useCallback(async (runId: string) => {
    if (!token) return
    setError(null)
    try {
      await deleteResumeAnalysis(token, runId)
      const remaining = history.filter((item) => item.run_id !== runId)
      setHistory(remaining)
      if (activeRunId === runId) {
        setActiveRunId((remaining.find((item) => item.artifact) ?? remaining[0])?.run_id ?? null)
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '删除简历分析记录失败。')
    }
  }, [activeRunId, history, token])

  return {
    currentResume,
    uploadResult,
    courses,
    selectedCourseIds,
    history,
    activeHistory,
    activeRunId,
    targetRole,
    jobDescription,
    loading,
    uploading,
    status,
    toolStatus,
    error,
    setTargetRole,
    setJobDescription,
    uploadResume,
    runAnalysis,
    retryAnalysis,
    stopAnalysis,
    toggleCourse,
    openHistory,
    removeHistory,
  }
}

function toolStatusLabel(value: unknown): string {
  switch (value) {
    case 'agent_routed': return '已进入简历优化智能体'
    case 'retrieved': return '已读取当前简历全文'
    default: return typeof value === 'string' ? value : '正在分析'
  }
}
