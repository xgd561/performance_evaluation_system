<template>
  <PageContainer :title="pageTitle">
    <div class="score-sheet-layout">
      <!-- 左侧：被评人信息面板 -->
      <div class="employee-panel">
        <div class="panel-card">
          <!-- 待评人选择器 -->
          <div class="record-selector" v-if="toReviewList.length > 1">
            <el-select
              v-model="selectedRecordId"
              placeholder="选择被评人"
              style="width: 100%"
              @change="selectRecord"
            >
              <el-option
                v-for="item in toReviewList"
                :key="item.record_id"
                :label="`${item.employee_name} (${item.employee_no})`"
                :value="item.record_id"
              />
            </el-select>
            <el-divider />
          </div>
          <div v-else-if="toReviewList.length === 0" class="no-record-tip">
            <el-empty description="暂无待评人员" />
          </div>
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
              :disabled="!canSubmit || submitting"
              :loading="submitting"
              @click="handleSubmit"
            >
              提交评分
            </el-button>
            <el-button size="large" :loading="savingDraft" @click="handleSaveDraft">保存草稿</el-button>
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
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getToReviewList, submitManagerScore, getManagerDraft, saveManagerDraft, deleteManagerDraft } from '@/api/scores'
import { useAuthStore } from '@/stores/auth'
import { SCORE_ANCHORS, DIMENSION_TEXT } from '@/utils/constants'

const route = useRoute()
const authStore = useAuthStore()

// 模式：self / manager / peer
const mode = computed(() => {
  const role = authStore.user?.role
  if (role === 'employee') return 'self'
  if (role === 'manager') return 'manager'
  if (role === 'peer') return 'peer'
  return 'self'
})

// 加载状态
const loading = ref(false)
const toReviewList = ref([])
const selectedRecordId = ref(null)
const currentRecord = ref(null)

// 被评人信息（从 currentRecord 派生）
const employeeInfo = computed(() => {
  if (!currentRecord.value) {
    return { name: '-', department: '-', position: '-', cycleName: '-', stage: '-', deadline: null }
  }
  const r = currentRecord.value
  return {
    name: r.employee_name || '-',
    department: r.department_name || '-',
    position: r.position_name || '-',
    cycleName: r.cycle_name || '-',
    stage: '上级评分中',
    deadline: r.manager_due_date ? new Date(r.manager_due_date) : new Date(Date.now() + 5 * 24 * 60 * 60 * 1000)
  }
})

const pageTitle = computed(() => {
  const titles = { self: '自评', manager: '上级评分', peer: '协作评分' }
  return `${titles[mode.value] || '评分'} - ${employeeInfo.value.name}`
})

const stageTagType = computed(() => {
  const map = { '自评中': 'warning', '上级评分中': 'primary', '协作评分中': 'success' }
  return map[employeeInfo.value.stage] || 'info'
})

// 倒计时
const countdownDays = computed(() => {
  const diff = employeeInfo.value.deadline - Date.now()
  return Math.ceil(diff / (24 * 60 * 60 * 1000))
})
const countdownText = computed(() => {
  if (countdownDays.value <= 0) return '已截止'
  return `${countdownDays.value} 天`
})

// 员工自评参考（上级评分时显示）
const selfScores = computed(() => {
  if (!currentRecord.value || !currentRecord.value.self_scores) {
    return { performance: null, ability: null, attitude: null }
  }
  const s = currentRecord.value.self_scores
  return { performance: s.performance, ability: s.ability, attitude: s.attitude }
})

// 维度定义（从系统配置或常量获取，也可由后端返回）
const dimensions = [
  { key: 'performance', label: DIMENSION_TEXT.performance, weight: 60 },
  { key: 'ability', label: DIMENSION_TEXT.ability, weight: 20 },
  { key: 'attitude', label: DIMENSION_TEXT.attitude, weight: 20 }
]

// KPI 数据（从 currentRecord.kpi_snapshot 派生）
const kpiItems = computed(() => {
  if (!currentRecord.value || !currentRecord.value.kpi_snapshot) return []
  const snapshot = currentRecord.value.kpi_snapshot
  if (Array.isArray(snapshot)) {
    return snapshot.map((item, index) => ({
      name: item.name || item.kpi_name || `KPI ${index + 1}`,
      target: item.target_value || item.target || '-',
      weight: item.weight || 0,
      selfScore: item.self_score || null
    }))
  }
  if (typeof snapshot === 'object' && snapshot.items) {
    return snapshot.items.map((item, index) => ({
      name: item.name || item.kpi_name || `KPI ${index + 1}`,
      target: item.target_value || item.target || '-',
      weight: item.weight || 0,
      selfScore: item.self_score || null
    }))
  }
  return []
})

// 表单数据
const scoreForm = reactive({
  dimensionScores: { performance: null, ability: null, attitude: null },
  kpiScores: [],
  comment: ''
})

const scoreFormRef = ref(null)
const submitting = ref(false)
const savingDraft = ref(false)
const dimensionErrors = reactive({ performance: '', ability: '', attitude: '' })
const commentError = ref('')

