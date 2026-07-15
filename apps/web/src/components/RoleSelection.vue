<script setup lang="ts">
import { ref } from 'vue'
import {
  createWorkspace,
  getCurrentWorkspace,
  WorkspaceApiError,
} from '../workspace-api'
import {
  clearWorkspaceHistory,
  getWorkspaceToken,
  saveWorkspaceToken,
  type WorkspaceRole,
} from '../workspaces'

const emit = defineEmits<{
  (event: 'entered', payload: { role: WorkspaceRole; token: string }): void
}>()

const roles: Array<{ id: WorkspaceRole; title: string; detail: string }> = [
  { id: 'student', title: '学生助手', detail: '个人学习与求职材料' },
  { id: 'teacher', title: '教师助手', detail: '教学设计与匿名学情分析' },
  { id: 'admin', title: '行政助手', detail: '会议材料与文稿整理' },
]

const isLoading = ref(false)
const notice = ref('请选择一个角色以创建或恢复本机工作空间。')
const pendingRole = ref<WorkspaceRole | null>(null)

async function enterWorkspace(role: WorkspaceRole): Promise<void> {
  if (isLoading.value) return
  isLoading.value = true
  pendingRole.value = role
  try {
    const existingToken = getWorkspaceToken(role)
    if (existingToken) {
      try {
        await getCurrentWorkspace(existingToken)
        emit('entered', { role, token: existingToken })
        return
      } catch (error) {
        if (!(error instanceof WorkspaceApiError) || error.status !== 401) throw error
        clearWorkspaceHistory(role)
        notice.value = '本地凭据已失效，正在为该角色创建新工作空间。'
      }
    }

    const created = await createWorkspace(role)
    saveWorkspaceToken(role, created.token)
    emit('entered', { role, token: created.token })
  } catch (error) {
    notice.value = error instanceof Error ? error.message : '无法连接工作空间服务。'
  } finally {
    isLoading.value = false
    pendingRole.value = null
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
        :class="{ pending: pendingRole === role.id }"
        :disabled="isLoading"
        type="button"
        @click="enterWorkspace(role.id)"
      >
        <span>{{ role.title }}</span>
        <small>{{ role.detail }}</small>
      </button>
    </section>
  </main>
</template>

<style scoped>
.workspace-home { max-width: 960px; margin: 0 auto; padding: 72px 24px; color: #1b2730; }
.workspace-header { max-width: 620px; }
.eyebrow { margin: 0; color: #39785e; font-weight: 700; }
h1 { margin: 8px 0 12px; font-size: 32px; font-weight: 700; }
.notice { margin: 0; color: #52616b; line-height: 1.6; }
.role-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 36px; }
.role-option { min-height: 136px; padding: 20px; border: 1px solid #c9d5cf; border-radius: 6px; background: #fff; color: inherit; text-align: left; cursor: pointer; }
.role-option:hover, .role-option.pending { border-color: #26734f; background: #f2f8f4; }
.role-option:disabled { cursor: wait; opacity: 0.7; }
.role-option span, .role-option small { display: block; }
.role-option span { font-size: 18px; font-weight: 700; }
.role-option small { margin-top: 10px; color: #607079; line-height: 1.5; }
@media (max-width: 680px) { .workspace-home { padding: 40px 20px; } .role-grid { grid-template-columns: 1fr; } }
</style>
