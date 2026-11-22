import axios from 'axios'
import { ElMessage } from 'element-plus'

const BASE_URL = import.meta.env?.VITE_API_BASE_URL || '/api/v1'

// 判断响应体是否为后端统一响应信封 { code, message, data }
function isEnvelope(payload) {
  return (
    payload !== null &&
    typeof payload === 'object' &&
    !Array.isArray(payload) &&
    typeof payload.code === 'number' &&
    typeof payload.message === 'string' &&
    Object.prototype.hasOwnProperty.call(payload, 'data')
  )
}

const request = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('pes_access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (import.meta.env?.MODE !== 'production') {
      const url = new URL(config.url, window.location.origin + (config.baseURL || ''))
      const params = new URLSearchParams()
      if (config.params) {
        for (const [key, value] of Object.entries(config.params)) {
          if (value !== undefined && value !== null) {
            params.append(key, value)
          }
        }
      }
      const paramStr = params.toString()
      console.log(
        `[Request] ${config.method?.toUpperCase()} ${url.pathname}${paramStr ? '?' + paramStr : ''}`,
        config.params || config.data
      )
    }
    return config
  },
  (error) => {
    if (import.meta.env?.MODE !== 'production') {
      console.error('[Request Error]', error)
    }
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    if (import.meta.env?.MODE !== 'production') {
      console.log(
        `[Response] ${response.config.method?.toUpperCase()} ${response.config.url}`,
        response.data
      )
    }
    const data = response.data

    // 后端成功响应统一为 { code, message, data }，这里解包出业务数据，
    // 视图层仍按 res.xxx 取值；未包装的旧接口（如健康检查）原样返回。
    if (isEnvelope(data)) {
      if (data.code !== 0 && data.code !== 200) {
        ElMessage.error(data.message || '请求失败')
        return Promise.reject(new Error(data.message || '请求失败'))
      }
      return data.data
    }

    if (typeof data?.code === 'number' && data.code !== 0 && data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return data
  },
  (error) => {
    const response = error.response
    let msg = '网络错误'

    if (response) {
      const status = response.status
      msg = response.data?.message || response.data?.detail || error.message || `HTTP ${status}`

      if (status === 401) {
        // 登录接口的 401 是「用户名或密码错误」，不能被当成登录态失效，
        // 否则会把登录失败误报成「登录已过期」并跳回登录页
        const isLoginRequest = String(error.config?.url || '').includes('/auth/login')
        if (!isLoginRequest) {
          localStorage.removeItem('pes_access_token')
          ElMessage.warning('登录已过期，请重新登录')
          setTimeout(() => {
            window.location.href = '/login'
          }, 1000)
          return Promise.reject(new Error('登录已过期'))
        }
      }
    } else {
      msg = error.message || '网络错误'
    }

    ElMessage.error(msg)
    return Promise.reject(new Error(msg))
  }
)

export default request
