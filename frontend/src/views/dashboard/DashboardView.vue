<template>
  <div class="dashboard-container">
    <!-- 高管仪表盘：独立组件，只读 -->
    <ExecutiveDashboard v-if="userRole === 'executive'" />

    <template v-else>
    <!-- 顶部：6阶段全流程图 -->
    <div class="dashboard-hero-card">
      <div class="hero-header">
        <div class="hero-title">
          <span class="hero-title-text" role="heading" aria-level="1">{{ pageTitle }}</span>
          <span v-if="activeCycle" class="hero-cycle-tag">{{ activeCycle.name }}</span>
        </div>
        <div class="hero-meta">
          <span class="meta-item">
            <el-icon><Calendar /></el-icon>
            {{ new Date().toLocaleDateString('zh-CN') }}
          </span>
        </div>
      </div>

      <div class="process-flow-wrapper">
        <div class="process-flow">
          <div
            v-for="(stage, index) in stages"
            :key="stage.key"
            class="stage-node"
            :class="{
              'active': isRoleStage(stage.key),
              'completed': isCompleted(stage.key),
              'current': isCurrent(stage.key),
              'disabled': !isRoleStage(stage.key) && !isCompleted(stage.key)
            }"
            @click="handleStageClick(stage)"
          >
            <div class="stage-badge" v-if="getBadgeCount(stage.key) > 0">
              {{ getBadgeCount(stage.key) }}
            </div>
            <div class="stage-icon">
              <el-icon v-if="isCompleted(stage.key)"><Check /></el-icon>
              <span v-else>{{ index + 1 }}</span>
            </div>
            <div class="stage-title">{{ stage.title }}</div>
            <div class="stage-desc">{{ stage.desc }}</div>
            <div class="stage-status" v-if="isCurrent(stage.key)">
              <span class="status-pill">进行中</span>
            </div>
          </div>

          <!-- 连接线 -->
          <div class="flow-lines">
            <div
              v-for="n in 5"
              :key="n"
              class="flow-line"
              :class="{ 'active': isLineActive(n) }"
            ></div>
          </div>
        </div>
      </div>

      <!-- 当前任务提示卡片 -->
      <div class="current-task-bar" v-if="currentTask">
        <div class="task-alert" :class="currentTask.type">
          <div class="task-alert-icon">
            <el-icon size="20"><Warning /></el-icon>
          </div>
          <div class="task-alert-content">
            <div class="task-alert-title">{{ currentTask.title }}</div>
            <div class="task-alert-desc">{{ currentTask.desc }}</div>
          </div>
          <div class="task-alert-action">
            <el-button
              v-if="currentTask.link"
              type="primary"
              size="small"
              @click="$router.push(currentTask.link)"
            >
              {{ currentTask.btnText }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 统计卡片区 -->
    <div class="stats-grid">
      <div
        v-for="card in statCards"
        :key="card.label"
        class="stat-card"
        :class="{ 'highlight': card.highlight }"
        @click="card.link && $router.push(card.link)"
      >
        <div class="stat-card-inner">
          <div class="stat-icon-wrapper" :style="{ '--icon-color': card.color }">
            <el-icon size="24"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">{{ card.label }}</div>
            <div class="stat-value" :style="{ color: card.color }">
              {{ card.value }}
            </div>
            <div class="stat-sublabel" v-if="card.sublabel">{{ card.sublabel }}</div>
          </div>
          <div v-if="card.badge" class="stat-badge">
            {{ card.badge }}
          </div>
        </div>
        <div class="stat-card-glow" :style="{ background: card.color }"></div>
      </div>
    </div>

    <!-- 快捷操作区 -->
    <div class="dashboard-card" v-if="quickActions.length > 0">
      <div class="card-header-custom">
        <div class="card-header-icon">
          <el-icon size="18"><Star /></el-icon>
        </div>
        <span class="card-header-title">快捷操作</span>
      </div>
      <div class="quick-actions-grid">
        <div
          v-for="action in quickActions"
          :key="action.label"
          class="action-btn"
          role="button"
          tabindex="0"
          :class="action.type"
          @click="$router.push(action.link)"
          @keydown.enter="$router.push(action.link)"
        >
          <el-icon size="20" v-if="action.icon"><component :is="action.icon" /></el-icon>
          <span class="action-label">{{ action.label }}</span>
          <el-icon size="14" class="action-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 最近考核周期 -->
    <div class="dashboard-card">
      <div class="card-header-custom">
        <div class="card-header-icon">
          <el-icon size="18"><Calendar /></el-icon>
        </div>
        <span class="card-header-title">最近考核周期</span>
      </div>
      <el-table :data="recentCycles" style="width: 100%" v-loading="loading" class="custom-table">
        <el-table-column prop="name" label="名称" min-width="180">
          <template #default="{ row }">
            <span class="table-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <span class="type-tag" :class="row.type">{{ row.type === 'quarterly' ? '季度' : '年度' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <span class="status-tag" :class="row.status">
              {{ statusText(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <el-progress
              v-if="row.status !== 'not_started' && row.status !== 'archived'"
              :percentage="Math.round(cycleProgress[row.id]?.self_completion_rate || 0)"
              :status="cycleProgress[row.id]?.self_completion_rate === 100 ? 'success' : ''"
              :stroke-width="8"
              :text-inside="true"
              class="custom-progress"
            />
            <span v-else class="progress-placeholder">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <button class="table-action-btn" @click="viewCycleDetail(row)">
              查看
            </button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import {
  Check, Setting, User, OfficeBuilding, Calendar, Star,
  Edit, DocumentChecked, ChatDotRound, Download, Warning,
  TrendCharts, View, List, ArrowRight, Flag
} from '@element-plus/icons-vue'
import { listCycles, getCycleProgress } from '@/api/cycles'
import request from '@/api/request'
import ExecutiveDashboard from './ExecutiveDashboard.vue'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const userRole = computed(() => authStore.user?.role || '')
const userName = computed(() => authStore.user?.name || '')

// 6阶段定义
const stages = [
  { key: 'prepare', title: '准备阶段', desc: '配置/导入/启动', status: 'not_started', route: '/config' },
  { key: 'scoring', title: '评分阶段', desc: '自评→上级→协作', status: 'pending_self', route: '/self-assessment' },
  { key: 'summary', title: '汇总阶段', desc: '加权/强制分布', status: 'pending_summary', route: '/summary' },
  { key: 'approval', title: '审批阶段', desc: '上级→HR审批', status: 'pending_approval', route: '/approval-workbench' },
  { key: 'interview', title: '面谈阶段', desc: '绩效面谈', status: 'pending_interview', route: '/interviews' },
  { key: 'publish', title: '发布归档', desc: '查看/归档/导出', status: 'published', route: '/reports' },
]

// 页面标题
const pageTitle = computed(() => {
  const titles = {
    admin: '系统管理员工作台',
    hr: 'HR 专员工作台',
    manager: '部门经理工作台',
    employee: '我的绩效首页',
    peer: '协作评分工作台',
    executive: '高管数据视图',
  }
  return titles[userRole.value] || '仪表盘'
})

// 该角色负责的阶段
const roleStages = computed(() => {
  const map = {
    admin: ['prepare'],
    hr: ['prepare', 'summary', 'approval', 'publish'],
    manager: ['scoring', 'approval', 'interview'],
    employee: ['scoring', 'publish'],
    peer: ['scoring'],
    executive: ['publish'],
  }
  return map[userRole.value] || []
})

// 判断某阶段是否属于该角色
function isRoleStage(key) {
  return roleStages.value.includes(key)
}

// 判断某阶段是否已完成
function isCompleted(key) {
  if (!activeCycle.value) return false
  const order = ['not_started', 'pending_self', 'pending_manager', 'pending_peer', 'pending_summary', 'pending_distribution_review', 'pending_approval', 'pending_interview', 'published', 'archived']
  const currentIndex = order.indexOf(activeCycle.value.status)
  const stageIndex = order.indexOf(stages.find(s => s.key === key)?.status)
  return currentIndex > stageIndex && stageIndex !== -1
}

// 判断是否为当前阶段
function isCurrent(key) {
  if (!activeCycle.value) return false
  const statusMap = {
    'prepare': ['not_started'],
    'scoring': ['pending_self', 'pending_manager', 'pending_peer'],
    'summary': ['pending_summary', 'pending_distribution_review'],
    'approval': ['pending_approval'],
    'interview': ['pending_interview'],
    'publish': ['published', 'archived'],
  }
  return statusMap[key]?.includes(activeCycle.value.status) || false
}

// 连接线是否激活
function isLineActive(n) {
  const completedCount = stages.filter((s, i) => i < n && isCompleted(s.key)).length
  return completedCount >= n
}

// 获取徽章数字
function getBadgeCount(key) {
  const counts = badgeCounts.value
  const map = {
    'prepare': counts.pending_config || 0,
    'scoring': counts.to_score || 0,
    'summary': counts.to_summary || 0,
    'approval': counts.to_approve || 0,
    'interview': counts.to_interview || 0,
    'publish': counts.to_archive || 0,
  }
  return isRoleStage(key) ? (map[key] || 0) : 0
}

// 处理阶段点击
function handleStageClick(stage) {
  if (!isRoleStage(stage.key)) {
    ElMessage.warning('此环节不属于您的职责范围，如需处理请联系 HR')
    return
  }
  router.push(stage.route)
}

// 数据状态
const activeCycle = ref(null)
const recentCycles = ref([])
const badgeCounts = ref({})
const dashboardData = ref({})
const cycleProgress = ref({})

// 统计卡片数据（使用新设计系统的颜色）
const statCards = computed(() => {
  const role = userRole.value
  const data = dashboardData.value

  if (role === 'admin') {
    return [
      { label: '员工总数', value: data.employee_count || 0, icon: 'User', color: '#6366f1', link: '/employees' },
      { label: '部门数量', value: data.department_count || 0, icon: 'OfficeBuilding', color: '#10b981', link: '/departments' },
      { label: '考核周期', value: data.cycle_count || 0, icon: 'Calendar', color: '#f59e0b', link: '/cycles' },
      { label: '进行中', value: data.active_cycle_count || 0, icon: 'Star', color: '#ef4444', link: '/cycles', highlight: true },
    ]
  }

  if (role === 'hr') {
    return [
      { label: '当前周期', value: data.cycle_count || 0, icon: 'Calendar', color: '#6366f1', link: '/cycles' },
      { label: '待汇总', value: data.to_summary || 0, icon: 'TrendCharts', color: '#ef4444', badge: data.to_summary > 0 ? 'urgent' : '', link: '/summary', highlight: true },
      { label: '待审批', value: data.to_approve || 0, icon: 'DocumentChecked', color: '#f59e0b', badge: data.to_approve > 0 ? 'pending' : '', link: '/approval-workbench' },
      { label: '待处理申诉', value: data.pending_appeals || 0, icon: 'Warning', color: '#10b981', link: '/appeals' },
      { label: '强制分布超标', value: data.force_distribution_exceeded || 0, icon: 'Flag', color: '#64748b', link: '/distribution-review' },
    ]
  }

  if (role === 'manager') {
    return [
      { label: '待评分', value: data.to_review || 0, icon: 'Edit', color: '#ef4444', badge: data.to_review > 0 ? 'pending' : '', link: '/score-sheet', highlight: true },
      { label: '待审批', value: data.to_approve || 0, icon: 'DocumentChecked', color: '#f59e0b', link: '/approval-workbench' },
      { label: '待面谈', value: data.to_interview || 0, icon: 'ChatDotRound', color: '#10b981', link: '/interviews' },
      { label: '下属总数', value: data.subordinate_count || 0, icon: 'User', color: '#6366f1', link: '/employees' },
    ]
  }

  if (role === 'employee') {
    return [
      { label: '当前状态', value: statusText(data.self_status) || '无', icon: 'View', color: '#6366f1' },
      { label: '待自评', value: data.pending_self || 0, icon: 'Edit', color: '#ef4444', badge: data.pending_self > 0 ? 'pending' : '', link: '/self-assessment', highlight: true },
      { label: '历史考核', value: data.total_records || 0, icon: 'List', color: '#10b981', link: '/my-performance' },
      { label: '申诉记录', value: data.appeal_count || 0, icon: 'Warning', color: '#f59e0b', link: '/appeal' },
    ]
  }

  if (role === 'peer') {
    return [
      { label: '待协作评分', value: data.pending_reviews || 0, icon: 'Edit', color: '#ef4444', badge: data.pending_reviews > 0 ? 'pending' : '', link: '/peer-review', highlight: true },
      { label: '已完成', value: data.completed_reviews || 0, icon: 'Check', color: '#10b981' },
      { label: '总协作任务', value: data.total_reviews || 0, icon: 'List', color: '#6366f1' },
    ]
  }

  if (role === 'executive') {
    return [
      { label: '员工总数', value: data.employee_count || 0, icon: 'User', color: '#6366f1' },
      { label: '考核覆盖率', value: (data.coverage_rate || 0) + '%', icon: 'TrendCharts', color: '#10b981' },
      { label: '公司平均分', value: data.avg_score || 0, icon: 'Star', color: '#f59e0b' },
      { label: '强制调整', value: data.adjusted_count || 0, icon: 'Warning', color: '#ef4444' },
    ]
  }

  return []
})

// 快捷操作
const quickActions = computed(() => {
  const role = userRole.value
  const actions = {
    admin: [
      { label: '系统配置', type: 'primary', link: '/config', icon: 'Setting' },
      { label: 'KPI模板', type: 'success', link: '/kpi-templates', icon: 'DocumentChecked' },
      { label: '员工导入', type: 'warning', link: '/employees', icon: 'User' },
    ],
    hr: [
      { label: '创建考核周期', type: 'primary', link: '/cycles', icon: 'Calendar' },
      { label: '汇总处理', type: 'danger', link: '/summary', icon: 'TrendCharts' },
      { label: '审批工作台', type: 'warning', link: '/approval-workbench', icon: 'DocumentChecked' },
      { label: '报表导出', type: 'success', link: '/reports', icon: 'Download' },
    ],
    manager: [
      { label: '批量评分', type: 'primary', link: '/score-sheet', icon: 'Edit' },
      { label: '审批确认', type: 'warning', link: '/approval-workbench', icon: 'DocumentChecked' },
      { label: '绩效面谈', type: 'success', link: '/interviews', icon: 'ChatDotRound' },
    ],
    employee: [
      { label: '进入自评', type: 'primary', link: '/self-assessment', icon: 'Edit' },
      { label: '查看历史', type: 'success', link: '/my-performance', icon: 'TrendCharts' },
      { label: '发起申诉', type: 'warning', link: '/appeal', icon: 'Warning' },
    ],
    peer: [
      { label: '协作评分', type: 'primary', link: '/peer-review', icon: 'Edit' },
    ],
    executive: [
      { label: '查看报表', type: 'primary', link: '/reports', icon: 'TrendCharts' },
    ],
  }
  return actions[role] || []
})

// 当前任务提示
const currentTask = computed(() => {
  const role = userRole.value
  const data = dashboardData.value

  if (role === 'admin' && (data.pending_config > 0)) {
    return { title: '系统配置待完成', type: 'warning', desc: `还有 ${data.pending_config} 项配置未完成，请尽快完成`, link: '/config', btnText: '去配置' }
  }
  if (role === 'hr' && (data.to_summary > 0)) {
    return { title: '有待汇总考核', type: 'error', desc: `${data.to_summary} 个周期待触发汇总计算`, link: '/summary', btnText: '去汇总' }
  }
  if (role === 'manager' && (data.to_review > 0)) {
    return { title: '有待评分下属', type: 'error', desc: `您有 ${data.to_review} 名下属待评分`, link: '/score-sheet', btnText: '去评分' }
  }
  if (role === 'employee' && (data.pending_self > 0)) {
    return { title: '您有待完成的自评', type: 'error', desc: '请尽快完成自评提交', link: '/self-assessment', btnText: '去自评' }
  }
  if (role === 'peer' && (data.pending_reviews > 0)) {
    return { title: '有待协作评分', type: 'warning', desc: `您有 ${data.pending_reviews} 条协作评分任务`, link: '/peer-review', btnText: '去评分' }
  }
  return null
})

// 状态文本
function statusText(status) {
  const map = {
    not_started: '未开始',
    pending_self: '自评中',
    pending_manager: '上级评分中',
    pending_peer: '协作评分中',
    pending_summary: '汇总中',
    pending_distribution_review: '强制分布审核',
    pending_approval: '审批中',
    pending_interview: '面谈中',
    published: '已发布',
    archived: '已归档',
    cancelled: '已取消',
  }
  return map[status] || status
}

function statusTagType(status) {
  const map = {
    not_started: 'info',
    pending_self: 'warning',
    pending_manager: 'warning',
    pending_peer: 'warning',
    pending_summary: 'primary',
    pending_distribution_review: 'danger',
    pending_approval: 'primary',
    pending_interview: 'success',
    published: 'success',
    archived: 'info',
  }
  return map[status] || ''
}

function viewCycleDetail(row) {
  router.push(`/cycles/${row.id}`)
}

// 加载数据
onMounted(async () => {
  loading.value = true
  try {
    const cycleRes = await listCycles()
    const cycles = cycleRes || []
    recentCycles.value = cycles.slice(0, 5)
    activeCycle.value = cycles.find(c => c.status !== 'not_started' && c.status !== 'archived') || cycles[0] || null

    // 根据角色加载仪表盘数据
    const role = userRole.value
    if (role) {
      try {
        const res = await request.get(`/dashboard${role === 'admin' || role === 'hr' ? '' : '/' + role}`)
        if (res) {
          dashboardData.value = res.stats || res
          badgeCounts.value = res.stats || res
        }
      } catch (e) {
        console.warn('Dashboard API error:', e)
      }
    }

    // 加载各周期进度
    for (const cycle of recentCycles.value) {
      if (cycle.status !== 'not_started' && cycle.status !== 'archived') {
        try {
          const progress = await getCycleProgress(cycle.id)
          cycleProgress.value[cycle.id] = progress
        } catch (e) {
          console.warn('Progress fetch error:', e)
        }
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* Base layout */
.dashboard-container {
  padding: 0;
  max-width: 1400px;
  margin: 0 auto;
}

/* Hero Card: the main process flow card */
.dashboard-hero-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 24px 28px;
  margin-bottom: 24px;
  border: 1px solid var(--border-light);
}

.hero-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.hero-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hero-title-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}

.hero-cycle-tag {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(99, 102, 241, 0.05) 100%);
  color: var(--primary-color);
  border: 1px solid rgba(99, 102, 241, 0.15);
  letter-spacing: 0.3px;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

/* Process Flow */
.process-flow-wrapper {
  padding: 24px 0 16px;
  overflow-x: auto;
}

.process-flow {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  position: relative;
  min-width: 800px;
  padding: 0 16px;
}

.flow-lines {
  position: absolute;
  top: 40px;
  left: 60px;
  right: 60px;
  display: flex;
  justify-content: space-between;
  z-index: 0;
  pointer-events: none;
  gap: 8px;
}

.flow-line {
  flex: 1;
  height: 3px;
  background: var(--border-light);
  border-radius: 2px;
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
}

.flow-line::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, var(--success-color) 0%, var(--success-color) 100%);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform var(--transition-slow);
  border-radius: 2px;
}

.flow-line.active::after {
  transform: scaleX(1);
}

/* Stage Node */
.stage-node {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 150px;
  padding: 16px 12px;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base);
  background: var(--bg-card);
  border: 2px solid var(--border-light);
  box-shadow: var(--shadow-sm);
}

.stage-node:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary-light);
}

.stage-node.active {
  border-color: var(--primary-color);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.06) 0%, rgba(99, 102, 241, 0.02) 100%);
  box-shadow: var(--shadow-glow);
}

