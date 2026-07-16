<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick, type Component } from 'vue'
import { ChatDotRound, Collection, DataAnalysis, Delete, Document, FolderOpened, MagicStick, Paperclip, Plus, Promotion, Switch, VideoPause } from '@element-plus/icons-vue'
import { useConversationStore } from '../stores/conversation'
import type { Agent, Conversation } from '../api/conversations'

const emit = defineEmits<{ (event: 'switch-role'): void }>()
const store = useConversationStore()
const messageContainerRef = ref<HTMLElement | null>(null)
const inputText = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)
const attachmentScope = ref<'workspace'>('workspace')
const guideDetailTab = ref<'uploads' | 'capabilities'>('uploads')
let guideDetailTimer: ReturnType<typeof setInterval> | null = null

interface AssistantGuide {
  icon: Component
  eyebrow: string
  title: string
  description: string
  uploads: readonly string[]
  capabilities: readonly string[]
  templates: readonly string[]
}

const roleGuideContent = {
  student: {
    uploads: ['简历与求职材料', '课程笔记与作业', '项目经历与作品说明'],
    capabilities: ['梳理学习重点', '优化求职表达', '完善项目材料'],
    templates: ['帮我梳理这份课程笔记的重点。', '请帮我优化这段项目经历描述。', '根据我的简历，准备一组面试问答。'],
  },
  teacher: {
    uploads: ['课程大纲与教学设计', '课件、教案与讲义', '作业、测验与学情记录'],
    capabilities: ['生成教学设计', '分析学习情况', '整理课程与测评材料'],
    templates: ['根据这份课程大纲，帮我设计一节课。', '请分析这份作业记录中的共性问题。', '根据本节课目标，生成一份课堂练习。'],
  },
  admin: {
    uploads: ['会议纪要与通知', '制度文件与材料', '活动方案与工作台账'],
    capabilities: ['提炼会议要点', '撰写规范文稿', '整理工作材料'],
    templates: ['请将这份会议记录整理成待办清单。', '根据这些要点起草一则通知。', '帮我梳理这份活动方案的执行流程。'],
  },
} as const

function selectedAgent(): Agent | null {
  return store.agents.find((agent) => agent.id === store.selectedAgentId) ?? null
}

function guideIcon(agent: Agent | null): Component {
  if (!agent) return MagicStick
  const keywords = `${agent.id} ${agent.name} ${agent.description}`
  if (/分析|学情|数据/.test(keywords)) return DataAnalysis
  if (/资料|知识|检索|学习/.test(keywords)) return Collection
  return Document
}

const assistantGuide = computed<AssistantGuide>(() => {
  const content = roleGuideContent[store.role ?? 'student']
  const agent = selectedAgent()

  if (!agent) {
    return {
      icon: MagicStick,
      eyebrow: '自动识别',
      title: store.role === 'teacher' ? '为教学任务匹配合适助手' : '为当前任务匹配合适助手',
      description:
        store.role === 'teacher'
          ? '上传教学资料或直接提问，我会根据任务自动匹配合适的智能助手。'
          : '上传资料或直接提问，我会根据任务自动匹配合适的智能助手。',
      ...content,
    }
  }

  return {
    icon: guideIcon(agent),
    eyebrow: `正在使用：${agent.name}`,
    title: agent.name,
    description: agent.description || `由${agent.name}协助处理当前任务。`,
    ...content,
  }
})

const roleLabel = computed(() => {
  if (store.role === 'student') return '学生助手'
  if (store.role === 'teacher') return '教师助手'
  if (store.role === 'admin') return '行政助手'
  return ''
})

watch(
  () => store.messages.length,
  async () => {
    await nextTick()
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight
    }
  },
)

watch(
  () => store.selectedAgentId,
  () => {
    guideDetailTab.value = 'uploads'
  },
)

onMounted(() => {
  guideDetailTimer = setInterval(() => {
    if (!store.activeConversation && !store.isStreaming) {
      guideDetailTab.value = guideDetailTab.value === 'uploads' ? 'capabilities' : 'uploads'
    }
  }, 5000)
})

onUnmounted(() => {
  if (guideDetailTimer) clearInterval(guideDetailTimer)
})

