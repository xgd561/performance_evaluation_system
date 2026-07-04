<template>
  <div class="app-sidebar">
    <div v-if="!appStore.sidebarCollapsed" class="sidebar-logo">
      <span>绩效考核系统</span>
    </div>
    <div v-else class="sidebar-logo collapsed">
      <span>绩效</span>
    </div>
    <el-menu
      :default-active="activePath"
      :collapse="appStore.sidebarCollapsed"
      :collapse-transition="false"
      router
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409eff"
    >
      <template v-for="item in menuItems" :key="item.path">
        <el-menu-item :index="item.path">
          <el-icon>
            <component :is="item.icon" />
          </el-icon>
          <template #title>
            <span>{{ item.title }}</span>
          </template>
        </el-menu-item>
      </template>
    </el-menu>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { ROLE_MENU_ITEMS } from '@/utils/constants'

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
  background-color: #304156;
}

.sidebar-logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #1f2d3d;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar-logo.collapsed {
  font-size: 14px;
}

.app-sidebar :deep(.el-menu) {
  border-right: none;
}

:deep(.el-menu-item) {
  height: 50px;
  line-height: 50px;
}

:deep(.el-menu-item .el-icon) {
  font-size: 18px;
  margin-right: 8px;
}

:deep(.el-menu-item.is-active) {
  background-color: #263445 !important;
}
</style>