.stage-node.active .stage-icon {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.stage-node.completed {
  border-color: var(--success-color);
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.06) 0%, rgba(16, 185, 129, 0.02) 100%);
}

.stage-node.completed .stage-icon {
  background: linear-gradient(135deg, var(--success-color) 0%, #059669 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.stage-node.current {
  border-color: var(--accent-color);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.06) 0%, rgba(245, 158, 11, 0.02) 100%);
  animation: pulse-glow 2.5s infinite ease-in-out;
}

.stage-node.current .stage-icon {
  background: linear-gradient(135deg, var(--accent-color) 0%, #d97706 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.stage-node.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stage-node.disabled:hover {
  transform: none;
  box-shadow: var(--shadow-sm);
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.15); }
  50% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0.08); }
}

.stage-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--danger-color) 0%, #dc2626 100%);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  z-index: 2;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);
  padding: 0 5px;
}

.stage-icon {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-color);
  color: var(--text-muted);
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
  transition: all var(--transition-base);
}

.stage-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
  text-align: center;
}

.stage-desc {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.4;
  font-weight: 500;
}

.stage-status {
  margin-top: 8px;
}

.status-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.06) 100%);
  color: var(--accent-color);
  border: 1px solid rgba(245, 158, 11, 0.2);
  letter-spacing: 0.3px;
}

