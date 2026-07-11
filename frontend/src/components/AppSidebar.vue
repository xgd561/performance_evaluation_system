<template>
  <div class="app-sidebar">
    <div class="sidebar-brand">
      <div class="brand-icon">
        <el-icon :size="24"><Histogram /></el-icon>
      </div>
      <div v-if="!appStore.sidebarCollapsed" class="brand-text">
        <div class="brand-title">绩效考核</div>
        <div class="brand-subtitle">PERFORMANCE</div>
      </div>
    </div>

    <el-menu
      :default-active="activePath"
      :collapse="appStore.sidebarCollapsed"
      :collapse-transition="false"
      router
      class="sidebar-menu"
      background-color="transparent"
      text-color="#94a3b8"
      active-text-color="#ffffff"
    >
      <template v-for="item in menuItems" :key="item.path">
        <el-menu-item :index="item.path" class="menu-item-custom">
          <el-icon>
            <component :is="item.icon" />
          </el-icon>
          <template #title>
            <span class="menu-title">{{ item.title }}</span>
          </template>
        </el-menu-item>
      </template>
    </el-menu>

    <div v-if="!appStore.sidebarCollapsed" class="sidebar-footer">
      <div class="footer-version">
        <span class="version-dot"></span>
        v2.0.0
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { ROLE_MENU_ITEMS } from '@/utils/constants'
import { Histogram } from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()
const authStore = useAuthStore()

const activePath = computed(() => route.path)

const menuItems = computed(() => {
  const role = authStore.userInfo?.role
  return ROLE_MENU_ITEMS[role] || ROLE_MENU_ITEMS.employee || []
})
</script>

<style scoped>
.app-sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.sidebar-brand {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.brand-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.brand-title {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 10px;
  font-weight: 600;
  color: var(--primary-light);
  letter-spacing: 1.5px;
  line-height: 1;
}

.sidebar-menu {
  border-right: none;
  flex: 1;
  padding: 12px 10px;
  overflow-y: auto;
}

.menu-item-custom {
  height: 48px;
  line-height: 48px;
  border-radius: var(--radius-md);
  margin-bottom: 4px;
  color: #94a3b8;
  transition: all var(--transition-fast);
}

.menu-item-custom:hover {
  background: rgba(255, 255, 255, 0.06) !important;
  color: #e2e8f0 !important;
}

.menu-item-custom.is-active {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.2) 0%, rgba(99, 102, 241, 0.05) 100%) !important;
  color: #fff !important;
  border-left: 3px solid var(--primary-color);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}

.menu-item-custom .el-icon {
  font-size: 18px;
  margin-right: 12px;
}

.menu-title {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.footer-version {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.version-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success-color);
  display: inline-block;
  box-shadow: 0 0 6px var(--success-color);
}

/* Deep overrides for Element Plus menu */
:deep(.el-menu) {
  background: transparent !important;
}

:deep(.el-menu-item) {
  border-radius: var(--radius-md);
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.2) 0%, rgba(99, 102, 241, 0.05) 100%) !important;
}

:deep(.el-menu--collapse) {
  width: 64px;
}

:deep(.el-menu--collapse .el-menu-item) {
  padding: 0 20px !important;
  justify-content: center;
}

:deep(.el-menu--collapse .el-tooltip__trigger) {
  justify-content: center;
  padding: 0 !important;
  left: 0 !important;
}
</style>
