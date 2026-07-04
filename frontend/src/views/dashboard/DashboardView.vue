<template>
  <div class="dashboard-container">
    <!-- 顶部：6阶段全流程图 -->
    <el-card class="flow-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>{{ pageTitle }}</span>
          <el-tag v-if="activeCycle" type="primary" size="small">{{ activeCycle.name }}</el-tag>
        </div>
      </template>

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
              <el-tag size="small" type="warning">进行中</el-tag>
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
        <el-alert
          :title="currentTask.title"
          :type="currentTask.type"
          :description="currentTask.desc"
          show-icon
          :closable="false"
        >
          <template #default>
            <el-button
              v-if="currentTask.link"
              type="primary"
              size="small"
              @click="$router.push(currentTask.link)"
            >
              {{ currentTask.btnText }}
            </el-button>
          </template>
        </el-alert>
      </div>
    </el-card>

    <!-- 统计卡片区 -->
    <el-row :gutter="20" class="stats-row">
      <el-col
        :xs="12" :sm="8" :md="6"
        v-for="card in statCards"
        :key="card.label"
      >
        <el-card
          class="stat-card"
          shadow="hover"
          :class="{ 'highlight': card.highlight }"
          @click="card.link && $router.push(card.link)"
        >
          <div class="stat-icon" :style="{ color: card.color }">
            <el-icon size="28"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">{{ card.label }}</div>
            <div class="stat-value" :style="{ color: card.color }">
              {{ card.value }}
            </div>
            <div class="stat-sublabel" v-if="card.sublabel">{{ card.sublabel }}</div>
          </div>
          <el-tag
            v-if="card.badge"
            class="stat-badge"
            type="danger"
            effect="dark"
            size="small"
          >{{ card.badge }}</el-tag>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作区 -->
    <el-card class="mt-20" shadow="hover" v-if="quickActions.length > 0">
      <template #header>
        <div class="card-title">快捷操作</div>
      </template>
      <el-row :gutter="20">
        <el-col
          :xs="12" :sm="8" :md="6"
          v-for="action in quickActions"
          :key="action.label"
        >
          <el-button
            :type="action.type"
            size="large"
            style="width: 100%; margin-bottom: 10px;"
            @click="$router.push(action.link)"
          >
            <el-icon v-if="action.icon"><component :is="action.icon" /></el-icon>
            {{ action.label }}
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 最近考核周期 -->
    <el-card class="mt-20" shadow="hover">
      <template #header>
        <div class="card-title">最近考核周期</div>
      </template>
      <el-table :data="recentCycles" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type === 'quarterly' ? '季度' : '年度' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="viewCycleDetail(row)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
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
  TrendCharts, View, List, ArrowRight
} from '@element-plus/icons-vue'
import { listCycles } from '@/api/cycles'
import request from '@/api/request'

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

// 判断某阶段是否已完成（简化逻辑：当前周期状态已越过该阶段）
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