/* Current Task Bar */
.current-task-bar {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed var(--border-color);
}

.task-alert {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.task-alert:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.task-alert.warning {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.06) 0%, rgba(245, 158, 11, 0.02) 100%);
  border-color: rgba(245, 158, 11, 0.15);
}

.task-alert.error {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.06) 0%, rgba(239, 68, 68, 0.02) 100%);
  border-color: rgba(239, 68, 68, 0.15);
}

.task-alert-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.06) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-color);
  flex-shrink: 0;
}

.task-alert.error .task-alert-icon {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(239, 68, 68, 0.06) 100%);
  color: var(--danger-color);
}

.task-alert-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.task-alert-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.task-alert-desc {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.task-alert-action {
  flex-shrink: 0;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  position: relative;
  cursor: pointer;
  transition: all var(--transition-base);
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-xl);
}

.stat-card.highlight {
  border-color: rgba(239, 68, 68, 0.2);
  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.08);
}

.stat-card.highlight:hover {
  box-shadow: 0 8px 30px rgba(239, 68, 68, 0.12);
}

.stat-card-inner {
  display: flex;
  align-items: center;
  padding: 20px;
  position: relative;
  z-index: 1;
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  flex-shrink: 0;
  background: rgba(99, 102, 241, 0.08);
  color: var(--icon-color, var(--primary-color));
  transition: all var(--transition-base);
}

