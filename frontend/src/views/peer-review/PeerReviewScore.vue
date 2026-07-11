<template>
  <PageContainer :title="pageTitle">
    <div class="score-sheet-layout">
      <!-- 左侧：被评人信息面板 -->
      <div class="employee-panel">
        <div class="panel-card">
          <div class="employee-avatar">
            <el-avatar :size="64" :icon="UserFilled" />
          </div>
          <h3 class="employee-name">{{ employeeInfo.name }}</h3>
          <p class="employee-meta">{{ employeeInfo.department }} · {{ employeeInfo.position }}</p>
          <el-divider />
          <div class="info-row">
            <span class="info-label">考核周期</span>
            <span class="info-value">{{ employeeInfo.cycleName }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">考核阶段</span>
            <el-tag type="warning">{{ employeeInfo.stage }}</el-tag>
          </div>
          <div class="info-row" v-if="employeeInfo.deadline">
            <span class="info-label">剩余时间</span>
            <span class="info-value countdown" :class="{ urgent: countdownDays <= 3 }">
              {{ countdownText }}
            </span>
          </div>
          <el-divider />
          <div class="score-comparison" v-if="selfScores">
            <h4>员工自评参考</h4>
            <div class="comparison-item">
              <span>工作业绩</span>
              <span class="score">{{ selfScores.performance || '-' }}</span>
            </div>
            <div class="comparison-item">
              <span>工作能力</span>
              <span class="score">{{ selfScores.ability || '-' }}</span>
            </div>
            <div class="comparison-item">
              <span>工作态度</span>
              <span class="score">{{ selfScores.attitude || '-' }}</span>
            </div>
          </div>
          <div class="score-comparison" v-if="managerScores">
            <h4>上级评分参考</h4>
            <div class="comparison-item">
              <span>工作业绩</span>
              <span class="score">{{ managerScores.performance || '-' }}</span>
            </div>
            <div class="comparison-item">
              <span>工作能力</span>
              <span class="score">{{ managerScores.ability || '-' }}</span>
            </div>
            <div class="comparison-item">
              <span>工作态度</span>
              <span class="score">{{ managerScores.attitude || '-' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：评分区域 -->
      <div class="score-area">
        <el-form ref="scoreFormRef" :model="scoreForm" label-position="top">
          <!-- 维度评分（仅工作能力） -->
          <div class="dimension-section">
            <h4>协作评分</h4>
            <p class="section-desc">请对被评人的<span class="highlight">工作能力</span>进行评分（0-100分）</p>
            <div class="dimension-list">
              <div class="dimension-item" :class="{ 'has-error': dimensionError }">
                <div class="dim-header">
                  <span class="dim-name">工作能力</span>
                  <span class="dim-weight">权重 20%</span>
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
                  v-model="scoreForm.ability"
                  :min="0"
                  :max="100"
                  :precision="1"
                  :step="1"
                  placeholder="0-100"
                  class="score-input"
                  :disabled="isLocked"
                />
                <span v-if="dimensionError" class="error-msg">{{ dimensionError }}</span>
              </div>
            </div>
          </div>

          <!-- 协作评语 -->
          <div class="comment-section">
            <h4>协作评语</h4>
            <p class="section-desc">请对被评人的工作表现进行综合评价，不少于20字，不超过500字</p>
            <el-input
              v-model="scoreForm.comment"
              type="textarea"
              :rows="6"
              :maxlength="500"
              :disabled="isLocked"
              placeholder="请输入协作评语..."
              show-word-limit
              :class="{ 'has-error': commentError }"
            />
            <span v-if="commentError" class="error-msg">{{ commentError }}</span>
          </div>

          <!-- 提交按钮 -->
          <div class="submit-section" v-if="!isLocked">
            <el-button
              type="primary"
              size="large"
              :disabled="!canSubmit"
              :loading="submitting"
              @click="handleSubmit"
            >
              提交评分
            </el-button>
            <el-button size="large" @click="handleCancel">返回</el-button>
          </div>
          <div class="submit-section" v-else>
            <el-tag type="success" size="large">评分已提交</el-tag>
            <el-button size="large" @click="handleCancel">返回</el-button>
          </div>
        </el-form>
      </div>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageContainer from '@/components/PageContainer.vue'
import { getPeerReviewList, submitPeerReviewTask } from '@/api/scores'
import { SCORE_ANCHORS } from '@/utils/constants'

const route = useRoute()
const router = useRouter()
const taskId = computed(() => route.params.taskId)

const pageTitle = computed(() => `协作评分 - ${employeeInfo.name}`)

const employeeInfo = reactive({
  name: '-',
  department: '-',
  position: '-',
  cycleName: '-',
  stage: '协作评分中',
  deadline: null
})

const selfScores = ref(null)
const managerScores = ref(null)
const taskStatus = ref('pending')

const countdownDays = computed(() => {
  if (!employeeInfo.deadline) return 1
  const diff = new Date(employeeInfo.deadline) - Date.now()
  return Math.ceil(diff / (24 * 60 * 60 * 1000))
})
const countdownText = computed(() => {
  if (!employeeInfo.deadline) return '-'
  if (countdownDays.value <= 0) return '已截止'
  return `${countdownDays.value} 天`
})

const scoreForm = reactive({
  ability: null,
  comment: ''
})

const scoreFormRef = ref(null)
const submitting = ref(false)
const dimensionError = ref('')
const commentError = ref('')

const isLocked = computed(() => taskStatus.value === 'completed')

const canSubmit = computed(() => {
  return scoreForm.ability !== null
    && scoreForm.ability >= 0
    && scoreForm.ability <= 100
    && scoreForm.comment.trim().length >= 20
    && scoreForm.comment.trim().length <= 500
})

onMounted(async () => {
  try {
    const res = await getPeerReviewList()
    const items = res?.items || []
    const item = items.find(i => String(i.task_id) === String(taskId.value))
    if (!item) {
      ElMessage.error('评分任务不存在')
      router.push('/peer-review')
      return
    }
    employeeInfo.name = item.employee_name
    employeeInfo.department = item.department_name
    employeeInfo.position = item.position_name
    employeeInfo.cycleName = item.cycle_name
    employeeInfo.deadline = item.peer_due_date
    taskStatus.value = item.status || 'pending'
    selfScores.value = item.self_scores || null
    managerScores.value = item.manager_scores || null
    // 已提交时回显数据
    if (item.status === 'completed') {
      scoreForm.ability = item.ability_score ? parseFloat(item.ability_score) : null
      scoreForm.comment = item.comment || ''
      employeeInfo.stage = '协作评分已完成'
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载评分数据失败')
  }
})

async function handleSubmit() {
  if (scoreForm.ability === null || scoreForm.ability < 0 || scoreForm.ability > 100) {
    dimensionError.value = '分数需在 0-100 之间'
    return
  }
  dimensionError.value = ''

  const comment = scoreForm.comment.trim()
  if (comment.length < 20) {
    commentError.value = '协作评语不少于20字'
    return
  }
  if (comment.length > 500) {
    commentError.value = '协作评语不超过500字'
    return
  }
  commentError.value = ''

  submitting.value = true
  try {
    await submitPeerReviewTask(taskId.value, {
      ability: scoreForm.ability,
      comment: comment
    })
    ElMessage.success('评分提交成功')
    taskStatus.value = 'completed'
    employeeInfo.stage = '协作评分已完成'
  } catch (error) {
    console.error('Submit failed:', error)
    ElMessage.error(error?.response?.data?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  router.push('/peer-review')
}
</script>

<style scoped>
.score-sheet-layout {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 200px);
}

.employee-panel {
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

.employee-avatar {
  text-align: center;
  margin-bottom: 16px;
}

.employee-name {
  text-align: center;
  margin: 0 0 8px;
  font-size: 18px;
  color: #303133;
}

.employee-meta {
  text-align: center;
  margin: 0 0 16px;
  font-size: 14px;
  color: #909399;
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

.score-comparison h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #303133;
}

.comparison-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px solid #ebeef5;
}

.comparison-item .score {
  color: #409eff;
  font-weight: 600;
}

.score-area {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.dimension-section h4,
.comment-section h4 {
  margin: 0 0 8px;
  font-size: 16px;
  color: #303133;
}

.section-desc {
  font-size: 13px;
  color: #606266;
  margin-bottom: 16px;
}

.section-desc .highlight {
  color: #409eff;
  font-weight: 600;
}

.dimension-list {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
}

.dimension-item {
  flex: 1;
  max-width: 300px;
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

.comment-section {
  margin-bottom: 24px;
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
  display: block;
}

@media (max-width: 1024px) {
  .score-sheet-layout {
    flex-direction: column;
  }

  .employee-panel {
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
