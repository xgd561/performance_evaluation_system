import axios from 'axios'
import { ElMessage } from 'element-plus'

const BASE_URL = import.meta.env?.VITE_API_BASE_URL || '/api/v1'

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
    if (typeof data.code === 'number' && data.code !== 0 && data.code !== 200) {
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
      msg = response.data?.message || error.message || `HTTP ${status}`

      if (status === 401) {
        localStorage.removeItem('pes_access_token')
        ElMessage.warning('登录已过期，请重新登录')
        setTimeout(() => {
          window.location.href = '/login'
        }, 1000)
        return Promise.reject(new Error('登录已过期'))
      }
    } else {
      msg = error.message || '网络错误'
    }

    ElMessage.error(msg)
    return Promise.reject(new Error(msg))
  }
)

export default request
