import type { WorkspaceRole } from './workspaces'

export interface Workspace {
  id: string
  role: WorkspaceRole
}

export interface CreatedWorkspace {
  workspace: Workspace
  token: string
}

export class WorkspaceApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/workspaces${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null) as {
      error?: { message?: string }
    } | null
    throw new WorkspaceApiError(response.status, body?.error?.message ?? 'Workspace request failed.')
  }
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>
}

export function createWorkspace(role: WorkspaceRole): Promise<CreatedWorkspace> {
  return request<CreatedWorkspace>('', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  })
}

export function getCurrentWorkspace(token: string): Promise<Workspace> {
  return request<Workspace>('/current', {
    headers: { 'X-Workspace-Token': token },
  })
}

export function deleteCurrentWorkspace(token: string): Promise<void> {
  return request<void>('/current', {
    method: 'DELETE',
    headers: { 'X-Workspace-Token': token },
  })
}
