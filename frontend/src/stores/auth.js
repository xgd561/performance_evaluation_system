import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, getMe, changePassword as apiChangePassword } from '@/api/auth'

const TOKEN_KEY = 'pes_access_token'
const USER_KEY = 'pes_user_info'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const storedUser = localStorage.getItem(USER_KEY)
  const userInfo = ref(storedUser ? JSON.parse(storedUser) : null)

  // Computed
  const isAuthenticated = computed(() => !!token.value)
  const role = computed(() => userInfo.value?.role || '')
  const isFirstLogin = computed(() => userInfo.value?.is_first_login || false)
  const user = computed(() => userInfo.value)

  // Actions
  async function login(credentials) {
    const res = await apiLogin(credentials)
    token.value = res.access_token
    userInfo.value = res.user
    localStorage.setItem(TOKEN_KEY, res.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(res.user))
    return res
  }

  async function getUserInfo() {
    if (!token.value) return null
    try {
      const res = await getMe()
      userInfo.value = res
      localStorage.setItem(USER_KEY, JSON.stringify(res))
      return res
    } catch (e) {
      logout()
      throw e
    }
  }

  async function changePassword(data) {
    const res = await apiChangePassword(data)
    // 修改成功后，更新 is_first_login 状态
    if (userInfo.value) {
      userInfo.value.is_first_login = false
      localStorage.setItem(USER_KEY, JSON.stringify(userInfo.value))
    }
    return res
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return {
    token,
    user,
    userInfo,
    role,
    isAuthenticated,
    isFirstLogin,
    login,
    logout,
    getUserInfo,
    changePassword,
  }
})
