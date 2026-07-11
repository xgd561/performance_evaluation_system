<template>
  <div class="executive-dashboard">
    <!-- 部门筛选 -->
    <div class="dashboard-card filter-card">
      <div class="card-header-custom">
        <div class="card-header-icon">
          <el-icon size="18"><Filter /></el-icon>
        </div>
        <span class="card-header-title">数据筛选</span>
      </div>
      <el-form :inline="true">
        <el-form-item label="部门筛选">
          <el-select v-model="selectedDept" placeholder="全部部门" clearable @change="onDeptChange" class="filter-select">
            <el-option v-for="dept in departments" :key="dept.id" :label="dept.name" :value="dept.id" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-card-inner">
          <div class="stat-icon-wrapper" style="--icon-color: #6366f1">
            <el-icon size="24"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">员工总数</div>
            <div class="stat-value" style="color: #6366f1">{{ stats.total_employees }}</div>
          </div>
        </div>
        <div class="stat-card-glow" style="background: #6366f1"></div>
      </div>

      <div class="stat-card">
        <div class="stat-card-inner">
          <div class="stat-icon-wrapper" style="--icon-color: #10b981">
            <el-icon size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">考核覆盖率</div>
            <div class="stat-value" style="color: #10b981">{{ stats.coverage_rate }}%</div>
          </div>
        </div>
        <div class="stat-card-glow" style="background: #10b981"></div>
      </div>

      <div class="stat-card">
        <div class="stat-card-inner">
          <div class="stat-icon-wrapper" style="--icon-color: #f59e0b">
            <el-icon size="24"><Star /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">公司平均总分</div>
            <div class="stat-value" style="color: #f59e0b">{{ stats.avg_total_score }}</div>
          </div>
        </div>
        <div class="stat-card-glow" style="background: #f59e0b"></div>
      </div>

      <div class="stat-card highlight">
        <div class="stat-card-inner">
          <div class="stat-icon-wrapper" style="--icon-color: #ef4444">
            <el-icon size="24"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">待审批数</div>
            <div class="stat-value" style="color: #ef4444">{{ stats.pending_approvals }}</div>
          </div>
        </div>
        <div class="stat-card-glow" style="background: #ef4444"></div>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="charts-grid">
      <div class="chart-card">
        <div class="card-header-custom">
          <div class="card-header-icon">
            <el-icon size="18"><PieChart /></el-icon>
          </div>
          <span class="card-header-title">绩效分布</span>
        </div>
        <div ref="pieChartRef" class="chart-container" />
      </div>

      <div class="chart-card">
        <div class="card-header-custom">
          <div class="card-header-icon">
            <el-icon size="18"><Histogram /></el-icon>
          </div>
          <span class="card-header-title">部门平均分对比</span>
        </div>
        <div ref="barChartRef" class="chart-container" />
      </div>
    </div>

    <!-- 趋势折线图 -->
    <div class="dashboard-card">
      <div class="card-header-custom">
        <div class="card-header-icon">
          <el-icon size="18"><TrendCharts /></el-icon>
        </div>
        <span class="card-header-title">近 4 季度绩效趋势</span>
      </div>
      <div ref="lineChartRef" class="chart-container" />
    </div>

    <!-- 强制调整人员列表 -->
    <div class="dashboard-card">
      <div class="card-header-custom">
        <div class="card-header-icon">
          <el-icon size="18"><Warning /></el-icon>
        </div>
        <span class="card-header-title">强制调整人员列表</span>
      </div>
      <el-table :data="adjustedEmployees" style="width: 100%" class="custom-table">
        <el-table-column prop="employee_name" label="姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="original_grade" label="原等级" width="100">
          <template #default="{ row }">
            <el-tag :type="gradeTagType(row.original_grade)" size="small" class="grade-tag">{{ row.original_grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="adjusted_grade" label="调整后等级" width="120">
          <template #default="{ row }">
            <el-tag type="danger" size="small" class="grade-tag">{{ row.adjusted_grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="override_reason" label="调整原因" show-overflow-tooltip />
      </el-table>
      <el-empty v-if="adjustedEmployees.length === 0" description="暂无强制调整记录" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { User, TrendCharts, Star, Warning, Filter, PieChart, Histogram } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import request from '@/api/request'
import { listDepartments } from '@/api/departments'

const loading = ref(false)
const stats = ref({
  total_employees: 0,
  coverage_rate: 0,
  avg_total_score: 0,
  pending_approvals: 0,
})
const gradeDistribution = ref({ A: 0, B: 0, C: 0, D: 0 })
const departmentAvg = ref([])
const quarterlyTrend = ref([])
const adjustedEmployees = ref([])
const departments = ref([])
const selectedDept = ref(null)

const pieChartRef = ref(null)
const barChartRef = ref(null)
const lineChartRef = ref(null)
let pieChart = null
let barChart = null
let lineChart = null

// Chart color palette matching the design system
const CHART_COLORS = {
  primary: '#6366f1',
  success: '#10b981',
  accent: '#f59e0b',
  danger: '#ef4444',
  info: '#3b82f6',
  purple: '#8b5cf6',
  teal: '#14b8a6',
}

async function loadData() {
  loading.value = true
  try {
    const res = await request.get('/dashboard/executive')
    if (res) {
      stats.value = res.stats || stats.value
      gradeDistribution.value = res.grade_distribution || gradeDistribution.value
      departmentAvg.value = res.department_avg || []
      quarterlyTrend.value = res.quarterly_trend || []
      adjustedEmployees.value = res.adjusted_employees || []
    }

    const deptRes = await listDepartments()
    departments.value = deptRes?.items || []
  } catch (e) {
    console.error(e)
    ElMessage.error('加载仪表盘数据失败')
  } finally {
    loading.value = false
  }
}

function initCharts() {
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value)
    updatePieChart()
  }
  if (barChartRef.value) {
    barChart = echarts.init(barChartRef.value)
    updateBarChart()
  }
  if (lineChartRef.value) {
    lineChart = echarts.init(lineChartRef.value)
    updateLineChart()
  }
}

function updatePieChart() {
  if (!pieChart) return
  const data = gradeDistribution.value
  pieChart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e2e8f0', textStyle: { color: '#1e293b' } },
    legend: { bottom: '5%', left: 'center', textStyle: { color: '#64748b', fontWeight: 500 } },
    series: [{
      name: '绩效分布',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 3 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold', color: '#1e293b' } },
      data: [
        { value: data.A, name: 'A', itemStyle: { color: CHART_COLORS.success } },
        { value: data.B, name: 'B', itemStyle: { color: CHART_COLORS.primary } },
        { value: data.C, name: 'C', itemStyle: { color: CHART_COLORS.accent } },
        { value: data.D, name: 'D', itemStyle: { color: CHART_COLORS.danger } },
      ],
    }],
  })
}

