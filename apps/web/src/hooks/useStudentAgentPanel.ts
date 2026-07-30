/**
 * useStudentAgentPanel — student-only hook for the agent history side panel.
 *
 * Mirrors the teacher-side agent history pattern but is completely self-contained:
 * it imports only from studentApi and standard React, never from useWorkspaceChat
 * or teacher-specific modules. This keeps the student-dev branch conflict-free.
 */

import { useState, useCallback, useEffect } from 'react'
import {
  listStudentAgentHistory,
  deleteStudentAgentHistory,
  type StudentAgentHistoryItem,
} from '../studentApi'

interface UseStudentAgentPanelOptions {
  token: string | null
  /** Whether the panel is currently visible; set to true to trigger a refresh. */
  open: boolean
}

interface UseStudentAgentPanelResult {
  history: StudentAgentHistoryItem[]
  loading: boolean
  error: string | null
  /** Manually trigger a reload from the server. */
  refresh: () => void
  /** Remove a run from history (optimistic + server delete). */
  removeHistoryItem: (runId: string) => Promise<void>
}

export function useStudentAgentPanel({
  token,
  open,
}: UseStudentAgentPanelOptions): UseStudentAgentPanelResult {
  const [history, setHistory] = useState<StudentAgentHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    if (!token) return
    setLoading(true)
    setError(null)
    listStudentAgentHistory(token)
      .then((items) => setHistory(items))
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : '历史记录加载失败，请稍后重试。')
      })
      .finally(() => setLoading(false))
  }, [token])

  // Reload whenever the panel opens
  useEffect(() => {
    if (open) refresh()
  }, [open, refresh])

  const removeHistoryItem = useCallback(
    async (runId: string) => {
      if (!token) return
      // Optimistic removal
      setHistory((prev) => prev.filter((item) => item.run_id !== runId))
      try {
        await deleteStudentAgentHistory(token, runId)
      } catch (err: unknown) {
        // Revert on failure and surface the error
        refresh()
        setError(err instanceof Error ? err.message : '删除失败，请稍后重试。')
      }
    },
    [token, refresh],
  )

  return { history, loading, error, refresh, removeHistoryItem }
}
