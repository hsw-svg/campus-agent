/**
 * Student-specific API client.
 *
 * Keep all student-only API calls here. Import shared types from ./api but
 * avoid importing teacher/admin-specific functions — this file is owned by
 * the student-dev branch and should never conflict with teacher/admin work.
 */

import type { Artifact, ApiError as _ApiError } from './api'
import { ApiError } from './api'

export type { Artifact }

export interface StudentCourse {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface StudentAgentHistoryItem {
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

async function studentRequest<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      ...(token ? { 'X-Workspace-Token': token } : {}),
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null) as {
      error?: { code?: string; message?: string; details?: Record<string, unknown> | null }
    } | null
    throw new ApiError(
      response.status,
      body?.error?.message ?? '请求失败，请稍后重试。',
      body?.error?.code,
      body?.error?.details,
    )
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

/** Fetch the list of courses available to the student workspace. */
export function listStudentCourses(token: string): Promise<StudentCourse[]> {
  return studentRequest<StudentCourse[]>('/courses', undefined, token)
}

/** Fetch recent agent run history for the current student workspace. */
export function listStudentAgentHistory(token: string): Promise<StudentAgentHistoryItem[]> {
  return studentRequest<StudentAgentHistoryItem[]>('/student-agents/history', undefined, token)
}

/** Delete a single student agent run from history. */
export function deleteStudentAgentHistory(token: string, runId: string): Promise<void> {
  return studentRequest<void>(`/student-agents/history/${runId}`, { method: 'DELETE' }, token)
}
