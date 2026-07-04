import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // Sidebar 折叠状态
  const sidebarCollapsed = ref(false)

  // 通知数量
  const notificationCount = ref(0)

  // 主题 (light | dark)
  const theme = ref('light')

  // 面包屑导航
  const breadcrumbs = ref([])

  // 页面加载状态
  const pageLoading = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setTheme(value) {
    theme.value = value
  }

  function setNotificationCount(count) {
    notificationCount.value = count
  }

  function incrementNotification() {
    notificationCount.value += 1
  }

  function clearNotification() {
    notificationCount.value = 0
  }

  function setBreadcrumbs(list) {
    breadcrumbs.value = list
  }

  function setPageLoading(loading) {
    pageLoading.value = loading
  }

  return {
    sidebarCollapsed,
    notificationCount,
    theme,
    breadcrumbs,
    pageLoading,
    toggleSidebar,
    setTheme,
    setNotificationCount,
    incrementNotification,
    clearNotification,
    setBreadcrumbs,
    setPageLoading,
  }
})
