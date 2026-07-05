<template>
  <PageContainer title="自评">
    <div class="score-sheet-layout">
      <!-- 左侧：考核信息 -->
      <div class="info-panel">
        <div class="panel-card">
          <h3>考核信息</h3>
          <div class="info-row">
            <span class="info-label">考核周期</span>
            <span class="info-value">{{ assessmentInfo.cycleName }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">截止日期</span>
            <span class="info-value countdown" :class="{ urgent: countdownDays <= 3 }">
              {{ countdownText }}
            </span>
          </div>
          <el-divider />
          <div class="dimension-desc">
            <h4>评分维度说明</h4>
            <p v-for="dim in dimensions" :key="dim.key">
              <strong>{{ dim.label }}（{{ dim.weight }}%）：</strong>{{ dim.desc }}
            </p>
          </div>
        </div>
      </div>

      <!-- 右侧：评分区域 -->
      <div class="score-area">
        <!-- 已提交自评展示 -->
        <div v-if="hasSubmitted" class="submitted-section">
          <el-result icon="success" title="自评已提交" sub-title="您已完成当前考核周期的自评">
            <template #extra>
              <el-button type="primary" @click="goToMyPerformance">查看我的绩效</el-button>
            </template>
          </el-result>

          <div class="submitted-scores">
            <h4>已提交的自评分数</h4>
            <div class="dimension-list">
              <div
                v-for="dim in dimensions"
                :key="dim.key"
                class="dimension-item submitted"
              >
                <div class="dim-header">
                  <span class="dim-name">{{ dim.label }}</span>
                  <span class="dim-weight">权重 {{ dim.weight }}%</span>
                </div>
                <div class="score-display">
                  <span class="score-value">{{ submittedScores[dim.key] ?? '-' }}</span>
                  <span class="score-unit">分</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 自评表单 -->
        <el-form v-else ref="scoreFormRef" :model="scoreForm" label-position="top">
          <div class="dimension-section">
            <h4>维度自评</h4>
            <div class="dimension-list">
              <div
                v-for="dim in dimensions"
                :key="dim.key"
                class="dimension-item"
                :class="{ 'has-error': dimensionErrors[dim.key] }"
              >
                <div class="dim-header">
                  <span class="dim-name">{{ dim.label }}</span>
                  <span class="dim-weight">权重 {{ dim.weight }}%</span>
                  <el-tooltip placement="top">
                    <template #content>
                      <div class="anchor-tooltip">
                        <p v-for="anchor in SCORE_ANCHORS" :key="anchor.range">
                          <strong>{{ anchor.range }} 分 = {{ anchor.label }}</strong><br/>
                          {{ anchor.desc }}
                        </p>
                      </div>
                    </template>
                    <el-icon class="anchor-icon"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <el-input-number
                  v-model="scoreForm.dimensionScores[dim.key]"
                  :min="0"
                  :max="100"
                  :precision="1"
                  :step="1"
                  placeholder="0-100"
                  class="score-input"
                  @change="(val) => handleDimensionScoreChange(dim.key, val)"
                />
                <span v-if="dimensionErrors[dim.key]" class="error-msg">
                  {{ dimensionErrors[dim.key] }}
                </span>
              </div>
            </div>
          </div>

          <!-- KPI 评分 -->
          <div v-if="kpiItems.length > 0" class="kpi-section">
            <h4>KPI 评分</h4>
            <div class="kpi-list">
              <div
                v-for="(kpi, index) in kpiItems"
                :key="index"
                class="kpi-item"
              >
                <div class="kpi-header">
                  <span class="kpi-name">{{ kpi.name }}</span>
                  <span class="kpi-weight">权重 {{ kpi.weight }}%</span>
                  <span class="kpi-target">目标: {{ kpi.target }}</span>
                </div>
                <el-input-number
                  v-model="kpiScores[index]"
                  :min="0"
                  :max="100"
                  :precision="1"
                  :step="1"
                  placeholder="0-100"
                  class="score-input"
                />
              </div>
            </div>
          </div>

          <div class="submit-section">
            <el-button
              type="primary"
              size="large"
              :disabled="!canSubmit"
              :loading="submitting"
              @click="handleSubmit"
            >
              提交自评
            </el-button>
            <el-button size="large" :loading="savingDraft" @click="handleSaveDraft">保存草稿</el-button>
            <el-button size="large" @click="handleCancel">返回</el-button>
          </div>
        </el-form>
      </div>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMyAssessment, getSelfAssessmentData, submitSelfScore, createScoreDraft } from '@/api/scores'
import { SCORE_ANCHORS, DIMENSION_TEXT } from '@/utils/constants'

const router = useRouter()

const assessmentInfo = reactive({
  cycleName: '-',
  deadline: null,
  recordId: null,
})

const hasSubmitted = ref(false)
const submittedScores = reactive({
  performance: null,
  ability: null,
  attitude: null,
})

const dimensionWeights = ref({})
const reviewerWeights = ref({})
const kpiItems = ref([])
const kpiScores = ref([])

