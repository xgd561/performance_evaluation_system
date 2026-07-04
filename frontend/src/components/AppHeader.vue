<template>
  <div class="app-header">
    <div class="header-left">
      <div class="collapse-btn" @click="appStore.toggleSidebar()">
        <el-icon :size="18"><Fold v-if="!appStore.sidebarCollapsed" /><Expand v-else /></el-icon>
      </div>
      <div class="logo">
        <el-icon :size="28" color="#409eff"><Histogram /></el-icon>
        <span class="logo-text">绩效考核评分系统</span>
      </div>
    </div>
    <div class="header-right">
      <div class="user-info">
        <span class="role-tag">{{ ROLE_TEXT[authStore.userInfo?.role] || '' }}</span>
        <span class="user-name">{{ authStore.userInfo?.name || authStore.userInfo?.username || '' }}</span>
        <el-dropdown @command="handleCommand">
          <span class="user-dropdown">
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { ROLE_TEXT } from '@/utils/constants'

const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-header {
  height: var(--header-height, 56px);
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  cursor: pointer;
  color: #606266;
  padding: 6px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.collapse-btn:hover {
  background-color: #f5f7fa;
  color: #409eff;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.role-tag {
  font-size: 12px;
  color: #409eff;
  background-color: #ecf5ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.user-name {
  font-size: 14px;
  color: #606266;
}

.user-dropdown {
  cursor: pointer;
  color: #606266;
  padding: 4px;
}

.user-dropdown:hover {
  color: #409eff;
}
</style>