function handleNewConversation(): void {
  store.beginDraftConversation()
  inputText.value = ''
}

function handleOpenConversation(conversation: Conversation): void {
  store.openConversation(conversation.id)
  inputText.value = ''
}

function handleSend(): void {
  if (!inputText.value.trim() || store.isStreaming) return
  store.sendMessage(inputText.value)
  inputText.value = ''
}

function handleTemplateQuestion(question: string): void {
  if (store.isStreaming) return
  inputText.value = question
  handleSend()
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey && !event.metaKey && !event.ctrlKey) {
    event.preventDefault()
    handleSend()
  }
}

function openFilePicker(): void {
  fileInputRef.value?.click()
}

async function handleFileSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) await store.uploadFile(file, attachmentScope.value)
}

function attachmentStatus(status: string): string {
  return {
    uploaded: '已上传',
    parsing: '解析中',
    indexed: '已索引',
    degraded: '降级检索',
    failed: '失败',
  }[status] ?? status
}

function sourceItems(message: { artifacts: unknown[] | null }): Array<{ filename: string; excerpt: string }> {
  const artifact = message.artifacts?.find(
    (item): item is { type?: unknown; sources?: unknown } =>
      typeof item === 'object' && item !== null && 'type' in item && (item as { type?: unknown }).type === 'sources',
  )
  if (!artifact || !Array.isArray(artifact.sources)) return []
  return artifact.sources.filter(
    (source): source is { filename: string; excerpt: string } =>
      typeof source === 'object' && source !== null &&
      typeof (source as { filename?: unknown }).filename === 'string' &&
      typeof (source as { excerpt?: unknown }).excerpt === 'string',
  )
}
</script>

