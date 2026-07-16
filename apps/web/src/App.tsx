/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import RoleSelector from './components/RoleSelector';
import TeacherWorkspace from './components/TeacherWorkspace';
import StudentWorkspace from './components/StudentWorkspace';
import AdminWorkspace from './components/AdminWorkspace';
import { ApiError, createWorkspace, getCurrentWorkspace } from './api';
import { Role, WorkspaceRole } from './types';

const tokenKey = (role: WorkspaceRole) => `campus-agent.workspace-token.${role}`;

export default function App() {
  const [activeRole, setActiveRole] = useState<Role>(null);
  const [workspaceToken, setWorkspaceToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const handleSelectRole = async (role: WorkspaceRole) => {
    if (isLoading) return;
    setIsLoading(true);
    setNotice(null);
    try {
      const storedToken = localStorage.getItem(tokenKey(role));
      if (storedToken) {
        try {
          await getCurrentWorkspace(storedToken);
          setWorkspaceToken(storedToken);
          setActiveRole(role);
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
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '无法连接工作空间服务。');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToRoles = () => {
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