function updateBarChart() {
  if (!barChart) return
  const filtered = selectedDept.value
    ? departmentAvg.value.filter(d => d.id === selectedDept.value)
    : departmentAvg.value
  barChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e2e8f0', textStyle: { color: '#1e293b' } },
    xAxis: { type: 'category', data: filtered.map(d => d.name), axisLabel: { rotate: 30, color: '#64748b', fontWeight: 500 }, axisLine: { lineStyle: { color: '#e2e8f0' } } },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [{
      data: filtered.map(d => d.avg_score),
      type: 'bar',
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#6366f1' }, { offset: 1, color: '#4f46e5' }]), borderRadius: [6, 6, 0, 0] },
      label: { show: true, position: 'top', color: '#64748b', fontWeight: 600 },
      barWidth: '40%',
    }],
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  })
}

function updateLineChart() {
  if (!lineChart) return
  lineChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e2e8f0', textStyle: { color: '#1e293b' } },
    xAxis: { type: 'category', data: quarterlyTrend.value.map(t => t.cycle_name), axisLabel: { color: '#64748b', fontWeight: 500 }, axisLine: { lineStyle: { color: '#e2e8f0' } } },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [{
      data: quarterlyTrend.value.map(t => t.avg_score),
      type: 'line',
      smooth: true,
      symbolSize: 8,
      itemStyle: { color: CHART_COLORS.primary, borderWidth: 2, borderColor: '#fff' },
      lineStyle: { width: 3, color: CHART_COLORS.primary },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(99, 102, 241, 0.2)' }, { offset: 1, color: 'rgba(99, 102, 241, 0.02)' }]) },
      label: { show: true, color: '#64748b', fontWeight: 600 },
    }],
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  })
}

function onDeptChange() {
  updateBarChart()
}

function gradeTagType(grade) {
  const map = { A: 'success', B: 'primary', C: 'warning', D: 'danger' }
  return map[grade] || 'info'
}

onMounted(async () => {
  await loadData()
  await nextTick()
  initCharts()
})

watch([gradeDistribution, departmentAvg, quarterlyTrend], () => {
  nextTick(() => {
    updatePieChart()
    updateBarChart()
    updateLineChart()
  })
})
</script>

<style scoped>
.executive-dashboard {
  padding: 0;
}

/* Stats grid (same as DashboardView) */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  position: relative;
  cursor: default;
  transition: all var(--transition-base);
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  overflow: hidden;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
}

.stat-card.highlight {
  border-color: rgba(239, 68, 68, 0.2);
  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.08);
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

/* Dashboard Card */
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

.filter-card {
  margin-bottom: 24px;
}

.filter-select {
  min-width: 200px;
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

/* Charts Grid */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  padding: 24px;
  transition: all var(--transition-base);
}

.chart-card:hover {
  box-shadow: var(--shadow-md);
}

.chart-container {
  height: 300px;
  width: 100%;
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

.grade-tag {
  border-radius: 6px;
  font-weight: 600;
  font-size: 12px;
  padding: 0 10px;
  height: 26px;
  line-height: 24px;
  letter-spacing: 0.3px;
}

/* Mobile */
@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
