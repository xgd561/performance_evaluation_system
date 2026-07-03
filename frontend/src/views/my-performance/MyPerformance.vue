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
        <div v-else-if="currentRecord.self_scores && Object.keys(currentRecord.self_scores).length > 0" class="self-scores-display">
          <el-divider />
          <h4>已提交的自评分数</h4>
          <div class="score-tags">
            <el-tag size="large" type="primary">业绩 {{ currentRecord.self_scores.performance ?? '-' }} 分</el-tag>
            <el-tag size="large" type="success">能力 {{ currentRecord.self_scores.ability ?? '-' }} 分</el-tag>
            <el-tag size="large" type="warning">态度 {{ currentRecord.self_scores.attitude ?? '-' }} 分</el-tag>
          </div>
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
          <el-table-column prop="total_score" label="总分">
            <template #default="{ row }">
              <span v-if="row.status === 'published' || row.status === 'archived'">{{ row.total_score }}</span>
              <span v-else class="empty">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="grade" label="等级">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'published' || row.status === 'archived'" :type="gradeTagType(row.grade)" size="small">{{ row.grade }}</el-tag>
              <span v-else class="empty">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              {{ statusText(row.status) }}
            </template>
          </el-table-column>
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-button v-if="row.status === 'published' || row.status === 'archived'" link type="primary" @click="viewDetail(row)">查看详情</el-button>
              <span v-else class="empty">待发布</span>
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

      <!-- 详情抽屉 -->
      <el-drawer
        v-model="detailDrawerVisible"
        :title="detailTitle"
        size="60%"
        :with-header="true"
        destroy-on-close
      >
        <div v-if="detailLoading" class="loading-wrap">
          <el-skeleton :rows="8" animated />
        </div>
        <div v-else-if="detailRecord" class="detail-content">
          <!-- 基本信息 -->
          <el-descriptions :column="2" border>
            <el-descriptions-item label="考核周期">{{ detailRecord.cycle_name }}</el-descriptions-item>
            <el-descriptions-item label="考核状态">
              <el-tag :type="statusTagType(detailRecord.status)" size="small">{{ statusText(detailRecord.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="总分">{{ detailRecord.total_score || '-' }}</el-descriptions-item>
            <el-descriptions-item label="等级">
              <el-tag :type="gradeTagType(detailRecord.grade)" size="small">{{ detailRecord.grade || '-' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="部门">{{ detailRecord.department_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="岗位">{{ detailRecord.position_name || '-' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 三维评分对比 -->
          <div class="section-title">三维评分对比</div>
          <el-table :data="dimensionCompareData" border style="width: 100%">
            <el-table-column prop="dimension" label="维度" />
            <el-table-column prop="self" label="自评" />
            <el-table-column prop="manager" label="上级评" />
            <el-table-column prop="peer" label="协作评" />
            <el-table-column prop="weighted" label="加权得分" />
          </el-table>

          <!-- KPI 评分明细 -->
          <div v-if="detailRecord.kpi_details?.length" class="section-title">KPI 评分明细</div>
          <el-table v-if="detailRecord.kpi_details?.length" :data="detailRecord.kpi_details" border style="width: 100%">
            <el-table-column prop="kpi_name" label="KPI 名称" />
            <el-table-column prop="weight" label="权重" />
            <el-table-column prop="target_value" label="目标值" />
            <el-table-column prop="self_score" label="自评得分" />
            <el-table-column prop="manager_score" label="上级评分" />
          </el-table>

          <!-- 上级评语 -->
          <div v-if="detailRecord.manager_comment" class="section-title">上级评语</div>
          <el-card v-if="detailRecord.manager_comment" shadow="never" class="comment-card">
            {{ detailRecord.manager_comment }}
          </el-card>

          <!-- 申诉记录 -->
          <div v-if="detailRecord.appeal" class="section-title">申诉记录</div>
          <el-descriptions v-if="detailRecord.appeal" :column="1" border>
            <el-descriptions-item label="申诉原因">{{ detailRecord.appeal.reason }}</el-descriptions-item>
            <el-descriptions-item label="申诉详情">{{ detailRecord.appeal.detail || '-' }}</el-descriptions-item>
            <el-descriptions-item label="申诉状态">
              <el-tag :type="appealStatusTag(detailRecord.appeal.status)" size="small">{{ appealStatusText(detailRecord.appeal.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="detailRecord.appeal.review_result" label="处理结果">{{ detailRecord.appeal.review_result }}</el-descriptions-item>
            <el-descriptions-item v-if="detailRecord.appeal.reviewer_name" label="处理人">{{ detailRecord.appeal.reviewer_name }}</el-descriptions-item>
          </el-descriptions>

          <!-- 面谈记录 -->
          <div v-if="detailRecord.interview" class="section-title">面谈记录</div>
          <el-descriptions v-if="detailRecord.interview" :column="1" border>
            <el-descriptions-item label="面谈时间">{{ detailRecord.interview.interview_time || '-' }}</el-descriptions-item>
            <el-descriptions-item label="面谈地点">{{ detailRecord.interview.location || '-' }}</el-descriptions-item>
            <el-descriptions-item label="面谈人">{{ detailRecord.interview.interviewer_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="面谈内容">{{ detailRecord.interview.content || '-' }}</el-descriptions-item>
            <el-descriptions-item v-if="detailRecord.interview.improvement_plan" label="改进计划">{{ detailRecord.interview.improvement_plan }}</el-descriptions-item>
          </el-descriptions>

          <!-- 操作按钮 -->
          <div class="detail-actions">
            <el-button type="primary" @click="downloadPdf">下载 PDF 档案</el-button>
          </div>
        </div>
      </el-drawer>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getMyAssessment, getAssessmentDetail, downloadRecordPdf } from '@/api/scores'
import { getEmployeeTrend } from '@/api/reports'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const records = ref([])
const currentRecord = ref(null)
const chartRef = ref(null)

const detailDrawerVisible = ref(false)
const detailLoading = ref(false)
const detailRecord = ref(null)
const detailRecordId = ref(null)

const detailTitle = computed(() => {
  return detailRecord.value ? `${detailRecord.value.cycle_name} - 考核详情` : '考核详情'
})

const dimensionCompareData = computed(() => {
  if (!detailRecord.value) return []
  const dims = [
    { key: 'performance', label: '业绩' },
    { key: 'ability', label: '能力' },
    { key: 'attitude', label: '态度' },
  ]
  const map = {
    performance: 'weighted_performance',
    ability: 'weighted_ability',
    attitude: 'weighted_attitude',
  }
  return dims.map(d => ({
    dimension: d.label,
    self: detailRecord.value.self_scores?.[d.key] ?? '-',
    manager: detailRecord.value.manager_scores?.[d.key] ?? '-',
    peer: detailRecord.value.peer_scores?.[d.key] ?? '-',
    weighted: detailRecord.value[map[d.key]] ?? '-',
  }))
})

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
  detailRecordId.value = row.record_id
  detailDrawerVisible.value = true
  loadDetail()
}

async function loadDetail() {
  if (!detailRecordId.value) return
  detailLoading.value = true
  try {
    const res = await getAssessmentDetail(detailRecordId.value)
    detailRecord.value = res
  } catch (e) {
    console.error(e)
    ElMessage.error('加载详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function downloadPdf() {
  if (!detailRecordId.value) return
  try {
    const res = await downloadRecordPdf(detailRecordId.value)
    const blob = new Blob([res], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `performance_${detailRecordId.value}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    ElMessage.error('PDF 下载失败')
  }
}

function appealStatusTag(status) {
  const map = { pending: 'warning', approved: 'success', rejected: 'danger' }
  return map[status] || 'info'
}

function appealStatusText(status) {
  const map = { pending: '待处理', approved: '已通过', rejected: '已驳回' }
  return map[status] || status
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

.detail-content {
  padding: 0 8px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 20px 0 12px;
  color: #303133;
}

.comment-card {
  background: #f5f7fa;
  color: #606266;
  line-height: 1.6;
}

.detail-actions {
  margin-top: 24px;
  text-align: center;
}

.status-actions {
  margin-top: 16px;
  text-align: center;
}

.self-scores-display {
  margin-top: 16px;
}

.self-scores-display h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #303133;
}

.score-tags {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}
</style>
