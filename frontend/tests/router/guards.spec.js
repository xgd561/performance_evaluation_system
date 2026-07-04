import { describe, it, expect, vi, beforeEach } from 'vitest'
import { routes, beforeEachGuard } from '@/router/index.js'

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}))

import { useAuthStore } from '@/stores/auth'

describe('P0-17 router — 导航守卫与角色过滤', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('beforeEachGuard', () => {
    it('未登录访问非公开页面应跳转 /login', () => {
      useAuthStore.mockReturnValue({ token: '', userInfo: null, role: '', isAuthenticated: false })
      const next = vi.fn()
      beforeEachGuard({ path: '/config', meta: { roles: ['admin'] } }, {}, next)
      expect(next).toHaveBeenCalledWith('/login')
    })

    it('未登录访问 /login 应允许通过', () => {
      useAuthStore.mockReturnValue({ token: '', userInfo: null, role: '', isAuthenticated: false })
      const next = vi.fn()
      beforeEachGuard({ path: '/login', meta: { public: true } }, {}, next)
      expect(next).toHaveBeenCalledWith()
    })

    it('未登录访问 /403 应允许通过', () => {
      useAuthStore.mockReturnValue({ token: '', userInfo: null, role: '', isAuthenticated: false })
      const next = vi.fn()
      beforeEachGuard({ path: '/403', meta: { public: true } }, {}, next)
      expect(next).toHaveBeenCalledWith()
    })

    it('admin 访问 /config 应允许通过', () => {
      useAuthStore.mockReturnValue({ token: 'admin_jwt', userInfo: { id: 1, role: 'admin' }, role: 'admin', isAuthenticated: true })
      const next = vi.fn()
      beforeEachGuard({ path: '/config', meta: { roles: ['admin'] } }, {}, next)
      expect(next).toHaveBeenCalledWith()
    })

    it('hr 访问 /config 应被拦截到 /403', () => {
      useAuthStore.mockReturnValue({ token: 'hr_jwt', userInfo: { id: 2, role: 'hr' }, role: 'hr', isAuthenticated: true })
      const next = vi.fn()
      beforeEachGuard({ path: '/config', meta: { roles: ['admin'] } }, {}, next)
      expect(next).toHaveBeenCalledWith('/403')
    })

    it('employee 访问 /config 应被拦截到 /403', () => {
      useAuthStore.mockReturnValue({ token: 'emp_jwt', userInfo: { id: 3, role: 'employee' }, role: 'employee', isAuthenticated: true })
      const next = vi.fn()
      beforeEachGuard({ path: '/config', meta: { roles: ['admin'] } }, {}, next)
      expect(next).toHaveBeenCalledWith('/403')
    })

    it('employee 访问 /dashboard 应允许通过', () => {
      useAuthStore.mockReturnValue({ token: 'emp_jwt', userInfo: { id: 3, role: 'employee' }, role: 'employee', isAuthenticated: true })
      const next = vi.fn()
      beforeEachGuard({ path: '/dashboard', meta: { roles: ['admin', 'hr', 'manager', 'employee', 'peer', 'executive'] } }, {}, next)
      expect(next).toHaveBeenCalledWith()
    })

    it('已登录但 role 为空访问需要角色的页面应允许通过（跳过权限校验）', () => {
      useAuthStore.mockReturnValue({ token: 'jwt', userInfo: null, role: '', isAuthenticated: true })
      const next = vi.fn()
      beforeEachGuard({ path: '/config', meta: { roles: ['admin'] } }, {}, next)
      expect(next).toHaveBeenCalledWith()
    })

    it('已登录用户访问不需要角色的页面应允许通过', () => {
      useAuthStore.mockReturnValue({ token: 'jwt', userInfo: { id: 1 }, role: '', isAuthenticated: true })
      const next = vi.fn()
      beforeEachGuard({ path: '/about', meta: {} }, {}, next)
      expect(next).toHaveBeenCalledWith()
    })
  })

  describe('路由表配置', () => {
    it('/login 应为公开路由', () => {
      const route = routes.find((r) => r.path === '/login')
      expect(route).toBeDefined()
      expect(route.meta.public).toBe(true)
    })

    it('/403 应为公开路由', () => {
      const route = routes.find((r) => r.path === '/403')
      expect(route).toBeDefined()
      expect(route.meta.public).toBe(true)
    })

    it('/config 应只允许 admin 访问', () => {
      const route = routes.find((r) => r.path === '/')
      const child = route.children.find((c) => c.path === 'config')
      expect(child.meta.roles).toEqual(['admin'])
    })

    it('/dashboard 应允许所有角色访问', () => {
      const route = routes.find((r) => r.path === '/')
      const child = route.children.find((c) => c.path === 'dashboard')
      expect(child.meta.roles).toEqual(['admin', 'hr', 'manager', 'employee', 'peer', 'executive'])
    })

    it('存在 /:pathMatch(.*)* 通配符路由', () => {
      const route = routes.find((r) => r.path === '/:pathMatch(.*)*')
      expect(route).toBeDefined()
      expect(route.redirect).toBe('/403')
    })
  })
})
