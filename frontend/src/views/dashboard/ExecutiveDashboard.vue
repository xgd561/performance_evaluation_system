
<template>
  <div class="executive-dashboard">
    <!-- 部门筛选 -->
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true">
        <el-form-item label="部门筛选">
          <el-select v-model="selectedDept" placeholder="全部部门" clearable @change="onDeptChange">
            <el-option v-for="dept in departments" :key="dept.id" :label="dept.name" :value="dept.id" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="color: #409eff;">
            <el-icon size="32"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">员工总数</div>
            <div class="stat-value" style="color: #409eff;">{{ stats.total_employees }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="color: #67c23a;">
            <el-icon size="32"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">考核覆盖率</div>
            <div class="stat-value" style="color: #67c23a;">{{ stats.coverage_rate }}%</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="color: #e6a23c;">
            <el-icon size="32"><Star /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">公司平均总分</div>
            <div class="stat-value" style="color: #e6a23c;">{{ stats.avg_total_score }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="color: #f56c6c;">
            <el-icon size="32"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">待审批数</div>
            <div class="stat-value" style="color: #f56c6c;">{{ stats.pending_approvals }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="20" class="charts-row">
      <!-- 绩效分布饼图 -->
      <el-col :xs="24" :md="12">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-title">绩效分布</div>
          </template>
          <div ref="pieChartRef" class="chart-container" />
        </el-card>
      </el-col>

      <!-- 部门平均分对比柱状图 -->
      <el-col :xs="24" :md="12">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-title">部门平均分对比</div>
          </template>
          <div ref="barChartRef" class="chart-container" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势折线图 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :xs="24">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-title">近 4 季度绩效趋势</div>
          </template>
          <div ref="lineChartRef" class="chart-container" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 强制调整人员列表 -->
    <el-card class="mt-20" shadow="hover">
      <template #header>
        <div class="card-title">强制调整人员列表</div>
      </template>
      <el-table :data="adjustedEmployees" style="width: 100%">
        <el-table-column prop="employee_name" label="姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="original_grade" label="原等级" width="100">
          <template #default="{ row }">
            <el-tag :type="gradeTagType(row.original_grade)" size="small">{{ row.original_grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="adjusted_grade" label="调整后等级" width="120">
          <template #default="{ row }">
            <el-tag type="danger" size="small">{{ row.adjusted_grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="override_reason" label="调整原因" show-overflow-tooltip />
      </el-table>
      <el-empty v-if="adjustedEmployees.length === 0" description="暂无强制调整记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { User, TrendCharts, Star, Warning } from '@element-plus/icons-vue'
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
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%', left: 'center' },
    series: [{
      name: '绩效分布',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
      data: [
        { value: data.A, name: 'A', itemStyle: { color: '#67c23a' } },
        { value: data.B, name: 'B', itemStyle: { color: '#409eff' } },
        { value: data.C, name: 'C', itemStyle: { color: '#e6a23c' } },
        { value: data.D, name: 'D', itemStyle: { color: '#f56c6c' } },
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
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: filtered.map(d => d.name), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      data: filtered.map(d => d.avg_score),
      type: 'bar',
      itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top' },
    }],
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  })
}

function updateLineChart() {
  if (!lineChart) return
  lineChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: quarterlyTrend.value.map(t => t.cycle_name) },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      data: quarterlyTrend.value.map(t => t.avg_score),
      type: 'line',
      smooth: true,
      itemStyle: { color: '#67c23a' },
      areaStyle: { color: 'rgba(103, 194, 58, 0.2)' },
      label: { show: true },
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
.filter-card {
  margin-bottom: 20px;
}
.stats-row {
  margin-bottom: 20px;
}
.stat-card {
  display: flex;
  align-items: center;
  padding: 16px;
  cursor: default;
}
.stat-icon {
  margin-right: 16px;
}
.stat-info {
  flex: 1;
}
.stat-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
}
.charts-row {
  margin-bottom: 20px;
}
.chart-card {
  margin-bottom: 20px;
}
.chart-container {
  height: 300px;
  width: 100%;
}
.card-title {
  font-weight: bold;
  font-size: 16px;
}
.mt-20 {
  margin-top: 20px;
}
</style>
