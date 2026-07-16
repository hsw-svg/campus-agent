<script setup lang="ts">
import { ref } from 'vue'
import { Collection, DataAnalysis, Document, Lock, MagicStick } from '@element-plus/icons-vue'
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

const roles: Array<{ id: WorkspaceRole; title: string; detail: string; icon: typeof Collection }> = [
  { id: 'student', title: '学生助手', detail: '个人学习与求职材料', icon: Collection },
  { id: 'teacher', title: '教师助手', detail: '教学设计与匿名学情分析', icon: DataAnalysis },
  { id: 'admin', title: '行政助手', detail: '会议材料与文稿整理', icon: Document },
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
  <main class="workspace-home inspira-grid" aria-label="校园智能助手">
    <div class="home-shell">
      <header class="topbar">
        <div class="brand-lockup">
          <span class="brand-mark"><MagicStick /></span>
          <span>校园智能助手</span>
        </div>
        <div class="privacy-pill"><Lock /> <span>匿名工作空间</span></div>
      </header>

      <section class="workspace-header inspira-fade-up" aria-labelledby="workspace-title">
        <div class="section-kicker"><span class="kicker-line"></span>个人工作空间</div>
        <h1 id="workspace-title">选择工作空间</h1>
        <p class="hero-copy">从一个角色开始，资料、对话与成果都会留在各自的空间里。</p>
        <p class="notice" role="status">{{ notice }}</p>
      </section>

      <section class="role-grid" aria-label="角色工作空间">
        <button
          v-for="(role, index) in roles"
          :key="role.id"
          class="role-option inspira-surface inspira-shimmer"
          :class="[`role-${role.id}`, { pending: pendingRole === role.id }]"
          :style="{ '--delay': `${index * 90}ms` }"
          :disabled="isLoading"
          type="button"
          @click="enterWorkspace(role.id)"
        >
          <span class="role-icon"><component :is="role.icon" /></span>
          <span class="role-title">{{ role.title }}</span>
          <small>{{ role.detail }}</small>
        </button>
      </section>

      <footer class="home-footer">
        <span>你的资料，你的空间</span>
        <span class="footer-dot"></span>
        <span>无需登录 · 无需注册</span>
      </footer>
    </div>
  </main>
</template>

<style scoped>
.workspace-home { min-height: 100vh; padding: 28px 32px; color: var(--ink); }
.home-shell { width: min(1120px, 100%); min-height: calc(100vh - 56px); margin: 0 auto; display: flex; flex-direction: column; }
.topbar, .brand-lockup, .privacy-pill, .home-footer { display: flex; align-items: center; }
.topbar { justify-content: space-between; margin-bottom: clamp(72px, 13vh, 150px); }
.brand-lockup { gap: 10px; color: #315149; font-size: 14px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.brand-mark { width: 30px; height: 30px; display: grid; place-items: center; border: 1px solid #a8c4b7; border-radius: 9px; background: #e0f2e9; color: var(--forest); }
.brand-mark svg { width: 16px; }
.privacy-pill { gap: 6px; padding: 7px 11px; border: 1px solid #d2dfd9; border-radius: 999px; background: rgba(251, 253, 251, .72); color: #6b7a76; font-size: 13px; }
.privacy-pill svg { width: 13px; color: var(--forest); }
.workspace-header { max-width: 680px; }
.section-kicker { display: flex; align-items: center; gap: 9px; color: var(--forest); font-size: 12px; font-weight: 800; letter-spacing: .16em; }
.kicker-line { width: 28px; height: 1px; background: var(--forest); }
h1 { max-width: 650px; margin: 18px 0 14px; color: #10211c; font-size: clamp(42px, 6vw, 74px); font-weight: 700; letter-spacing: -.045em; line-height: .98; }
.hero-copy { max-width: 470px; margin: 0; color: #5f716b; font-size: 17px; line-height: 1.75; }
.notice { min-height: 22px; margin: 18px 0 0; color: var(--amber); font-size: 14px; line-height: 1.5; }
.role-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 42px; }
.role-option { position: relative; min-height: 270px; padding: 18px 20px 20px; border-radius: 14px; color: var(--ink); text-align: left; cursor: pointer; transition: transform 220ms ease, border-color 220ms ease, box-shadow 220ms ease; animation: inspira-fade-up 520ms calc(180ms + var(--delay)) cubic-bezier(.2,.8,.2,1) both; }
.role-option:hover, .role-option.pending { border-color: #80b6a0; box-shadow: 0 20px 48px rgba(23, 100, 72, .15); transform: translateY(-5px); }
.role-option:disabled { cursor: wait; opacity: .7; }
.role-student { --role-accent: #247b5a; }
.role-teacher { --role-accent: #3b6f8f; }
.role-admin { --role-accent: #aa7132; }
.role-icon { width: 48px; height: 48px; display: grid !important; place-items: center; margin-top: 18px; border: 1px solid color-mix(in srgb, var(--role-accent), white 50%); border-radius: 13px; background: color-mix(in srgb, var(--role-accent), white 88%); color: var(--role-accent); }
.role-icon svg { width: 22px; }
.role-title { display: block; margin-top: 19px; color: #18332a; font-size: 24px; font-weight: 700; letter-spacing: -.03em; }
.role-option small { display: block; margin-top: 7px; color: #71807b; font-size: 14px; line-height: 1.5; }
.home-footer { gap: 10px; margin-top: auto; padding-top: 72px; color: #84938e; font-size: 11px; font-weight: 800; letter-spacing: .13em; }
.footer-dot { width: 4px; height: 4px; border-radius: 50%; background: #9db8ad; }
@media (max-width: 760px) { .workspace-home { padding: 20px; } .home-shell { min-height: calc(100vh - 40px); } .topbar { margin-bottom: 70px; } h1 { font-size: clamp(42px, 14vw, 64px); } .role-grid { grid-template-columns: 1fr; margin-top: 30px; } .role-option { min-height: 208px; } .role-icon { margin-top: 18px; } .home-footer { padding-top: 44px; padding-bottom: 10px; } }
@media (max-width: 420px) { .privacy-pill span { display: none; } .privacy-pill { padding: 8px; } .home-footer { flex-wrap: wrap; line-height: 1.5; } }
</style>
