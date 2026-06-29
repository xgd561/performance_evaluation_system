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
            <el-tag :type="stageTagType">{{ employeeInfo.stage }}</el-tag>
          </div>
          <div class="info-row">
            <span class="info-label">剩余时间</span>
            <span class="info-value countdown" :class="{ urgent: countdownDays <= 3 }">
              {{ countdownText }}
            </span>
          </div>
          <el-divider />
          <div v-if="mode === 'manager'" class="score-comparison">
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
        </div>
      </div>

      <!-- 右侧：评分区域 -->
      <div class="score-area">
        <el-form ref="scoreFormRef" :model="scoreForm" label-position="top">
          <!-- 维度评分 -->
          <div class="dimension-section">
            <h4>维度评分</h4>
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

          <!-- KPI 逐项评分（仅业绩维度） -->
          <div v-if="mode === 'manager' || mode === 'self'" class="kpi-section">
            <h4>KPI 逐项评分</h4>
            <el-table :data="kpiItems" style="width: 100%" border>
              <el-table-column prop="name" label="指标名称" min-width="150" />
              <el-table-column prop="target" label="目标值" min-width="120" />
              <el-table-column prop="weight" label="权重" width="100">
                <template #default="{ row }">{{ row.weight }}%</template>
              </el-table-column>
              <el-table-column v-if="mode === 'manager'" label="自评分" width="100">
                <template #default="{ row }">{{ row.selfScore || '-' }}</template>
              </el-table-column>
              <el-table-column :label="mode === 'self' ? '自评分' : '上级评分'" width="140">
                <template #default="{ row, $index }">
                  <el-input-number
                    v-model="scoreForm.kpiScores[$index]"
                    :min="0"
                    :max="100"
                    :precision="1"
                    :step="1"
                    size="small"
                    placeholder="0-100"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 评语区 -->
          <div v-if="mode === 'manager'" class="comment-section">
            <h4>综合评语</h4>
            <el-form-item
              :rules="[{ required: true, message: '请填写综合评语', trigger: 'blur' }]"
            >
              <el-input
                v-model="scoreForm.comment"
                type="textarea"
                :rows="4"
                placeholder="请填写综合评语（不少于20字）"
                maxlength="500"
                show-word-limit
              />
            </el-form-item>
            <p v-if="commentError" class="error-msg">{{ commentError }}</p>
          </div>

          <!-- 提交按钮 -->
          <div class="submit-section">
            <el-button
              type="primary"
              size="large"
              :disabled="!canSubmit"
              :loading="submitting"
              @click="handleSubmit"
            >
              提交评分
            </el-button>
            <el-button size="large" @click="handleSaveDraft">保存草稿</el-button>
          </div>
        </el-form>
      </div>
    </div>

    <!-- 差异确认弹窗 -->
    <el-dialog v-model="diffDialogVisible" title="评分差异确认" width="400px">
      <p>您给 <strong>{{ diffDimension }}</strong> 打的 <strong>{{ diffScore }}</strong> 分</p>
      <p>与员工自评 <strong>{{ diffSelfScore }}</strong> 分差异较大（超过20分）</p>
      <p>请确认是否继续？</p>
      <template #footer>
        <el-button @click="diffDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmDiffSubmit">确认提交</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getToReviewList, submitManagerScore } from '@/api/scores'
import { useAuthStore } from '@/stores/auth'
import { SCORE_ANCHORS, DIMENSION_TEXT } from '@/utils/constants'

const route = useRoute()
const authStore = useAuthStore()

// 模式：self / manager / peer
const mode = computed(() => {
  const role = authStore.userInfo?.role
  if (role === 'employee') return 'self'
  if (role === 'manager') return 'manager'
  if (role === 'peer') return 'peer'
  return 'self'
})

const pageTitle = computed(() => {
  const titles = { self: '自评', manager: '上级评分', peer: '协作评分' }
  return `${titles[mode.value] || '评分'} - ${employeeInfo.name}`
})

// 被评人信息（mock）
const employeeInfo = reactive({
  name: '张三',
  department: '技术部',
  position: 'Java 开发工程师',
  cycleName: '2026年Q2季度考核',
  stage: '上级评分中',
  deadline: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000) // 5天后截止
})

