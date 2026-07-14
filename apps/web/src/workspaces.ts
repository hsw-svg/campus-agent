export const workspaceRoles = ['student', 'teacher', 'admin'] as const

export type WorkspaceRole = (typeof workspaceRoles)[number]

const tokenKey = (role: WorkspaceRole) => `campus-agent.workspace-token.${role}`
const historyKey = (role: WorkspaceRole) => `campus-agent.history.${role}`

export function getWorkspaceToken(role: WorkspaceRole): string | null {
  return localStorage.getItem(tokenKey(role))
}

export function saveWorkspaceToken(role: WorkspaceRole, token: string): void {
  localStorage.setItem(tokenKey(role), token)
}

export function clearWorkspaceHistory(role: WorkspaceRole): void {
  localStorage.removeItem(tokenKey(role))
  localStorage.removeItem(historyKey(role))
}
