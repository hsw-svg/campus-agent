import { afterEach, describe, expect, it } from 'vitest'
import {
  clearWorkspaceHistory,
  getWorkspaceToken,
  saveWorkspaceToken,
} from './workspaces'

describe('workspace token storage', () => {
  afterEach(() => {
    localStorage.clear()
  })

  it('keeps a separate token for each role', () => {
    saveWorkspaceToken('student', 'student-token')
    saveWorkspaceToken('teacher', 'teacher-token')

    expect(getWorkspaceToken('student')).toBe('student-token')
    expect(getWorkspaceToken('teacher')).toBe('teacher-token')
    expect(getWorkspaceToken('admin')).toBeNull()
  })

  it('clears local history for a single role', () => {
    saveWorkspaceToken('student', 'student-token')
    saveWorkspaceToken('teacher', 'teacher-token')
    localStorage.setItem('campus-agent.history.student', '[]')
    localStorage.setItem('campus-agent.history.teacher', '[]')

    clearWorkspaceHistory('student')

    expect(getWorkspaceToken('student')).toBeNull()
    expect(localStorage.getItem('campus-agent.history.student')).toBeNull()
    expect(getWorkspaceToken('teacher')).toBe('teacher-token')
    expect(localStorage.getItem('campus-agent.history.teacher')).toBe('[]')
  })
})
