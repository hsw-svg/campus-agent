<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  createWorkspace,
  deleteCurrentWorkspace,
  getCurrentWorkspace,
  WorkspaceApiError,
  type Workspace,
} from './workspace-api'
import {
  clearWorkspaceHistory,
  getWorkspaceToken,
  saveWorkspaceToken,
  type WorkspaceRole,
} from './workspaces'

const roles: Array<{ id: WorkspaceRole; title: string; detail: string }> = [
  { id: 'student', title: '学生助手', detail: '个人学习与求职材料' },
  { id: 'teacher', title: '教师助手', detail: '教学设计与匿名学情分析' },
  { id: 'admin', title: '行政助手', detail: '会议材料与文稿整理' },
]

const activeWorkspace = ref<Workspace | null>(null)
const isLoading = ref(false)
const notice = ref('请选择一个角色以创建或恢复本机工作空间。')
const activeRole = computed(() => activeWorkspace.value?.role ?? null)

async function enterWorkspace(role: WorkspaceRole): Promise<void> {
  isLoading.value = true
  try {
    const existingToken = getWorkspaceToken(role)
    if (existingToken) {
      try {
        activeWorkspace.value = await getCurrentWorkspace(existingToken)
        notice.value = `已恢复${roles.find((item) => item.id === role)?.title}的本机工作空间。`
        return
      } catch (error) {
        if (!(error instanceof WorkspaceApiError) || error.status !== 401) throw error
        clearWorkspaceHistory(role)
        activeWorkspace.value = null
        notice.value = '工作空间凭据已失效，请重新选择角色。'
        return
      }
    }

    const created = await createWorkspace(role)
    saveWorkspaceToken(role, created.token)
    activeWorkspace.value = created.workspace
    notice.value = `已创建${roles.find((item) => item.id === role)?.title}的独立工作空间。`
  } catch (error) {
    notice.value = error instanceof Error ? error.message : '无法连接工作空间服务。'
  } finally {
    isLoading.value = false
  }
}

async function removeActiveWorkspace(): Promise<void> {
  if (!activeWorkspace.value) return

  const role = activeWorkspace.value.role
  const token = getWorkspaceToken(role)
  isLoading.value = true
  try {
    if (token) await deleteCurrentWorkspace(token)
    clearWorkspaceHistory(role)
    activeWorkspace.value = null
    notice.value = '工作空间及此角色的本地历史已清理。'
  } catch (error) {
    if (error instanceof WorkspaceApiError && error.status === 401) {
      clearWorkspaceHistory(role)
      activeWorkspace.value = null
      notice.value = '工作空间凭据已失效，请重新选择角色。'
      return
    }
    notice.value = error instanceof Error ? error.message : '无法清理工作空间。'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="workspace-home" aria-label="校园 AI 助手">
    <section class="workspace-header" aria-labelledby="workspace-title">
      <p class="eyebrow">Campus Agent</p>
      <h1 id="workspace-title">选择工作空间</h1>
      <p class="notice" role="status">{{ notice }}</p>
    </section>

    <section class="role-grid" aria-label="角色工作空间">
      <button
        v-for="role in roles"
        :key="role.id"
        class="role-option"
        :class="{ active: activeRole === role.id }"
        :disabled="isLoading"
        type="button"
        @click="enterWorkspace(role.id)"
      >
        <span>{{ role.title }}</span>
        <small>{{ role.detail }}</small>
      </button>
    </section>

    <section v-if="activeWorkspace" class="current-workspace" aria-label="当前工作空间">
      <div>
        <strong>当前：{{ roles.find((role) => role.id === activeWorkspace?.role)?.title }}</strong>
        <p>该空间与其他角色的会话、文件和本地历史相互隔离。</p>
      </div>
      <button class="clear-button" :disabled="isLoading" type="button" @click="removeActiveWorkspace">
        清理此空间
      </button>
    </section>
  </main>
</template>

<style scoped>
.workspace-home { max-width: 960px; margin: 0 auto; padding: 72px 24px; color: #1b2730; }
.workspace-header { max-width: 620px; }
.eyebrow { margin: 0; color: #39785e; font-weight: 700; }
h1 { margin: 8px 0 12px; font-size: 32px; font-weight: 700; letter-spacing: 0; }
.notice { margin: 0; color: #52616b; line-height: 1.6; }
.role-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 36px; }
.role-option { min-height: 136px; padding: 20px; border: 1px solid #c9d5cf; border-radius: 6px; background: #fff; color: inherit; text-align: left; cursor: pointer; }
.role-option:hover, .role-option.active { border-color: #26734f; background: #f2f8f4; }
.role-option:disabled { cursor: wait; opacity: 0.7; }
.role-option span, .role-option small { display: block; }
.role-option span { font-size: 18px; font-weight: 700; }
.role-option small { margin-top: 10px; color: #607079; line-height: 1.5; }
.current-workspace { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-top: 24px; padding: 18px 0; border-top: 1px solid #dce4df; }
.current-workspace p { margin: 6px 0 0; color: #52616b; }
.clear-button { border: 1px solid #b84c4c; border-radius: 4px; padding: 8px 12px; background: #fff; color: #9e3434; cursor: pointer; white-space: nowrap; }
@media (max-width: 680px) { .workspace-home { padding: 40px 20px; } .role-grid { grid-template-columns: 1fr; } .current-workspace { align-items: flex-start; flex-direction: column; } }
</style>
