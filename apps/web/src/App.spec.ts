import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.vue'

function mountApp() {
  return mount(App, { global: { plugins: [createPinia()] } })
}

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('App', () => {
  afterEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
  })

  it('renders role selection when no workspace is active', () => {
    const wrapper = mountApp()
    expect(wrapper.text()).toContain('选择工作空间')
    expect(wrapper.find('.conversation-shell').exists()).toBe(false)
  })

  it('creates a workspace and enters the conversation shell', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === '/api/workspaces') {
        return jsonResponse(
          { workspace: { id: 'student-id', role: 'student' }, token: 'student-token' },
          { status: 201 },
        )
      }
      if (url === '/api/agents') {
        return jsonResponse({ role: 'student', auto_agent_id: 'auto', agents: [] })
      }
      if (url === '/api/conversations') {
        return jsonResponse([])
      }
      throw new Error(`unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountApp()
    await wrapper.get('.role-option').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith('/api/workspaces', expect.objectContaining({ method: 'POST' }))
    expect(localStorage.getItem('campus-agent.workspace-token.student')).toBe('student-token')
    expect(wrapper.find('.conversation-shell').exists()).toBe(true)
    expect(wrapper.text()).toContain('学生助手')
  })

  it('clears an invalid saved credential and stays on role selection', async () => {
    localStorage.setItem('campus-agent.workspace-token.teacher', 'expired-token')
    const fetchMock = vi.fn(async () =>
      jsonResponse({ error: { message: 'Workspace credentials are invalid or expired.' } }, { status: 401 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountApp()
    await wrapper.get('.role-option:nth-child(2)').trigger('click')
    await flushPromises()

    expect(localStorage.getItem('campus-agent.workspace-token.teacher')).toBeNull()
    expect(wrapper.find('.conversation-shell').exists()).toBe(false)
    expect(wrapper.text()).toContain('Workspace credentials are invalid or expired.')
  })
})
