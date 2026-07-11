<template>
  <div class="app-header">
    <div class="header-left">
      <div class="collapse-btn" @click="appStore.toggleSidebar()">
        <el-icon :size="18"><Fold v-if="!appStore.sidebarCollapsed" /><Expand v-else /></el-icon>
      </div>
      <div class="page-title">
        <span class="title-greeting">{{ greeting }}</span>
        <span class="title-divider">| </span>
        <span class="title-system">绩效考核评分系统</span>
      </div>
    </div>
    <div class="header-right">
      <div class="user-info">
        <div class="role-badge role-tag" :class="authStore.userInfo?.role">
          {{ ROLE_TEXT[authStore.userInfo?.role] || '' }}
        </div>
        <div class="user-avatar">
          <span class="avatar-text">{{ avatarText }}</span>
        </div>

        <div class="user-name">
          <div class="name-main">{{ authStore.userInfo?.name || authStore.userInfo?.username || '' }}</div>
          <div class="name-sub">{{ authStore.userInfo?.employee_no || '' }}</div>
        </div>

        <el-dropdown @command="handleCommand" trigger="click">
          <span class="user-dropdown">
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu class="custom-dropdown">
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
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { ROLE_TEXT } from '@/utils/constants'
import { Fold, Expand, ArrowDown, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 9) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const avatarText = computed(() => {
  const name = authStore.userInfo?.name || authStore.userInfo?.username || '?'
  return name.charAt(0).toUpperCase()
})

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-header {
  height: var(--header-height, 64px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: transparent;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  cursor: pointer;
  color: var(--text-secondary);
  padding: 8px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  background: rgba(99, 102, 241, 0.08);
}

.collapse-btn:hover {
  background: rgba(99, 102, 241, 0.15);
  color: var(--primary-color);
  transform: scale(1.05);
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-greeting {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.title-divider {
  color: var(--border-color);
  font-weight: 300;
}

.title-system {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 14px;
}

.role-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 1px solid transparent;
}

.role-badge.admin {
  background: rgba(99, 102, 241, 0.1);
  color: var(--primary-color);
  border-color: rgba(99, 102, 241, 0.2);
}

.role-badge.hr {
  background: rgba(245, 158, 11, 0.1);
  color: var(--accent-color);
  border-color: rgba(245, 158, 11, 0.2);
}

.role-badge.manager {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
  border-color: rgba(16, 185, 129, 0.2);
}

.role-badge.employee {
  background: rgba(59, 130, 246, 0.1);
  color: var(--info-color);
  border-color: rgba(59, 130, 246, 0.2);
}

.role-badge.executive {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
  border-color: rgba(239, 68, 68, 0.2);
}

.role-badge.peer {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
  border-color: rgba(139, 92, 246, 0.2);
}

.user-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.3);
  flex-shrink: 0;
}

.avatar-text {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.user-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.2;
}

.name-main {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.name-sub {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.user-dropdown {
  cursor: pointer;
  color: var(--text-muted);
  padding: 6px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  margin-left: 4px;
}

.user-dropdown:hover {
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.08);
}

:deep(.custom-dropdown) {
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 6px 0;
}

:deep(.custom-dropdown .el-dropdown-menu__item) {
  padding: 10px 18px;
  font-size: 14px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

:deep(.custom-dropdown .el-dropdown-menu__item:hover) {
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.06);
}

:deep(.custom-dropdown .el-dropdown-menu__item .el-icon) {
  margin-right: 8px;
  font-size: 16px;
}
</style>
