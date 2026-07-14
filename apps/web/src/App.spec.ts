import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.vue'

describe('App', () => {
  afterEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
  })

  it('mounts the application root', () => {
    expect(mount(App).exists()).toBe(true)
  })

  it('creates and saves a workspace when a role is selected', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ workspace: { id: 'student-id', role: 'student' }, token: 'student-token' }), { status: 201 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(App)
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith('/api/workspaces', expect.objectContaining({ method: 'POST' }))
    expect(localStorage.getItem('campus-agent.workspace-token.student')).toBe('student-token')
    expect(wrapper.text()).toContain('已创建学生助手')
  })

  it('clears an invalid saved credential and returns to role selection', async () => {
    localStorage.setItem('campus-agent.workspace-token.teacher', 'expired-token')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: { message: 'Workspace credentials are invalid or expired.' } }), { status: 401 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(App)
    await wrapper.get('.role-option:nth-child(2)').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(localStorage.getItem('campus-agent.workspace-token.teacher')).toBeNull()
    expect(wrapper.text()).toContain('工作空间凭据已失效，请重新选择角色。')
  })
})