.stat-card:hover .stat-icon-wrapper {
  transform: scale(1.1) rotate(-4deg);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

.stat-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 0.2px;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.5px;
  line-height: 1;
  color: var(--icon-color, var(--primary-color));
  transition: all var(--transition-base);
}

.stat-card:hover .stat-value {
  transform: scale(1.05);
}

.stat-sublabel {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  margin-top: 2px;
}

.stat-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 20px;
  background: linear-gradient(135deg, var(--danger-color) 0%, #dc2626 100%);
  color: #fff;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);
  letter-spacing: 0.5px;
  text-transform: uppercase;
  z-index: 1;
}

.stat-card-glow {
  position: absolute;
  bottom: -40px;
  right: -40px;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.15;
  transition: opacity var(--transition-base);
  z-index: 0;
}

.stat-card:hover .stat-card-glow {
  opacity: 0.25;
}

/* Dashboard Card (replaces el-card for tables and lists) */
.dashboard-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  padding: 24px;
  margin-bottom: 24px;
  transition: all var(--transition-base);
}

.dashboard-card:hover {
  box-shadow: var(--shadow-md);
}

.card-header-custom {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.card-header-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(99, 102, 241, 0.04) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
}

.card-header-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}

/* Quick Actions */
.quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  border: 1px solid var(--border-light);
  background: var(--bg-card);
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  position: relative;
  overflow: hidden;
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--border-light);
  transition: all var(--transition-base);
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-btn:hover::before {
  height: 4px;
}

