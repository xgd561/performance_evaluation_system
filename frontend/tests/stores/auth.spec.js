import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}))

import { login as apiLogin, getMe } from '@/api/auth'

const TOKEN_KEY = 'pes_access_token'
const USER_KEY = 'pes_user_info'

describe('P0-16 auth.js — Pinia Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('State 初始化', () => {
    it('无 localStorage 时，token 为空，userInfo 为 null', () => {
      const store = useAuthStore()
      expect(store.token).toBe('')
      expect(store.userInfo).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.role).toBe('')
    })

    it('localStorage 存在 token 和 user 时，应从 localStorage 恢复', () => {
      localStorage.setItem(TOKEN_KEY, 'stored_jwt')
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1, name: '张三', role: 'admin' }))
      const store = useAuthStore()
      expect(store.token).toBe('stored_jwt')
      expect(store.userInfo).toEqual({ id: 1, name: '张三', role: 'admin' })
      expect(store.isAuthenticated).toBe(true)
      expect(store.role).toBe('admin')
    })
  })

  describe('login action', () => {
    it('登录成功后应更新 token、userInfo，并写入 localStorage', async () => {
      apiLogin.mockResolvedValue({
        access_token: 'new_jwt_token',
        user: { id: 2, name: '李四', role: 'hr' },
      })
      const store = useAuthStore()
      const res = await store.login({ username: 'lisi', password: '123456' })

      expect(apiLogin).toHaveBeenCalledWith({ username: 'lisi', password: '123456' })
      expect(store.token).toBe('new_jwt_token')
      expect(store.userInfo).toEqual({ id: 2, name: '李四', role: 'hr' })
      expect(store.isAuthenticated).toBe(true)
      expect(store.role).toBe('hr')
      expect(localStorage.getItem(TOKEN_KEY)).toBe('new_jwt_token')
      expect(localStorage.getItem(USER_KEY)).toBe(JSON.stringify({ id: 2, name: '李四', role: 'hr' }))
      expect(res).toEqual({
        access_token: 'new_jwt_token',
        user: { id: 2, name: '李四', role: 'hr' },
      })
    })
  })

  describe('logout action', () => {
    it('应清除 token、userInfo 并移除 localStorage', () => {
      localStorage.setItem(TOKEN_KEY, 'old_jwt')
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }))
      const store = useAuthStore()
      store.logout()

      expect(store.token).toBe('')
      expect(store.userInfo).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
      expect(localStorage.getItem(USER_KEY)).toBeNull()
    })
  })

  describe('getUserInfo action', () => {
    it('应调用 getMe 并更新 userInfo 和 localStorage', async () => {
      getMe.mockResolvedValue({ id: 3, name: '王五', role: 'manager' })
      localStorage.setItem(TOKEN_KEY, 'valid_jwt')
      const store = useAuthStore()
      store.token = 'valid_jwt'
      const res = await store.getUserInfo()

      expect(getMe).toHaveBeenCalled()
      expect(store.userInfo).toEqual({ id: 3, name: '王五', role: 'manager' })
      expect(localStorage.getItem(USER_KEY)).toBe(JSON.stringify({ id: 3, name: '王五', role: 'manager' }))
      expect(res).toEqual({ id: 3, name: '王五', role: 'manager' })
    })

    it('无 token 时应直接返回 null，不调用 getMe', async () => {
      const store = useAuthStore()
      const res = await store.getUserInfo()
      expect(getMe).not.toHaveBeenCalled()
      expect(res).toBeNull()
    })

    it('getMe 失败时应调用 logout 并抛出异常', async () => {
      getMe.mockRejectedValue(new Error('token expired'))
      localStorage.setItem(TOKEN_KEY, 'expired_jwt')
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }))
      const store = useAuthStore()
      store.token = 'expired_jwt'
      store.userInfo = { id: 1 }

      await expect(store.getUserInfo()).rejects.toThrow('token expired')
      expect(store.token).toBe('')
      expect(store.userInfo).toBeNull()
      expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
    })
  })

  describe('Computed 属性', () => {
    it('isAuthenticated 在 token 非空时为 true', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
      store.token = 'abc'
      expect(store.isAuthenticated).toBe(true)
    })

    it('role 应从 userInfo.role 读取', () => {
      const store = useAuthStore()
      expect(store.role).toBe('')
      store.userInfo = { id: 1, role: 'admin' }
      expect(store.role).toBe('admin')
    })
  })
})
