/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import RoleSelector from './components/RoleSelector';
import TeacherWorkspace from './components/TeacherWorkspace';
import StudentWorkspace from './components/StudentWorkspace';
import AdminWorkspace from './components/AdminWorkspace';
import { ApiError, createWorkspace, getCurrentWorkspace } from './api';
import { Role, WorkspaceRole } from './types';

const tokenKey = (role: WorkspaceRole) => `campus-agent.workspace-token.${role}`;
const ACTIVE_ROLE_KEY = 'campus-agent.active-role';

function isWorkspaceRole(value: string | null): value is WorkspaceRole {
  return value === 'teacher' || value === 'student' || value === 'admin';
}

export default function App() {
  const [activeRole, setActiveRole] = useState<Role>(null);
  const [workspaceToken, setWorkspaceToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const resumeAttemptedRef = useRef(false);

  const activateRole = useCallback(async (role: WorkspaceRole) => {
    setIsLoading(true);
    setNotice(null);
    try {
      const storedToken = localStorage.getItem(tokenKey(role));
      if (storedToken) {
        try {
          await getCurrentWorkspace(storedToken);
          setWorkspaceToken(storedToken);
          setActiveRole(role);
          sessionStorage.setItem(ACTIVE_ROLE_KEY, role);
          return;
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 401) throw error;
          localStorage.removeItem(tokenKey(role));
        }
      }
      const created = await createWorkspace(role);
      localStorage.setItem(tokenKey(role), created.token);
      setWorkspaceToken(created.token);
      setActiveRole(role);
      sessionStorage.setItem(ACTIVE_ROLE_KEY, role);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '无法连接工作空间服务。');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (resumeAttemptedRef.current) return;
    resumeAttemptedRef.current = true;
    const storedRole = sessionStorage.getItem(ACTIVE_ROLE_KEY);
    if (isWorkspaceRole(storedRole)) void activateRole(storedRole);
  }, [activateRole]);

  const handleSelectRole = async (role: WorkspaceRole) => {
    if (isLoading) return;
    await activateRole(role);
  };

  const handleBackToRoles = () => {
    sessionStorage.removeItem(ACTIVE_ROLE_KEY);
    setActiveRole(null);
    setWorkspaceToken(null);
  };

  return (
    <>
      {activeRole === null && (
        <RoleSelector onSelectRole={handleSelectRole} isLoading={isLoading} notice={notice} />
      )}
      {activeRole === 'teacher' && (
        <TeacherWorkspace token={workspaceToken} onBackToRoles={handleBackToRoles} />
      )}
      {activeRole === 'student' && (
        <StudentWorkspace token={workspaceToken} onBackToRoles={handleBackToRoles} />
      )}
      {activeRole === 'admin' && (
        <AdminWorkspace token={workspaceToken} onBackToRoles={handleBackToRoles} />
      )}
    </>
  );
}
