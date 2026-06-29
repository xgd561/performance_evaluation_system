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
            <p><strong>工作业绩（60%）：</strong>KPI 完成情况，如销售额、项目交付等</p>
            <p><strong>工作能力（20%）：</strong>专业技能、沟通协作、学习能力</p>
            <p><strong>工作态度（20%）：</strong>责任心、主动性、团队精神</p>
          </div>
        </div>
      </div>

      <!-- 右侧：评分区域 -->
      <div class="score-area">
        <el-form ref="scoreFormRef" :model="scoreForm" label-position="top">
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
import { getMyAssessment, submitSelfScore } from '@/api/scores'
import { SCORE_ANCHORS, DIMENSION_TEXT } from '@/utils/constants'

const router = useRouter()

const assessmentInfo = reactive({
  cycleName: '-',
  deadline: null,
  recordId: null,
})

const countdownDays = computed(() => {
  if (!assessmentInfo.deadline) return 1
  const diff = new Date(assessmentInfo.deadline) - Date.now()
  return Math.ceil(diff / (24 * 60 * 60 * 1000))
})
const countdownText = computed(() => {
  if (!assessmentInfo.deadline) return '-'
  if (countdownDays.value <= 0) return '已截止'
  return `${countdownDays.value} 天`
})

const dimensions = [
  { key: 'performance', label: DIMENSION_TEXT.performance, weight: 60 },
  { key: 'ability', label: DIMENSION_TEXT.ability, weight: 20 },
  { key: 'attitude', label: DIMENSION_TEXT.attitude, weight: 20 }
]

const scoreForm = reactive({
  dimensionScores: {
    performance: null,
    ability: null,
    attitude: null
  }
})

const scoreFormRef = ref(null)
const submitting = ref(false)
const dimensionErrors = reactive({ performance: '', ability: '', attitude: '' })

const canSubmit = computed(() => {
  return Object.values(scoreForm.dimensionScores).every(
    s => s !== null && s !== undefined && s >= 0 && s <= 100
  )
})

onMounted(async () => {
  try {
    const res = await getMyAssessment()
    const items = res?.items || []
    const item = items.find(i => i.status === 'pending_self')
    if (item) {
      assessmentInfo.cycleName = item.cycle_name
      assessmentInfo.deadline = item.self_due_date
      assessmentInfo.recordId = item.record_id
    } else {
      ElMessage.info('当前没有待自评的考核')
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

  for (const dim of dimensions) {
    const score = scoreForm.dimensionScores[dim.key]
    if (score === null || score === undefined || score < 0 || score > 100) {
      dimensionErrors[dim.key] = '请填写 0-100 之间的分数'
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

.dimension-section h4 {
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
