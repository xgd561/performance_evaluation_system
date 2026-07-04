import { describe, it, expect, vi } from 'vitest'

vi.mock('vue-router', () => ({
  createRouter: vi.fn(() => ({ beforeEach: vi.fn() })),
  createWebHistory: vi.fn(() => ({})),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}))

import { beforeEachGuard } from '@/router/index'
import { useAuthStore } from '@/stores/auth'

describe('Router guard - ConfigView access control', () => {
  it('redirects non-admin user to 403 when accessing /config', () => {
    const next = vi.fn()
    useAuthStore.mockReturnValue({ token: 'token123', role: 'employee' })

    beforeEachGuard(
      { path: '/config', meta: { roles: ['admin'] } },
      { path: '/dashboard' },
      next,
    )

    expect(next).toHaveBeenCalledWith('/403')
  })

  it('allows admin user to access /config', () => {
    const next = vi.fn()
    useAuthStore.mockReturnValue({ token: 'token123', role: 'admin' })

    beforeEachGuard(
      { path: '/config', meta: { roles: ['admin'] } },
      { path: '/dashboard' },
      next,
    )

    expect(next).toHaveBeenCalledWith()
  })
})