.action-btn.primary::before {
  background: var(--primary-color);
}
.action-btn.success::before {
  background: var(--success-color);
}
.action-btn.warning::before {
  background: var(--accent-color);
}
.action-btn.danger::before {
  background: var(--danger-color);
}

.action-label {
  flex: 1;
}

.action-arrow {
  color: var(--text-muted);
  transition: transform var(--transition-fast);
}

.action-btn:hover .action-arrow {
  transform: translateX(3px);
  color: var(--primary-color);
}

/* Custom Table */
:deep(.custom-table) {
  --el-table-border-color: var(--border-light);
  --el-table-header-bg-color: var(--bg-color);
  --el-table-row-hover-bg-color: rgba(99, 102, 241, 0.04);
}

:deep(.custom-table .el-table__header th) {
  font-weight: 700;
  font-size: 13px;
  color: var(--text-secondary);
  letter-spacing: 0.3px;
  padding: 14px 12px;
}

:deep(.custom-table .el-table__row td) {
  padding: 14px 12px;
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.table-name {
  font-weight: 600;
  color: var(--text-primary);
}

.type-tag {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  background: rgba(99, 102, 241, 0.08);
  color: var(--primary-color);
  letter-spacing: 0.3px;
}

.type-tag.annual {
  background: rgba(16, 185, 129, 0.08);
  color: var(--success-color);
}

.status-tag {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  display: inline-block;
  letter-spacing: 0.3px;
}

.status-tag.not_started {
  background: rgba(148, 163, 184, 0.1);
  color: var(--text-muted);
}
.status-tag.pending_self,
.status-tag.pending_manager,
.status-tag.pending_peer {
  background: rgba(245, 158, 11, 0.1);
  color: var(--accent-color);
}
.status-tag.pending_summary,
.status-tag.pending_approval {
  background: rgba(99, 102, 241, 0.1);
  color: var(--primary-color);
}
.status-tag.pending_interview {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}
.status-tag.published,
.status-tag.archived {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}
.status-tag.cancelled {
  background: rgba(148, 163, 184, 0.1);
  color: var(--text-muted);
}

.table-action-btn {
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  border: none;
  background: rgba(99, 102, 241, 0.08);
  color: var(--primary-color);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.table-action-btn:hover {
  background: var(--primary-color);
  color: #fff;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.25);
}

/* Custom Progress */
:deep(.custom-progress .el-progress-bar__outer) {
  border-radius: 4px;
  background: var(--border-light);
}

:deep(.custom-progress .el-progress-bar__inner) {
  border-radius: 4px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-placeholder {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
}

/* Mobile */
@media (max-width: 768px) {
  .process-flow-wrapper {
    overflow-x: scroll;
  }
  .stage-node {
    width: 120px;
    padding: 12px 8px;
  }
  .stage-title {
    font-size: 12px;
  }
  .stage-desc {
    font-size: 10px;
  }
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .quick-actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .hero-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .task-alert {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