// 差异确认弹窗
const diffDialogVisible = ref(false)
const diffDimension = ref('')
const diffScore = ref(0)
const diffSelfScore = ref(0)

// 监听 KPI 项目变化，初始化评分数组
watch(kpiItems, (items) => {
  scoreForm.kpiScores = new Array(items.length).fill(null)
}, { immediate: true })

// 挂载时获取待评列表
onMounted(async () => {
  loading.value = true
  try {
    const res = await getToReviewList()
    toReviewList.value = res || []
    if (toReviewList.value.length > 0) {
      // 支持通过 query 参数指定 recordId
      const queryRecordId = route.query.recordId ? parseInt(route.query.recordId) : null
      const target = queryRecordId
        ? toReviewList.value.find(r => r.record_id === queryRecordId)
        : toReviewList.value[0]
      if (target) {
        await selectRecord(target.record_id)
      } else {
        await selectRecord(toReviewList.value[0].record_id)
      }
    }
  } catch (e) {
    console.error('获取待评列表失败:', e)
    ElMessage.error('获取待评列表失败')
  } finally {
    loading.value = false
  }
})

// 选择被评人
async function selectRecord(recordId) {
  selectedRecordId.value = recordId
  currentRecord.value = toReviewList.value.find(r => r.record_id === recordId)
  resetScoreForm()
  await loadDraft(recordId)
}

function resetScoreForm() {
  scoreForm.dimensionScores = { performance: null, ability: null, attitude: null }
  scoreForm.comment = ''
  dimensionErrors.performance = ''
  dimensionErrors.ability = ''
  dimensionErrors.attitude = ''
  commentError.value = ''
  // kpiScores 由 watch 自动重置
}

async function loadDraft(recordId) {
  try {
    const res = await getManagerDraft(recordId)
    if (res.has_draft && res.draft) {
      const draft = res.draft
      if (draft.performance !== undefined && draft.performance !== null) {
        scoreForm.dimensionScores.performance = draft.performance
      }
      if (draft.ability !== undefined && draft.ability !== null) {
        scoreForm.dimensionScores.ability = draft.ability
      }
      if (draft.attitude !== undefined && draft.attitude !== null) {
        scoreForm.dimensionScores.attitude = draft.attitude
      }
      if (draft.comment !== undefined && draft.comment !== null) {
        scoreForm.comment = draft.comment
      }
      if (draft.kpi_scores && Array.isArray(draft.kpi_scores)) {
        scoreForm.kpiScores = draft.kpi_scores.slice(0, kpiItems.value.length)
      }
      ElMessage.info('已自动恢复上次保存的草稿')
    }
  } catch (e) {
    console.error('加载草稿失败:', e)
  }
}

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
  const allDimensionsFilled = Object.values(scoreForm.dimensionScores).every(
    s => s !== null && s !== undefined && s >= 0 && s <= 100
  )
  if (!allDimensionsFilled) return false
  if (mode.value === 'manager') {
    if (!scoreForm.comment || scoreForm.comment.length < 20) return false
  }
  return true
})

// 提交评分
async function handleSubmit() {
  if (submitting.value) return
  if (!selectedRecordId.value) {
    ElMessage.warning('请选择被评人')
    return
  }
  // 检查上级评分差异
  if (mode.value === 'manager') {
    const diffs = []
    for (const dim of dimensions) {
      const managerScore = scoreForm.dimensionScores[dim.key]
      const selfScore = selfScores.value[dim.key]
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
    const data = {
      performance: scoreForm.dimensionScores.performance,
      ability: scoreForm.dimensionScores.ability,
      attitude: scoreForm.dimensionScores.attitude,
      kpi_scores: scoreForm.kpiScores,
      comment: scoreForm.comment
    }
    await submitManagerScore(selectedRecordId.value, data)
    // 提交成功后删除草稿
    try {
      await deleteManagerDraft(selectedRecordId.value)
    } catch (e) {
      console.warn('删除草稿失败:', e)
    }
    ElMessage.success('评分提交成功')
    // 从列表中移除已评记录
    toReviewList.value = toReviewList.value.filter(r => r.record_id !== selectedRecordId.value)
    if (toReviewList.value.length > 0) {
      await selectRecord(toReviewList.value[0].record_id)
    } else {
      currentRecord.value = null
      selectedRecordId.value = null
      resetScoreForm()
    }
  } catch (error) {
    console.error('Submit failed:', error)
    ElMessage.error(error?.response?.data?.message || '评分提交失败')
  } finally {
    submitting.value = false
  }
}

// 保存草稿
async function handleSaveDraft() {
  if (!selectedRecordId.value) {
    ElMessage.warning('请选择被评人')
    return
  }
  savingDraft.value = true
  try {
    const data = {
      performance: scoreForm.dimensionScores.performance,
      ability: scoreForm.dimensionScores.ability,
      attitude: scoreForm.dimensionScores.attitude,
      kpi_scores: scoreForm.kpiScores,
      comment: scoreForm.comment
    }
    await saveManagerDraft(selectedRecordId.value, data)
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

.no-record-tip {
  padding: 40px 0;
}

.record-selector {
  margin-bottom: 16px;
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
