import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAppStore } from '@/stores/app'

describe('P0-16 app.js — Pinia App Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('State 初始化', () => {
    it('默认状态应正确', () => {
      const store = useAppStore()
      expect(store.sidebarCollapsed).toBe(false)
      expect(store.notificationCount).toBe(0)
      expect(store.theme).toBe('light')
      expect(store.breadcrumbs).toEqual([])
      expect(store.pageLoading).toBe(false)
    })
  })

  describe('toggleSidebar', () => {
    it('应切换 sidebarCollapsed 状态', () => {
      const store = useAppStore()
      expect(store.sidebarCollapsed).toBe(false)
      store.toggleSidebar()
      expect(store.sidebarCollapsed).toBe(true)
      store.toggleSidebar()
      expect(store.sidebarCollapsed).toBe(false)
    })
  })

  describe('setTheme', () => {
    it('应设置 theme 值', () => {
      const store = useAppStore()
      store.setTheme('dark')
      expect(store.theme).toBe('dark')
      store.setTheme('light')
      expect(store.theme).toBe('light')
    })
  })

  describe('NotificationCount', () => {
    it('setNotificationCount 应直接设置数量', () => {
      const store = useAppStore()
      store.setNotificationCount(5)
      expect(store.notificationCount).toBe(5)
    })

    it('incrementNotification 应增加数量', () => {
      const store = useAppStore()
      store.setNotificationCount(2)
      store.incrementNotification()
      expect(store.notificationCount).toBe(3)
    })

    it('clearNotification 应清零', () => {
      const store = useAppStore()
      store.setNotificationCount(10)
      store.clearNotification()
      expect(store.notificationCount).toBe(0)
    })
  })

  describe('setBreadcrumbs', () => {
    it('应设置面包屑导航', () => {
      const store = useAppStore()
      store.setBreadcrumbs([{ name: '首页', path: '/' }, { name: '配置', path: '/config' }])
      expect(store.breadcrumbs).toEqual([{ name: '首页', path: '/' }, { name: '配置', path: '/config' }])
    })
  })

  describe('setPageLoading', () => {
    it('应设置页面加载状态', () => {
      const store = useAppStore()
      store.setPageLoading(true)
      expect(store.pageLoading).toBe(true)
      store.setPageLoading(false)
      expect(store.pageLoading).toBe(false)
    })
  })
})
