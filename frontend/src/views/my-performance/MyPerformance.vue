<template>
  <PageContainer title="我的绩效">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else>
      <!-- 当前考核状态 -->
      <el-card class="status-card" v-if="currentRecord">
        <div class="status-header">
          <div>
            <h3>{{ currentRecord.cycle_name }}</h3>
            <p class="status-desc">当前考核状态</p>
          </div>
          <el-tag :type="statusTagType(currentRecord.status)" size="large">
            {{ statusText(currentRecord.status) }}
          </el-tag>
        </div>
        <el-progress
          :percentage="progressPercent(currentRecord.status)"
          :status="progressStatus(currentRecord.status)"
          class="progress-bar"
        />
        <div class="status-steps">
          <div
            v-for="(step, idx) in steps"
            :key="step.key"
            class="step-item"
            :class="{ active: stepActive(idx, currentRecord.status), current: stepCurrent(idx, currentRecord.status) }"
          >
            <div class="step-dot" />
            <div class="step-label">{{ step.label }}</div>
          </div>
        </div>
        <div class="status-actions" v-if="currentRecord.status === 'pending_self'">
          <el-button type="primary" @click="goSelfAssessment">进入自评</el-button>
        </div>
      </el-card>

      <!-- 历史趋势图 -->
      <el-card class="mt-20">
        <div class="card-title">历史绩效趋势</div>
        <div ref="chartRef" class="chart-wrap" />
      </el-card>

      <!-- 历史考核记录 -->
      <el-card class="mt-20">
        <div class="card-title">历史考核记录</div>
        <el-table :data="records" style="width: 100%">
          <el-table-column prop="cycle_name" label="考核周期" />
          <el-table-column prop="total_score" label="总分" />
          <el-table-column prop="grade" label="等级">
            <template #default="{ row }">
              <el-tag :type="gradeTagType(row.grade)" size="small">{{ row.grade }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              {{ statusText(row.status) }}
            </template>
          </el-table-column>
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewDetail(row)">查看详情</el-button>
              <el-button
                v-if="row.status === 'published' && !row.hasAppeal"
                link
                type="warning"
                @click="goAppeal(row)"
              >
                发起申诉
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getMyAssessment } from '@/api/scores'
import { getEmployeeTrend } from '@/api/reports'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const records = ref([])
const currentRecord = ref(null)
const chartRef = ref(null)

const employeeId = computed(() => authStore.user?.employee_id)

const steps = [
  { key: 'pending_self', label: '自评' },
  { key: 'pending_manager', label: '上级评' },
  { key: 'pending_peer', label: '协作评' },
  { key: 'pending_summary', label: '汇总' },
  { key: 'pending_approval', label: '审批' },
  { key: 'published', label: '已发布' },
]

onMounted(async () => {
  loading.value = true
  try {
    const res = await getMyAssessment()
    records.value = res?.items || []
    if (records.value.length > 0) {
      currentRecord.value = records.value[0]
    }

    const trendRes = await getEmployeeTrend(employeeId.value)
    nextTick(() => {
      renderChart(trendRes?.items || [])
    })
  } catch (e) {
    console.error(e)
    ElMessage.error('加载绩效数据失败')
  } finally {
    loading.value = false
  }
})

function renderChart(items) {
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)
  const xData = items.map(i => i.cycle_name)
  const totalData = items.map(i => i.total_score || 0)
  const perfData = items.map(i => i.weighted_performance || 0)
  const abilityData = items.map(i => i.weighted_ability || 0)
  const attitudeData = items.map(i => i.weighted_attitude || 0)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['总分', '业绩', '能力', '态度'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: xData },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [
      { name: '总分', type: 'line', data: totalData, smooth: true },
      { name: '业绩', type: 'line', data: perfData, smooth: true },
      { name: '能力', type: 'line', data: abilityData, smooth: true },
      { name: '态度', type: 'line', data: attitudeData, smooth: true },
    ],
  })
}

function statusTagType(status) {
  const map = {
    pending_self: 'warning',
    pending_manager: 'primary',
    pending_peer: 'success',
    pending_summary: 'info',
    pending_approval: 'info',
    published: 'success',
  }
  return map[status] || 'info'
}

function statusText(status) {
  const map = {
    pending_self: '待自评',
    pending_manager: '待上级评',
    pending_peer: '待协作评',
    pending_summary: '汇总中',
    pending_approval: '审批中',
    published: '已发布',
  }
  return map[status] || status
}

function gradeTagType(grade) {
  const map = { A: 'success', B: 'primary', C: 'warning', D: 'danger' }
  return map[grade] || 'info'
}

function progressPercent(status) {
  const map = {
    pending_self: 16,
    pending_manager: 33,
    pending_peer: 50,
    pending_summary: 66,
    pending_approval: 83,
    published: 100,
  }
  return map[status] || 0
}

function progressStatus(status) {
  if (status === 'published') return 'success'
  return ''
}

function stepActive(idx, status) {
  const idxMap = {
    pending_self: 0,
    pending_manager: 1,
    pending_peer: 2,
    pending_summary: 3,
    pending_approval: 4,
    published: 5,
  }
  const currentIdx = idxMap[status] || 0
  return idx <= currentIdx
}

function stepCurrent(idx, status) {
  const idxMap = {
    pending_self: 0,
    pending_manager: 1,
    pending_peer: 2,
    pending_summary: 3,
    pending_approval: 4,
    published: 5,
  }
  return idx === (idxMap[status] || 0)
}

function goSelfAssessment() {
  router.push('/self-assessment')
}

function viewDetail(row) {
  ElMessage.info('查看详情功能开发中')
}

function goAppeal(row) {
  router.push({ path: '/appeal', query: { recordId: row.record_id } })
}
</script>

<style scoped>
.loading-wrap {
  padding: 40px;
}
.status-card {
  margin-bottom: 20px;
}
.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.status-header h3 {
  margin: 0 0 4px;
}
.status-desc {
  margin: 0;
  color: #909399;
  font-size: 13px;
}
.progress-bar {
  margin-bottom: 16px;
}
.status-steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
  position: relative;
}
.step-item::before {
  content: '';
  position: absolute;
  top: 6px;
  left: -50%;
  width: 100%;
  height: 2px;
  background: #e4e7ed;
  z-index: 0;
}
.step-item:first-child::before {
  display: none;
}
.step-item.active::before {
  background: #409eff;
}
.step-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #e4e7ed;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #e4e7ed;
  z-index: 1;
}
.step-item.active .step-dot {
  background: #409eff;
  box-shadow: 0 0 0 1px #409eff;
}
.step-item.current .step-dot {
  background: #67c23a;
  box-shadow: 0 0 0 1px #67c23a;
}
.step-label {
  font-size: 12px;
  color: #909399;
}
.step-item.active .step-label {
  color: #409eff;
  font-weight: 600;
}
.chart-wrap {
  width: 100%;
  height: 300px;
}
.mt-20 {
  margin-top: 20px;
}
.card-title {
  font-weight: bold;
  margin-bottom: 16px;
}
</style>
