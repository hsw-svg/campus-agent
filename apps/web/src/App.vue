<script setup lang="ts">
import { ref } from 'vue'
import RoleSelection from './components/RoleSelection.vue'
import ConversationShell from './components/ConversationShell.vue'
import { useConversationStore } from './stores/conversation'
import type { WorkspaceRole } from './workspaces'

const store = useConversationStore()
const activeRole = ref<WorkspaceRole | null>(null)

async function handleEntered(payload: { role: WorkspaceRole; token: string }): Promise<void> {
  await store.activateRole(payload.role, payload.token)
  activeRole.value = payload.role
}

function handleSwitchRole(): void {
  store.reset()
  activeRole.value = null
}
</script>

<template>
  <ConversationShell v-if="activeRole" @switch-role="handleSwitchRole" />
  <RoleSelection v-else @entered="handleEntered" />
</template>
