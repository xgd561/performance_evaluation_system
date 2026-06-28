import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // Sidebar 折叠状态
  const sidebarCollapsed = ref(false)

  // 面包屑导航
  const breadcrumbs = ref([])

  // 页面加载状态
  const pageLoading = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setBreadcrumbs(list) {
    breadcrumbs.value = list
  }

  function setPageLoading(loading) {
    pageLoading.value = loading
  }

  return {
    sidebarCollapsed,
    breadcrumbs,
    pageLoading,
    toggleSidebar,
    setBreadcrumbs,
    setPageLoading
  }
})