<template>
  <div class="conversation-shell inspira-grid">
    <aside class="sidebar inspira-surface" aria-label="对话列表">
      <div class="sidebar-brand">
        <div class="brand-lockup"><span class="brand-mark"><ChatDotRound /></span><span>校园智能助手</span></div>
        <span class="online-dot" title="服务在线"></span>
      </div>
      <button class="new-button" type="button" @click="handleNewConversation"><Plus /><span>新建对话</span></button>
      <div class="sidebar-header">
        <div class="workspace-label"><span class="workspace-avatar">{{ roleLabel.slice(0, 1) }}</span><span><strong>{{ roleLabel }}</strong><small>当前工作空间</small></span></div>
        <button class="icon-button" type="button" title="切换角色" aria-label="切换角色" @click="emit('switch-role')"><Switch /></button>
      </div>
      <div class="list-heading"><span>最近对话</span><span>{{ store.conversations.length }}</span></div>
      <div class="conversation-list-wrap">
        <div v-if="!store.conversations.length" class="sidebar-empty"><FolderOpened /><span>还没有对话</span></div>
        <ul v-else class="conversation-list">
          <li
            v-for="conversation in store.conversations"
            :key="conversation.id"
            class="conversation-row"
            :class="{ active: store.activeConversationId === conversation.id }"
          >
            <button class="conversation-item" type="button" @click="handleOpenConversation(conversation)">
              <ChatDotRound /><span class="conversation-title">{{ conversation.title }}</span>
            </button>
            <button class="delete-button" type="button" title="删除对话" aria-label="删除对话" @click.stop="store.removeConversation(conversation.id)"><Delete /></button>
          </li>
        </ul>
      </div>
    </aside>

    <main class="main-area" aria-label="对话内容">
      <header class="conversation-meta">
        <div class="meta-copy">
          <div class="breadcrumb"><span>工作空间</span><span>/</span><strong>{{ roleLabel }}</strong></div>
          <h1>{{ store.activeConversation?.title ?? '新的对话' }}</h1>
        </div>
      </header>

      <div v-if="!store.activeConversation" class="empty-state inspira-fade-up">
        <div class="guide-summary">
          <div class="empty-orbit"><span></span><component :is="assistantGuide.icon" /></div>
          <div class="empty-kicker">{{ assistantGuide.eyebrow }}</div>
          <h2>{{ assistantGuide.title }}</h2>
          <p>{{ assistantGuide.description }}</p>
        </div>
        <div class="guide-details">
          <Transition name="guide-fade" mode="out-in">
            <section v-if="guideDetailTab === 'uploads'" key="uploads" class="guide-section" role="tabpanel">
              <h3>可上传资料</h3>
              <div class="guide-tags"><span v-for="item in assistantGuide.uploads" :key="item">{{ item }}</span></div>
            </section>
            <section v-else key="capabilities" class="guide-section" role="tabpanel">
              <h3>可以帮你完成</h3>
              <div class="guide-tags"><span v-for="item in assistantGuide.capabilities" :key="item">{{ item }}</span></div>
            </section>
          </Transition>
        </div>
        <section class="template-section" aria-label="推荐提问">
          <h3>试试这样问</h3>
          <div class="template-list">
            <button
              v-for="question in assistantGuide.templates"
              :key="question"
              class="template-question"
              type="button"
              :disabled="store.isStreaming"
              @click="handleTemplateQuestion(question)"
            >
              {{ question }}
            </button>
          </div>
        </section>
      </div>

      <div
        v-if="store.activeConversation"
        ref="messageContainerRef"
        class="message-container"
        aria-live="polite"
      >
        <article
          v-for="message in store.messages"
          :key="message.id"
          class="message"
          :class="message.role"
        >
          <div class="message-role">{{ message.role === 'user' ? '你' : '助手' }}</div>
          <div class="message-block"><div class="message-label">{{ message.role === 'user' ? '你' : '校园智能助手' }}</div><div class="message-content">{{ message.content }}</div></div>
          <div v-if="sourceItems(message).length" class="source-list">
            <span class="source-heading">资料来源</span>
            <div v-for="source in sourceItems(message)" :key="`${message.id}-${source.filename}-${source.excerpt}`" class="source-item">
              <strong>{{ source.filename }}</strong>
              <span>{{ source.excerpt }}</span>
            </div>
          </div>
        </article>
      </div>

      <div v-if="store.streamError" class="error-banner" role="alert">
        {{ store.streamError }}
      </div>

      <div v-if="store.activeConversation || store.messages.length === 0" class="input-area">
        <div v-if="store.attachments.length" class="attachment-list" aria-label="附件状态">
          <div v-for="attachment in store.attachments" :key="attachment.id" class="attachment-item">
            <span class="attachment-name">{{ attachment.filename }}</span>
            <span class="attachment-status" :class="attachment.status">{{ attachmentStatus(attachment.status) }}</span>
            <small v-if="attachment.status_message">{{ attachment.status_message }}</small>
          </div>
        </div>
        <div class="composer inspira-surface">
        <textarea
          v-model="inputText"
          class="input-field"
          placeholder="输入消息…"
          rows="3"
          :disabled="store.isStreaming"
          @keydown="handleKeydown"
        />
        <div class="input-actions">
          <input ref="fileInputRef" class="file-input" type="file" accept=".txt,.md,.docx,.pdf,.xlsx,.csv" @change="handleFileSelected" />
          <div class="agent-options" role="radiogroup" aria-label="选择智能体">
            <label class="agent-option">
              <input v-model="store.selectedAgentId" type="radio" :value="store.autoAgentId" name="selected-agent" />
              <span>自动识别</span>
            </label>
            <label v-for="agent in store.agents" :key="agent.id" class="agent-option">
              <input v-model="store.selectedAgentId" type="radio" :value="agent.id" name="selected-agent" />
              <span>{{ agent.name }}</span>
            </label>
          </div>
          <button class="attachment-button" type="button" title="添加附件" :disabled="store.isStreaming" @click="openFilePicker"><Paperclip /><span>添加附件</span></button>
          <button
            v-if="store.isStreaming"
            class="stop-button"
            type="button"
            @click="store.stopStreaming"
          >
            <VideoPause /><span>停止生成</span>
          </button>
          <button
            v-else
            class="send-button"
            type="button"
            :disabled="!inputText.trim()"
            @click="handleSend"
          >
            <Promotion /><span>发送</span>
          </button>
        </div>
        </div>
        <div class="composer-note"><span>按回车发送 · 使用组合键换行</span><span>内容会保存在当前匿名工作空间</span></div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.conversation-shell {
  display: flex;
  height: 100vh;
  color: #1b2730;
}
.sidebar {
  width: 280px;
  border-right: 1px solid #dce4df;
  background: #fbf9f5;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #dce4df;
}
.sidebar-actions {
  display: flex;
  gap: 8px;
}
.new-button,
.switch-button {
  border: 1px solid #26734f;
  border-radius: 4px;
  padding: 6px 12px;
  background: #fff;
  color: #26734f;
  cursor: pointer;
  font-size: 14px;
}
.switch-button {
  border-color: #607079;
  color: #607079;
}
.new-button:hover {
  background: #f2f8f4;
}
.switch-button:hover {
  background: #f0f2f3;
}
.conversation-list {
  flex: 1;
  overflow-y: auto;
  margin: 0;
  padding: 8px 0;
  list-style: none;
}
.conversation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  font-size: 14px;
}
.conversation-item:hover {
  background: #f2f8f4;
}
.conversation-item.active {
  background: #e7f3ed;
  font-weight: 600;
}
.conversation-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.delete-button {
  border: none;
  background: transparent;
  color: #b84c4c;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
  padding: 0 4px;
  margin-left: 8px;
}
.delete-button:hover {
  color: #9e3434;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.conversation-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #dce4df;
}
.conversation-meta h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #607079;
}