const countdownDays = computed(() => {
  if (!assessmentInfo.deadline) return 1
  const diff = new Date(assessmentInfo.deadline) - Date.now()
  return Math.ceil(diff / (24 * 60 * 60 * 1000))
})
const countdownText = computed(() => {
  if (!assessmentInfo.deadline) return '-'
  const dateStr = assessmentInfo.deadline.substring(0, 10)
  if (countdownDays.value <= 0) return `${dateStr}（已截止）`
  return `${dateStr}（还剩 ${countdownDays.value} 天）`
})

const dimensions = computed(() => {
  const dw = dimensionWeights.value || {}
  const list = []
  const weightFn = (v) => {
    if (v === undefined || v === null) return 0
    return v <= 1 ? Math.round(v * 100) : v
  }
  const descMap = {
    performance: 'KPI 完成情况，如销售额、项目交付等',
    ability: '专业技能、沟通协作、学习能力',
    attitude: '责任心、主动性、团队精神',
  }
  if (dw.performance !== undefined) {
    list.push({ key: 'performance', label: DIMENSION_TEXT.performance, weight: weightFn(dw.performance), desc: descMap.performance })
  }
  if (dw.ability !== undefined) {
    list.push({ key: 'ability', label: DIMENSION_TEXT.ability, weight: weightFn(dw.ability), desc: descMap.ability })
  }
  if (dw.attitude !== undefined) {
    list.push({ key: 'attitude', label: DIMENSION_TEXT.attitude, weight: weightFn(dw.attitude), desc: descMap.attitude })
  }
  return list
})

const scoreForm = reactive({
  dimensionScores: {
    performance: null,
    ability: null,
    attitude: null
  }
})

const scoreFormRef = ref(null)
const submitting = ref(false)
const savingDraft = ref(false)
const dimensionErrors = reactive({ performance: '', ability: '', attitude: '' })

const canSubmit = computed(() => {
  const dimsValid = Object.values(scoreForm.dimensionScores).every(
    s => s !== null && s !== undefined && s >= 0 && s <= 100
  )
  const kpiValid = kpiScores.value.every(
    s => s !== null && s !== undefined && s >= 0 && s <= 100
  )
  return dimsValid && (kpiItems.value.length === 0 || kpiValid)
})

