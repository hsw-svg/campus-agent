<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { useConversationStore } from '../stores/conversation'
import type { Conversation } from '../api/conversations'

const emit = defineEmits<{ (event: 'switch-role'): void }>()
const store = useConversationStore()
const messageContainerRef = ref<HTMLElement | null>(null)
const inputText = ref('')

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

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey && !event.metaKey && !event.ctrlKey) {
    event.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="conversation-shell">
    <aside class="sidebar" aria-label="对话列表">
      <div class="sidebar-header">
        <strong>{{ roleLabel }}</strong>
        <div class="sidebar-actions">
          <button class="new-button" type="button" @click="handleNewConversation">新对话</button>
          <button class="switch-button" type="button" @click="emit('switch-role')">切换角色</button>
        </div>
      </div>
      <ul class="conversation-list">
        <li
          v-for="conversation in store.conversations"
          :key="conversation.id"
          class="conversation-row"
          :class="{ active: store.activeConversationId === conversation.id }"
        >
          <button
            class="conversation-item"
            type="button"
            @click="handleOpenConversation(conversation)"
          >
            <span class="conversation-title">{{ conversation.title }}</span>
          </button>
          <button
            class="delete-button"
            type="button"
            title="删除对话"
            aria-label="删除对话"
            @click.stop="store.removeConversation(conversation.id)"
          >
            ×
          </button>
        </li>
      </ul>
    </aside>

    <main class="main-area" aria-label="对话内容">
      <div v-if="store.activeConversation" class="conversation-meta">
        <h2>{{ store.activeConversation.title }}</h2>
        <div class="agent-selector">
          <label for="agent-select">智能体：</label>
          <select id="agent-select" v-model="store.selectedAgentId">
            <option :value="store.autoAgentId">自动识别</option>
            <option v-for="agent in store.agents" :key="agent.id" :value="agent.id">
              {{ agent.name }}
            </option>
          </select>
        </div>
      </div>

      <div v-if="!store.activeConversation" class="empty-state">
        <p>开始新对话或从左侧选择已有会话。</p>
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
          <div class="message-role">{{ message.role === 'user' ? '你' : 'AI' }}</div>
          <div class="message-content">{{ message.content }}</div>
        </article>
      </div>

      <div v-if="store.streamError" class="error-banner" role="alert">
        {{ store.streamError }}
      </div>

      <div v-if="store.activeConversation || store.messages.length === 0" class="input-area">
        <textarea
          v-model="inputText"
          class="input-field"
          placeholder="输入消息…"
          rows="3"
          :disabled="store.isStreaming"
          @keydown="handleKeydown"
        />
        <div class="input-actions">
          <button
            v-if="store.isStreaming"
            class="stop-button"
            type="button"
            @click="store.stopStreaming"
          >
            停止生成
          </button>
          <button
            v-else
            class="send-button"
            type="button"
            :disabled="!inputText.trim()"
            @click="handleSend"
          >
            发送
          </button>
        </div>
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
.agent-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.agent-selector select {
  border: 1px solid #c9d5cf;
  border-radius: 4px;
  padding: 4px 8px;
  background: #fff;
  font-size: 14px;
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
  justify-content: flex-end;
  margin-top: 8px;
}
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