.message-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
.message {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 24px;
}
.message-role {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e7f3ed;
  font-size: 12px;
  font-weight: 600;
  color: #26734f;
}
.message.user .message-role {
  background: #f2e3d6;
  color: #a94e22;
}
.message-content {
  flex: 1;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.error-banner {
  padding: 12px 24px;
  background: #fdeaea;
  color: #9e3434;
  border-top: 1px solid #f5c6c6;
  font-size: 14px;
}

.input-area {
  border-top: 1px solid #dce4df;
  padding: 16px 24px;
}
.input-field {
  width: 100%;
  border: 1px solid #c9d5cf;
  border-radius: 6px;
  padding: 12px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  resize: vertical;
}
.input-field:focus {
  outline: none;
  border-color: #26734f;
}
.input-field:disabled {
  background: #f7f4ef;
  cursor: wait;
}
.input-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 8px;
}
.file-input { display: none; }
.attachment-button {
  border: 1px solid #c9d5cf;
  border-radius: 4px;
  padding: 8px 10px;
  background: #fff;
  color: #52616b;
  font-size: 13px;
}
.attachment-button { cursor: pointer; }
.attachment-button:hover { border-color: #26734f; color: #26734f; }
.attachment-button:disabled { cursor: wait; opacity: 0.6; }
.attachment-list { display: grid; gap: 6px; margin-bottom: 10px; }
.attachment-item { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; padding: 8px 10px; border-left: 3px solid #c9d5cf; background: #f7f9f7; font-size: 13px; }
.attachment-name { font-weight: 600; }
.attachment-status.indexed { color: #26734f; }
.attachment-status.degraded { color: #a1671c; }
.attachment-status.failed { color: #9e3434; }
.attachment-item small { flex-basis: 100%; color: #607079; }
.source-list { flex-basis: 100%; margin-left: 52px; padding: 10px 12px; border-left: 2px solid #c9d5cf; color: #52616b; font-size: 13px; }
.source-heading { display: block; margin-bottom: 6px; font-weight: 700; color: #26734f; }
.source-item { display: grid; gap: 2px; margin-top: 6px; }
.source-item span { line-height: 1.45; }
.send-button,
.stop-button {
  border: 1px solid #26734f;
  border-radius: 4px;
  padding: 8px 16px;
  background: #26734f;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
}
.send-button:hover {
  background: #1f5c3f;
}
.send-button:disabled {
  background: #c9d5cf;
  border-color: #c9d5cf;
  cursor: not-allowed;
}
.stop-button {
  background: #b84c4c;
  border-color: #b84c4c;
}
.stop-button:hover {
  background: #9e3434;
}
</style>

<style scoped>
.conversation-shell { min-height: 100vh; height: 100svh; gap: 14px; padding: 14px; color: var(--ink); }
.sidebar { width: 292px; min-width: 292px; height: 100%; display: flex; overflow: hidden; border-radius: 16px; background: rgba(248, 251, 248, .88); border-color: #d1dfd9; }
.sidebar-brand { display: flex; align-items: center; justify-content: space-between; padding: 20px 18px 16px; }
.brand-lockup { display: flex; align-items: center; gap: 9px; color: #315149; font-size: 13px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.brand-mark { width: 29px; height: 29px; display: grid; place-items: center; border: 1px solid #a8c4b7; border-radius: 8px; background: #e0f2e9; color: var(--forest); }
.brand-mark svg { width: 15px; }
.online-dot { width: 7px; height: 7px; border-radius: 50%; background: #46a174; box-shadow: 0 0 0 4px #dcefe4; }
.new-button { display: flex; align-items: center; gap: 9px; width: calc(100% - 32px); margin: 0 16px 18px; padding: 11px 13px; border: 1px solid #176448; border-radius: 9px; background: #176448; color: #fff; cursor: pointer; font-size: 14px; font-weight: 700; box-shadow: 0 8px 18px rgba(23, 100, 72, .16); }
.new-button svg { width: 16px; }
.new-button kbd { margin-left: auto; color: #b9dccb; font-size: 10px; font-weight: 500; }
.new-button:hover { background: #0f4937; }
.sidebar-header { padding: 13px 16px; border-top: 1px solid #dfe9e4; border-bottom: 0; }
.workspace-label { display: flex; align-items: center; gap: 9px; min-width: 0; }
.workspace-avatar { width: 27px; height: 27px; display: grid; flex-shrink: 0; place-items: center; border-radius: 8px; background: #e6f0eb; color: var(--forest); font-size: 13px; font-weight: 800; }
.workspace-label strong, .workspace-label small { display: block; }
.workspace-label strong { overflow: hidden; color: #2b423a; font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
.workspace-label small { margin-top: 2px; color: #91a09a; font-size: 11px; }
.icon-button { width: 30px; height: 30px; display: grid; place-items: center; border: 1px solid transparent; border-radius: 8px; background: transparent; color: #74837d; cursor: pointer; }
.icon-button svg { width: 15px; }
.icon-button:hover { border-color: #cbdcd4; background: #edf5f0; color: var(--forest); }
.list-heading { display: flex; justify-content: space-between; padding: 12px 18px 7px; color: #8a9993; font-size: 11px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.list-heading span:last-child { color: #b2c0ba; }
.conversation-list-wrap { flex: 1; overflow-y: auto; }
.sidebar-empty { display: grid; place-items: center; gap: 8px; min-height: 150px; color: #9aa8a2; font-size: 13px; }
.sidebar-empty svg { width: 19px; color: #8eb8a3; }
.conversation-list { padding: 4px 10px; }
.conversation-row { display: flex; align-items: center; margin: 2px 0; border-radius: 9px; }
.conversation-row.active { background: #e4f2eb; box-shadow: inset 3px 0 0 #27805d; }
.conversation-item { display: flex; align-items: center; gap: 9px; min-width: 0; flex: 1; padding: 10px 8px; border: 0; background: transparent; color: #50615a; text-align: left; cursor: pointer; font-size: 13px; }
.conversation-item svg { width: 14px; flex-shrink: 0; color: #8aa098; }
.conversation-row.active .conversation-item { color: #176448; font-weight: 700; }
.conversation-row.active .conversation-item svg { color: #27805d; }
.conversation-item:hover { color: #176448; }
.delete-button { width: 28px; height: 28px; display: grid; flex-shrink: 0; place-items: center; margin-right: 5px; border: 0; border-radius: 7px; background: transparent; color: #a7b2ad; cursor: pointer; font-size: 0; }
.delete-button svg { width: 14px; }
.delete-button:hover { background: #fae9e8; color: var(--rose); }
.main-area { min-width: 0; overflow: hidden; border: 1px solid #d5e1dc; border-radius: 16px; background-color: rgba(250, 252, 250, .72); box-shadow: 0 18px 50px rgba(34, 67, 55, .06); }
.conversation-meta { min-height: 78px; padding: 16px 28px; border-bottom: 1px solid #dce7e1; background: rgba(251, 253, 251, .7); }
.meta-copy { min-width: 0; }
.breadcrumb { display: flex; align-items: center; gap: 8px; color: #9aa8a2; font-size: 10px; font-weight: 800; letter-spacing: .12em; }
.breadcrumb strong { color: #4f675d; }
.meta-copy h1 { overflow: hidden; margin: 7px 0 0; color: #213a30; font-size: 19px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.empty-state { flex-direction: column; justify-content: center; gap: 0; min-height: 0; padding: 28px 20px 42px; color: #60716a; }
.guide-summary { max-width: 620px; text-align: center; }
.guide-summary .empty-orbit { margin-right: auto; margin-left: auto; }
.empty-orbit { position: relative; width: 70px; height: 70px; display: grid; place-items: center; margin-bottom: 21px; border: 1px solid #b8d9c9; border-radius: 50%; background: rgba(224, 242, 233, .72); color: #27805d; }
.empty-orbit::before, .empty-orbit::after { position: absolute; border: 1px solid #cbe5d8; border-radius: 50%; content: ""; }
.empty-orbit::before { inset: -9px; }
.empty-orbit::after { inset: 9px; border-color: #a9d1bd; }
.empty-orbit span { position: absolute; top: -3px; right: 4px; width: 7px; height: 7px; border-radius: 50%; background: #bb7c32; }
.empty-orbit svg { position: relative; z-index: 1; width: 24px; }
.empty-kicker { color: #27805d; font-size: 11px; font-weight: 800; letter-spacing: .16em; }
.empty-state h2 { margin: 13px 0 8px; color: #20382e; font-size: 28px; letter-spacing: -.04em; }
.empty-state p { margin: 0; color: #82918b; font-size: 14px; }
.guide-details { width: min(720px, 100%); margin-top: 25px; }
.guide-section { display: flex; align-items: center; justify-content: center; gap: 12px; min-height: 42px; padding: 8px 0; }
.template-section { padding: 14px; border: 0; border-radius: 11px; background: rgba(251, 253, 251, .76); }
.guide-section h3 { margin: 0; color: #36584b; font-size: 12px; font-weight: 800; white-space: nowrap; }
.template-section h3 { margin: 0 0 10px; color: #36584b; font-size: 12px; font-weight: 800; }
.guide-tags { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; }
.guide-tags span { padding: 5px 8px; border-radius: 999px; background: #edf6f0; color: #668077; font-size: 12px; }
.guide-fade-enter-active, .guide-fade-leave-active { transition: opacity 1s ease, transform 1s ease; }
.guide-fade-enter-from, .guide-fade-leave-to { opacity: 0; transform: translateY(3px); }
.template-section { width: min(720px, 100%); margin-top: 10px; }
.template-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.template-question { min-height: 50px; padding: 9px 10px; border: 1px solid #cfe1d6; border-radius: 8px; background: #f8fcf9; color: #48665a; cursor: pointer; font: inherit; font-size: 12px; line-height: 1.5; text-align: left; transition: transform 180ms ease, border-color 180ms ease, background-color 180ms ease, box-shadow 180ms ease; }
.template-question:hover { border-color: #7eaf95; background: #edf7f0; box-shadow: 0 5px 12px rgba(23, 100, 72, .1); transform: translateY(-2px); }
.template-question:disabled { cursor: wait; opacity: .6; transform: none; }
.message-container { padding: 28px clamp(18px, 6vw, 100px); }
.message { max-width: 760px; margin: 0 auto 30px; gap: 12px; }
.message-role { width: 32px; height: 32px; border-radius: 10px; background: #dff1e7; color: #237354; font-size: 11px; }
.message.user .message-role { background: #f8e8d6; color: #a76a2d; }
.message-block { min-width: 0; flex: 1; }
.message-label { margin: 1px 0 7px; color: #82918b; font-size: 11px; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
.message.user .message-label { color: #a76a2d; }
.message-content { color: #31453d; font-size: 15px; line-height: 1.75; }
.source-list { margin: 12px 0 0 44px; border-left-color: #a9d1bd; border-radius: 0 8px 8px 0; background: rgba(234, 245, 238, .58); }
.input-area { width: min(calc(100% - 48px), 1180px); max-width: none; margin: auto auto 0; padding: 12px 22px 14px; border-top: 0; }
.composer { border-radius: 13px; padding: 10px 12px 8px; background: rgba(251, 253, 251, .96); }
.input-field { min-height: 72px; padding: 8px 4px; border: 0; outline: 0; background: transparent; color: #28443a; font-size: 15px; resize: none; }
.input-field::placeholder { color: #a6b2ad; }
.input-field:focus { border: 0; }
.input-actions { justify-content: space-between; margin-top: 3px; }
.agent-options { display: flex; flex: 1 1 260px; align-items: center; gap: 6px 8px; min-width: 0; }
.agent-option { position: relative; display: inline-flex; align-items: center; min-height: 30px; padding: 0 10px; border: 1px solid #cfe0d7; border-radius: 7px; background: #f7fbf8; color: #5d7068; cursor: pointer; font-size: 12px; white-space: nowrap; transition: transform 180ms ease, border-color 180ms ease, background-color 180ms ease, box-shadow 180ms ease, color 180ms ease; }
.agent-option:hover { border-color: #82b79e; background: #edf7f0; color: var(--forest); box-shadow: 0 5px 12px rgba(23, 100, 72, .12); transform: translateY(-2px); }
.agent-option input { position: absolute; width: 1px; height: 1px; overflow: hidden; opacity: 0; pointer-events: none; }
.agent-option:has(input:focus-visible) { outline: 2px solid #70a98c; outline-offset: 2px; }
.agent-option:has(input:checked) { border-color: var(--forest); background: var(--forest); color: #fff; font-weight: 700; box-shadow: 0 5px 12px rgba(23, 100, 72, .22); }
.agent-option:has(input:checked):hover { background: var(--forest-dark); border-color: var(--forest-dark); }
.attachment-button { padding: 7px 9px; border-color: #d5e3dc; border-radius: 7px; background: #f8fbf8; color: #72837c; font-size: 12px; }
.attachment-button { display: inline-flex; align-items: center; gap: 5px; cursor: pointer; }
.attachment-button svg { width: 14px; color: #27805d; }
.send-button, .stop-button { display: inline-flex; align-items: center; gap: 6px; padding: 8px 13px; border-radius: 8px; font-size: 13px; font-weight: 700; }
.send-button svg, .stop-button svg { width: 14px; }
.send-button { border-color: #176448; background: #176448; }
.send-button:hover { background: #0f4937; }
.stop-button { border-color: #ae4f54; background: #ae4f54; }
.composer-note { display: flex; justify-content: space-between; padding: 8px 3px 0; color: #9aa8a2; font-size: 11px; }
.error-banner { margin: 0 22px; border: 1px solid #f1c9c7; border-radius: 8px; background: #fff2f0; }
.attachment-list { margin-bottom: 9px; }
.attachment-item { border-color: #c1dccd; border-radius: 7px; background: rgba(235, 246, 239, .72); }
@media (max-width: 760px) { .conversation-shell { height: auto; min-height: 100vh; padding: 8px; display: block; } .sidebar { width: 100%; min-width: 0; height: auto; max-height: 210px; margin-bottom: 8px; border-radius: 13px; } .conversation-list-wrap { max-height: 48px; } .main-area { min-height: calc(100vh - 226px); border-radius: 13px; } .conversation-meta { padding: 14px 16px; } .empty-state { padding-bottom: 28px; } .template-list { grid-template-columns: 1fr; } .message-container { padding: 20px 14px; } .input-area { padding: 10px; } .agent-options { flex-basis: 100%; order: 3; } .composer-note { display: none; } }
@media (max-width: 470px) { .sidebar-header { padding-bottom: 9px; } .conversation-meta { align-items: flex-start; gap: 10px; } .meta-copy h1 { font-size: 17px; } .empty-state h2 { font-size: 25px; } .input-actions { justify-content: flex-end; } .attachment-button span { display: none; } }
</style>
