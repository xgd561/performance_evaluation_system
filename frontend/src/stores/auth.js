import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, getMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => user.value?.role || '')

  async function doLogin(credentials) {
    const res = await login(credentials)
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    user.value = res.user
    return res
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const res = await getMe()
      user.value = res
    } catch (e) {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, role, doLogin, fetchUser, logout }
})
