import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import App from './App.vue'

describe('App', () => {
  it('mounts the application root', () => {
    expect(mount(App).exists()).toBe(true)
  })
})