onMounted(async () => {
  try {
    const res = await getMyAssessment()
    const items = res?.items || []
    // 优先查找待自评记录
    const pendingItem = items.find(i => i.status === 'pending_self')
    if (pendingItem) {
      assessmentInfo.cycleName = pendingItem.cycle_name
      assessmentInfo.deadline = pendingItem.self_due_date
      assessmentInfo.recordId = pendingItem.record_id
      hasSubmitted.value = false

      // 加载自评详情（含 KPI、维度权重、草稿）
      try {
        const detail = await getSelfAssessmentData(pendingItem.record_id)
        dimensionWeights.value = detail.dimension_weights || {}
        reviewerWeights.value = detail.reviewer_weights || {}
        kpiItems.value = detail.kpi_items || []
        kpiScores.value = detail.kpi_scores?.map(s => s.self_score ? parseFloat(s.self_score) : null) || new Array(kpiItems.value.length).fill(null)

        // 加载已有自评分数（如存在）
        if (detail.self_scores && Object.keys(detail.self_scores).length > 0) {
          scoreForm.dimensionScores.performance = detail.self_scores.performance ?? null
          scoreForm.dimensionScores.ability = detail.self_scores.ability ?? null
          scoreForm.dimensionScores.attitude = detail.self_scores.attitude ?? null
        }

        // 加载草稿
        if (detail.draft) {
          if (detail.draft.performance !== undefined && detail.draft.performance !== null) {
            scoreForm.dimensionScores.performance = detail.draft.performance
          }
          if (detail.draft.ability !== undefined && detail.draft.ability !== null) {
            scoreForm.dimensionScores.ability = detail.draft.ability
          }
          if (detail.draft.attitude !== undefined && detail.draft.attitude !== null) {
            scoreForm.dimensionScores.attitude = detail.draft.attitude
          }
          if (detail.draft.kpi_scores && Array.isArray(detail.draft.kpi_scores)) {
            kpiScores.value = detail.draft.kpi_scores.map(s => s !== null && s !== undefined ? parseFloat(s) : null)
          }
          ElMessage.info('已自动恢复上次保存的草稿')
        }
      } catch (e) {
        console.warn('加载自评详情失败:', e)
      }
    } else {
      // 查找已提交自评的记录
      const submittedItem = items.find(i => i.status !== 'pending_self' && i.self_scores && Object.keys(i.self_scores).length > 0)
      if (submittedItem) {
        assessmentInfo.cycleName = submittedItem.cycle_name
        assessmentInfo.deadline = submittedItem.self_due_date
        assessmentInfo.recordId = submittedItem.record_id
        hasSubmitted.value = true
        submittedScores.performance = submittedItem.self_scores?.performance ?? null
        submittedScores.ability = submittedItem.self_scores?.ability ?? null
        submittedScores.attitude = submittedItem.self_scores?.attitude ?? null
      } else {
        ElMessage.info('当前没有待自评的考核')
      }
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载考核数据失败')
  }
})

function handleDimensionScoreChange(dimKey, val) {
  dimensionErrors[dimKey] = ''
  if (val === null || val === undefined) return
  if (val < 0 || val > 100) {
    dimensionErrors[dimKey] = '分数需在 0-100 之间'
  }
}

async function handleSubmit() {
  if (!assessmentInfo.recordId) {
    ElMessage.warning('没有可提交的考核记录')
    return
  }

  for (const dim of dimensions.value) {
    const score = scoreForm.dimensionScores[dim.key]
    if (score === null || score === undefined || score < 0 || score > 100) {
      dimensionErrors[dim.key] = '请填写 0-100 之间的分数'
      return
    }
  }

  for (let i = 0; i < kpiItems.value.length; i++) {
    const score = kpiScores.value[i]
    if (score === null || score === undefined || score < 0 || score > 100) {
      ElMessage.warning(`请为 KPI「${kpiItems.value[i].name}」填写 0-100 之间的分数`)
      return
    }
  }

  try {
    await ElMessageBox.confirm('确认提交自评？提交后不可修改', '确认', { type: 'warning' })
  } catch {
    return
  }

  submitting.value = true
  try {
    await submitSelfScore(assessmentInfo.recordId, {
      performance: scoreForm.dimensionScores.performance,
      ability: scoreForm.dimensionScores.ability,
      attitude: scoreForm.dimensionScores.attitude,
      kpi_scores: kpiScores.value,
    })
    ElMessage.success('自评提交成功')
    router.push('/my-performance')
  } catch (error) {
    console.error('Submit failed:', error)
    ElMessage.error(error?.response?.data?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  router.push('/my-performance')
}

function goToMyPerformance() {
  router.push('/my-performance')
}

async function handleSaveDraft() {
  if (!assessmentInfo.recordId) {
    ElMessage.warning('没有可保存的考核记录')
    return
  }
  savingDraft.value = true
  try {
    await createScoreDraft({
      record_id: assessmentInfo.recordId,
      draft_type: 'self',
      draft_data: {
        performance: scoreForm.dimensionScores.performance,
        ability: scoreForm.dimensionScores.ability,
        attitude: scoreForm.dimensionScores.attitude,
        kpi_scores: kpiScores.value,
      },
    })
    ElMessage.success('草稿保存成功')
  } catch (error) {
    console.error('Save draft failed:', error)
    ElMessage.error(error?.response?.data?.message || '草稿保存失败')
  } finally {
    savingDraft.value = false
  }
}
</script>

<style scoped>
.score-sheet-layout {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 200px);
}

.info-panel {
  width: 280px;
  flex-shrink: 0;
}

.panel-card {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 20px;
}

.panel-card h3 {
  margin: 0 0 16px;
  font-size: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 14px;
}

.info-label {
  color: #606266;
}

.info-value {
  color: #303133;
  font-weight: 500;
}

.countdown {
  color: #67c23a;
}

.countdown.urgent {
  color: #f56c6c;
}

.dimension-desc h4 {
  margin: 0 0 12px;
  font-size: 14px;
}

.dimension-desc p {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  line-height: 1.5;
}

.score-area {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.dimension-section h4,
.kpi-section h4 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #303133;
}

.dimension-list {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
}

.dimension-item {
  flex: 1;
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  transition: border-color 0.2s;
}

.dimension-item.has-error {
  border-color: #f56c6c;
}

.dim-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.dim-name {
  font-weight: 600;
  color: #303133;
}

.dim-weight {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

.anchor-icon {
  color: #909399;
  cursor: pointer;
}

.anchor-icon:hover {
  color: #409eff;
}

.score-input {
  width: 100%;
}

.anchor-tooltip p {
  margin: 4px 0;
  font-size: 13px;
}

.submit-section {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding-top: 24px;
  border-top: 1px solid #e4e7ed;
}

.error-msg {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
}

.submitted-section {
  padding: 24px;
}

.submitted-scores {
  margin-top: 24px;
}

.submitted-scores h4 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #303133;
}

.dimension-item.submitted {
  background: #f0f9ff;
  border-color: #409eff;
}

.score-display {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 8px;
}

.score-value {
  font-size: 28px;
  font-weight: 700;
  color: #409eff;
}

.score-unit {
  font-size: 14px;
  color: #606266;
}

.kpi-section {
  margin-bottom: 24px;
}

.kpi-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.kpi-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.kpi-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.kpi-name {
  font-weight: 600;
  color: #303133;
}

.kpi-weight {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

.kpi-target {
  font-size: 12px;
  color: #606266;
}

@media (max-width: 1024px) {
  .score-sheet-layout {
    flex-direction: column;
  }

  .info-panel {
    width: 100%;
  }

  .panel-card {
    position: static;
  }

  .dimension-list {
    flex-direction: column;
  }
}
</style>