// 统计卡片数据
const statCards = computed(() => {
  const role = userRole.value
  const data = dashboardData.value

  if (role === 'admin') {
    return [
      { label: '员工总数', value: data.employee_count || 0, icon: 'User', color: '#409eff', link: '/employees' },
      { label: '部门数量', value: data.department_count || 0, icon: 'OfficeBuilding', color: '#67c23a', link: '/departments' },
      { label: '考核周期', value: data.cycle_count || 0, icon: 'Calendar', color: '#e6a23c', link: '/cycles' },
      { label: '进行中', value: data.active_cycle_count || 0, icon: 'Star', color: '#f56c6c', link: '/cycles', highlight: true },
    ]
  }

  if (role === 'hr') {
    return [
      { label: '待汇总', value: data.to_summary || 0, icon: 'TrendCharts', color: '#f56c6c', badge: data.to_summary > 0 ? ' urgent' : '', link: '/summary', highlight: true },
      { label: '待审批', value: data.to_approve || 0, icon: 'DocumentChecked', color: '#e6a23c', badge: data.to_approve > 0 ? ' pending' : '', link: '/approval-workbench' },
      { label: '待归档', value: data.to_archive || 0, icon: 'Download', color: '#67c23a', link: '/reports' },
      { label: '待处理申诉', value: data.pending_appeals || 0, icon: 'Warning', color: '#409eff', link: '/appeals' },
    ]
  }

  if (role === 'manager') {
    return [
      { label: '待评分', value: data.to_review || 0, icon: 'Edit', color: '#f56c6c', badge: data.to_review > 0 ? ' pending' : '', link: '/score-sheet', highlight: true },
      { label: '待审批', value: data.to_approve || 0, icon: 'DocumentChecked', color: '#e6a23c', link: '/approval-workbench' },
      { label: '待面谈', value: data.to_interview || 0, icon: 'ChatDotRound', color: '#67c23a', link: '/interviews' },
      { label: '下属总数', value: data.subordinate_count || 0, icon: 'User', color: '#409eff', link: '/employees' },
    ]
  }

  if (role === 'employee') {
    return [
      { label: '当前状态', value: statusText(data.self_status) || '无', icon: 'View', color: '#409eff' },
      { label: '待自评', value: data.pending_self || 0, icon: 'Edit', color: '#f56c6c', badge: data.pending_self > 0 ? ' pending' : '', link: '/self-assessment', highlight: true },
      { label: '历史考核', value: data.total_records || 0, icon: 'List', color: '#67c23a', link: '/my-performance' },
      { label: '申诉记录', value: data.appeal_count || 0, icon: 'Warning', color: '#e6a23c', link: '/appeal' },
    ]
  }

  if (role === 'peer') {
    return [
      { label: '待协作评分', value: data.pending_reviews || 0, icon: 'Edit', color: '#f56c6c', badge: data.pending_reviews > 0 ? ' pending' : '', link: '/peer-review', highlight: true },
      { label: '已完成', value: data.completed_reviews || 0, icon: 'Check', color: '#67c23a' },
      { label: '总协作任务', value: data.total_reviews || 0, icon: 'List', color: '#409eff' },
    ]
  }

  if (role === 'executive') {
    return [
      { label: '员工总数', value: data.employee_count || 0, icon: 'User', color: '#409eff' },
      { label: '考核覆盖率', value: (data.coverage_rate || 0) + '%', icon: 'TrendCharts', color: '#67c23a' },
      { label: '公司平均分', value: data.avg_score || 0, icon: 'Star', color: '#e6a23c' },
      { label: '强制调整', value: data.adjusted_count || 0, icon: 'Warning', color: '#f56c6c' },
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
          dashboardData.value = res
          badgeCounts.value = res
        }
      } catch (e) {
        console.warn('Dashboard API error:', e)
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
.dashboard-container {
  padding: 20px;
}

.flow-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: bold;
}

.process-flow-wrapper {
  padding: 20px 0;
  overflow-x: auto;
}

.process-flow {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  position: relative;
  min-width: 800px;
  padding: 0 10px;
}

.flow-lines {
  position: absolute;
  top: 35px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 0 60px;
  z-index: 0;
  pointer-events: none;
}

.flow-line {
  flex: 1;
  height: 3px;
  background: #e4e7ed;
  margin: 0 10px;
  transition: all 0.3s;
}

.flow-line.active {
  background: #67c23a;
}

.stage-node {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 140px;
  padding: 12px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  background: #fff;
  border: 2px solid #e4e7ed;
}

.stage-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.stage-node.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.stage-node.active .stage-icon {
  background: #409eff;
  color: #fff;
}

.stage-node.completed {
  border-color: #67c23a;
  background: #f0f9ff;
}

.stage-node.completed .stage-icon {
  background: #67c23a;
  color: #fff;
}

.stage-node.current {
  border-color: #e6a23c;
  box-shadow: 0 0 0 4px rgba(230, 162, 60, 0.2);
  animation: pulse 2s infinite;
}

.stage-node.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(230, 162, 60, 0.2); }
  50% { box-shadow: 0 0 0 8px rgba(230, 162, 60, 0.1); }
}

.stage-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  min-width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  border-radius: 50%;
  background: #f56c6c;
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  z-index: 2;
}

.stage-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #909399;
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 8px;
  transition: all 0.3s;
}

.stage-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.stage-desc {
  font-size: 12px;
  color: #909399;
  text-align: center;
}

.stage-status {
  margin-top: 6px;
}

.current-task-bar {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #dcdfe6;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  padding: 16px;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.stat-card.highlight {
  border: 1px solid #f56c6c;
}

.stat-icon {
  margin-right: 12px;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-sublabel {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 2px;
}

.stat-badge {
  position: absolute;
  top: 8px;
  right: 8px;
}

.mt-20 {
  margin-top: 20px;
}

.card-title {
  font-weight: bold;
  font-size: 16px;
}

@media (max-width: 768px) {
  .process-flow-wrapper {
    overflow-x: scroll;
  }
  .stage-node {
    width: 110px;
    padding: 8px 4px;
  }
  .stage-title {
    font-size: 12px;
  }
  .stage-desc {
    font-size: 10px;
  }
}
</style>
