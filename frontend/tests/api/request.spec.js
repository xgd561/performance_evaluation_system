import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

const state = vi.hoisted(() => ({
  capturedCreateArgs: null,
  requestInterceptor: null,
  requestErrorInterceptor: null,
  responseSuccessInterceptor: null,
  responseErrorInterceptor: null,
  mockAxiosInstance: {
    interceptors: {
      request: {
        use: vi.fn((onFulfilled, onRejected) => {
          state.requestInterceptor = onFulfilled
          state.requestErrorInterceptor = onRejected
        }),
      },
      response: {
        use: vi.fn((onFulfilled, onRejected) => {
          state.responseSuccessInterceptor = onFulfilled
          state.responseErrorInterceptor = onRejected
        }),
      },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn((args) => {
      state.capturedCreateArgs = args
      return state.mockAxiosInstance
    }),
  },
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    warning: vi.fn(),
  },
}))

// 导入被测模块（必须在 vi.mock 之后）
import request from '@/api/request'
import { ElMessage } from 'element-plus'

describe('P0-15 request.js — 前端 API 请求封装', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    localStorage.clear()
    delete window.location
    window.location = { href: '' }
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('axios 实例配置', () => {
    it('应使用 /api/v1 作为 baseURL', () => {
      expect(state.capturedCreateArgs).toMatchObject({
        baseURL: '/api/v1',
        timeout: 10000,
        headers: { 'Content-Type': 'application/json' },
      })
    })
  })

  describe('请求拦截器', () => {
    it('localStorage 有 token 时，应在请求头注入 Authorization', () => {
      localStorage.setItem('pes_access_token', 'test_jwt_token')
      const config = { headers: {}, method: 'get', url: '/users/me' }
      const result = state.requestInterceptor(config)
      expect(result.headers.Authorization).toBe('Bearer test_jwt_token')
    })

    it('localStorage 无 token 时，不应注入 Authorization', () => {
      const config = { headers: {}, method: 'get', url: '/users/me' }
      const result = state.requestInterceptor(config)
      expect(result.headers.Authorization).toBeUndefined()
    })

    it('应在非生产环境打印请求日志', () => {
      const config = { headers: {}, method: 'post', url: '/auth/login', data: { username: 'admin' } }
      state.requestInterceptor(config)
      expect(console.log).toHaveBeenCalled()
    })
  })

  describe('响应拦截器 — 成功', () => {
    it('code 为 0 时，应返回响应 data', () => {
      const response = {
        config: { method: 'get', url: '/users/me' },
        data: { code: 0, message: 'ok', data: { id: 1, name: '张三' } },
      }
      const result = state.responseSuccessInterceptor(response)
      expect(result).toEqual({ code: 0, message: 'ok', data: { id: 1, name: '张三' } })
    })

    it('code 非 0 时，应显示错误消息并 reject', async () => {
      const response = {
        config: { method: 'post', url: '/auth/login' },
        data: { code: 1001, message: '用户名或密码错误' },
      }
      const result = state.responseSuccessInterceptor(response)
      await expect(result).rejects.toThrow('用户名或密码错误')
      expect(ElMessage.error).toHaveBeenCalledWith('用户名或密码错误')
    })

    it('code 非 0 且无 message 时，应显示默认错误消息', async () => {
      const response = {
        config: { method: 'get', url: '/users/me' },
        data: { code: 500 },
      }
      const result = state.responseSuccessInterceptor(response)
      await expect(result).rejects.toThrow('请求失败')
      expect(ElMessage.error).toHaveBeenCalledWith('请求失败')
    })
  })

  describe('响应拦截器 — 错误', () => {
    it('401 响应时，应清除 token、提示过期并跳转到登录页', async () => {
      localStorage.setItem('pes_access_token', 'expired_token')
      const error = {
        response: { status: 401, data: { message: 'Unauthorized' } },
      }
      const result = state.responseErrorInterceptor(error)
      await expect(result).rejects.toThrow('登录已过期')
      expect(localStorage.getItem('pes_access_token')).toBeNull()
      expect(ElMessage.warning).toHaveBeenCalledWith('登录已过期，请重新登录')
      vi.runAllTimers()
      expect(window.location.href).toBe('/login')
    })

    it('非 401 HTTP 错误时，应显示错误消息并 reject', async () => {
      const error = {
        response: { status: 500, data: { message: '服务器内部错误' } },
      }
      const result = state.responseErrorInterceptor(error)
      await expect(result).rejects.toThrow('服务器内部错误')
      expect(ElMessage.error).toHaveBeenCalledWith('服务器内部错误')
    })

    it('网络错误（无 response）时，应显示错误消息并 reject', async () => {
      const error = { message: 'Network Error' }
      const result = state.responseErrorInterceptor(error)
      await expect(result).rejects.toThrow('Network Error')
      expect(ElMessage.error).toHaveBeenCalledWith('Network Error')
    })
  })

  describe('API 快捷方法', () => {
    it('request.get 应为已定义的函数', () => {
      expect(typeof request.get).toBe('function')
    })
    it('request.post 应为已定义的函数', () => {
      expect(typeof request.post).toBe('function')
    })
    it('request.put 应为已定义的函数', () => {
      expect(typeof request.put).toBe('function')
    })
    it('request.delete 应为已定义的函数', () => {
      expect(typeof request.delete).toBe('function')
    })
  })
})