const stageTagType = computed(() => {
  const map = { '自评中': 'warning', '上级评分中': 'primary', '协作评分中': 'success' }
  return map[employeeInfo.stage] || 'info'
})

// 倒计时
const countdownDays = computed(() => {
  const diff = employeeInfo.deadline - Date.now()
  return Math.ceil(diff / (24 * 60 * 60 * 1000))
})
const countdownText = computed(() => {
  if (countdownDays.value <= 0) return '已截止'
  return `${countdownDays.value} 天`
})

// 员工自评参考（上级评分时显示）
const selfScores = reactive({
  performance: 85,
  ability: 90,
  attitude: 88
})

// 维度定义
const dimensions = [
  { key: 'performance', label: DIMENSION_TEXT.performance, weight: 60 },
  { key: 'ability', label: DIMENSION_TEXT.ability, weight: 20 },
  { key: 'attitude', label: DIMENSION_TEXT.attitude, weight: 20 }
]

// KPI 数据（mock）
const kpiItems = [
  { name: '销售额完成率', target: '100万', weight: 40, selfScore: 85 },
  { name: '项目交付准时率', target: '≥95%', weight: 30, selfScore: 90 },
  { name: '代码质量', target: '无P0缺陷', weight: 30, selfScore: 88 }
]

// 表单数据
const scoreForm = reactive({
  dimensionScores: {
    performance: null,
    ability: null,
    attitude: null
  },
  kpiScores: [null, null, null],
  comment: ''
})

const scoreFormRef = ref(null)
const submitting = ref(false)
const dimensionErrors = reactive({ performance: '', ability: '', attitude: '' })
const commentError = ref('')

// 差异确认弹窗
const diffDialogVisible = ref(false)
const diffDimension = ref('')
const diffScore = ref(0)
const diffSelfScore = ref(0)

// 校验维度分数
function handleDimensionScoreChange(dimKey, val) {
  dimensionErrors[dimKey] = ''
  if (val === null || val === undefined) return
  if (val < 0 || val > 100) {
    dimensionErrors[dimKey] = '分数需在 0-100 之间'
  }
}

// 检查是否可以提交
const canSubmit = computed(() => {
  // 所有维度已填写
  const allDimensionsFilled = Object.values(scoreForm.dimensionScores).every(
    s => s !== null && s !== undefined && s >= 0 && s <= 100
  )
  if (!allDimensionsFilled) return false

  // 上级评分时评语不少于20字
  if (mode.value === 'manager') {
    if (!scoreForm.comment || scoreForm.comment.length < 20) return false
  }

  return true
})

// 提交评分
async function handleSubmit() {
  // 检查上级评分差异
  if (mode.value === 'manager') {
    const diffs = []
    for (const dim of dimensions) {
      const managerScore = scoreForm.dimensionScores[dim.key]
      const selfScore = selfScores[dim.key]
      if (managerScore !== null && selfScore !== null && Math.abs(managerScore - selfScore) > 20) {
        diffs.push({ dim: dim.label, managerScore, selfScore })
      }
    }
    if (diffs.length > 0 && !diffDialogVisible.value) {
      diffDimension.value = diffs[0].dim
      diffScore.value = diffs[0].managerScore
      diffSelfScore.value = diffs[0].selfScore
      diffDialogVisible.value = true
      return
    }
  }

  await doSubmit()
}

async function confirmDiffSubmit() {
  diffDialogVisible.value = false
  await doSubmit()
}

async function doSubmit() {
  submitting.value = true
  try {
    // TODO: 调用 API 提交评分
    // await submitManagerScore(recordId, scoreForm)
    ElMessage.success('评分提交成功')
  } catch (error) {
    console.error('Submit failed:', error)
  } finally {
    submitting.value = false
  }
}

// 保存草稿
async function handleSaveDraft() {
  try {
    // TODO: 调用 API 保存草稿
    // await saveDraft(recordId, scoreForm)
    ElMessage.success('草稿保存成功')
  } catch (error) {
    console.error('Save draft failed:', error)
  }
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
.kpi-section h4,
.comment-section h4 {
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

.kpi-section,
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
