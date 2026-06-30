<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">绩效考核系统</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('employees')" index="/employees">
          <el-icon><UserFilled /></el-icon>
          <span>员工管理</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('departments')" index="/departments">
          <el-icon><OfficeBuilding /></el-icon>
          <span>部门岗位</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('cycles')" index="/cycles">
          <el-icon><Calendar /></el-icon>
          <span>考核周期</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('kpi-templates')" index="/kpi-templates">
          <el-icon><Document /></el-icon>
          <span>KPI模板</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('config')" index="/config">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('audit-logs')" index="/audit-logs">
          <el-icon><Document /></el-icon>
          <span>操作日志</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('appeals')" index="/appeals">
          <el-icon><Bell /></el-icon>
          <span>申诉管理</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('summary')" index="/summary">
          <el-icon><TrendCharts /></el-icon>
          <span>绩效汇总</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('reports')" index="/reports">
          <el-icon><Download /></el-icon>
          <span>报表导出</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('distribution-review')" index="/distribution-review">
          <el-icon><ScaleToOriginal /></el-icon>
          <span>强制分布处理</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('kpi-adjustment-request')" index="/kpi-adjustment-request">
          <el-icon><Edit /></el-icon>
          <span>KPI调整申请</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('kpi-adjustment-approval')" index="/kpi-adjustment-approval">
          <el-icon><Checked /></el-icon>
          <span>KPI调整审批</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('score-sheet')" index="/score-sheet">
          <el-icon><Edit /></el-icon>
          <span>上级评分</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('approval-workbench')" index="/approval-workbench">
          <el-icon><Checked /></el-icon>
          <span>审批工作台</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('interviews')" index="/interviews">
          <el-icon><ChatDotRound /></el-icon>
          <span>绩效面谈</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('peer-review')" index="/peer-review">
          <el-icon><Share /></el-icon>
          <span>协作评分</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('my-performance')" index="/my-performance">
          <el-icon><TrendCharts /></el-icon>
          <span>我的绩效</span>
        </el-menu-item>
        <el-menu-item v-if="canSee('appeal')" index="/appeal">
          <el-icon><Bell /></el-icon>
          <span>申诉</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              {{ authStore.user?.name || authStore.user?.username }}
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

const router = useRouter()
const $route = useRoute()
const authStore = useAuthStore()

const role = computed(() => authStore.user?.role || '')

const menuPermissions = {
  'admin': ['employees', 'departments', 'cycles', 'kpi-templates', 'config', 'appeals', 'summary', 'reports', 'score-sheet', 'approval-workbench', 'interviews', 'peer-review', 'kpi-adjustment-approval', 'audit-logs'],
  'hr': ['employees', 'cycles', 'appeals', 'summary', 'reports', 'distribution-review', 'kpi-adjustment-approval', 'audit-logs'],
  'manager': ['score-sheet', 'approval-workbench', 'interviews', 'kpi-adjustment-request'],
  'employee': ['my-performance', 'appeal'],
  'peer': ['peer-review']
}

function canSee(menu) {
  const allowed = menuPermissions[role.value] || []
  return allowed.includes(menu)
}

function handleCommand(cmd) {
  if (cmd === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}
.sidebar {
  background-color: #304156;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #1f2d3d;
}
.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
.header-right {
  display: flex;
  align-items: center;
}
.user-info {
  cursor: pointer;
  color: #606266;
}
</style>
