<template>
  <div>
    <h2>系统配置</h2>
    <el-tabs v-model="activeTab" class="mt-20">
      <el-tab-pane label="等级规则" name="grades">
        <el-card>
          <el-form label-width="120px">
            <el-form-item v-for="(rule, grade) in gradeRules" :key="grade" :label="grade">
              <el-row :gutter="10" align="middle">
                <el-col :span="6">
                  <el-input-number v-model="gradeRules[grade].min" placeholder="最低分" :precision="1" :min="0" :max="100" style="width: 100%" />
                </el-col>
                <el-col :span="1" style="text-align: center">~</el-col>
                <el-col :span="6">
                  <el-input-number v-model="gradeRules[grade].max" placeholder="最高分" :precision="1" :min="0" :max="100" style="width: 100%" />
                </el-col>
                <el-col :span="1" style="text-align: center"></el-col>
                <el-col :span="6">
                  <el-input-number v-model="gradeRules[grade].ratio_limit" placeholder="人数上限%" :precision="0" :min="0" :max="100" style="width: 100%" />
                </el-col>
                <el-col :span="2" style="text-align: center">%</el-col>
              </el-row>
            </el-form-item>
            <el-form-item>
              <el-tag :type="ratioTotal <= 100 ? 'success' : 'danger'" size="large">比例上限合计: {{ ratioTotal }}% ({{ ratioTotal <= 100 ? '正确' : '不能超过100%' }})</el-tag>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveGradeRules">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="维度权重" name="weights">
        <el-card>
          <el-form label-width="120px">
            <el-form-item label="工作业绩权重">
              <el-input-number v-model="dimensionWeights.performance" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="工作能力权重">
              <el-input-number v-model="dimensionWeights.ability" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="工作态度权重">
              <el-input-number v-model="dimensionWeights.attitude" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item>
              <el-tag :type="weightTotal === 100 ? 'success' : 'danger'">当前合计: {{ weightTotal }}% ({{ weightTotal === 100 ? '正确' : '应为100' }})</el-tag>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="weightTotal !== 100" @click="saveDimensionWeights">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="评价人权重" name="reviewers">
        <el-card>
          <el-form label-width="120px">
            <h4>业绩维度</h4>
            <el-form-item label="自评">
              <el-input-number v-model="reviewerWeights.performance.self" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="上级">
              <el-input-number v-model="reviewerWeights.performance.manager" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="协作">
              <el-input-number v-model="reviewerWeights.performance.peer" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item>
              <el-tag :type="performanceReviewerTotal === 100 ? 'success' : 'danger'">业绩维度合计: {{ performanceReviewerTotal }}% ({{ performanceReviewerTotal === 100 ? '正确' : '应为100' }})</el-tag>
            </el-form-item>

            <h4>能力维度</h4>
            <el-form-item label="自评">
              <el-input-number v-model="reviewerWeights.ability.self" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="上级">
              <el-input-number v-model="reviewerWeights.ability.manager" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="协作">
              <el-input-number v-model="reviewerWeights.ability.peer" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item>
              <el-tag :type="abilityReviewerTotal === 100 ? 'success' : 'danger'">能力维度合计: {{ abilityReviewerTotal }}% ({{ abilityReviewerTotal === 100 ? '正确' : '应为100' }})</el-tag>
            </el-form-item>

            <h4>态度维度</h4>
            <el-form-item label="自评">
              <el-input-number v-model="reviewerWeights.attitude.self" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="上级">
              <el-input-number v-model="reviewerWeights.attitude.manager" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="协作">
              <el-input-number v-model="reviewerWeights.attitude.peer" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item>
              <el-tag :type="attitudeReviewerTotal === 100 ? 'success' : 'danger'">态度维度合计: {{ attitudeReviewerTotal }}% ({{ attitudeReviewerTotal === 100 ? '正确' : '应为100' }})</el-tag>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :disabled="!allReviewerTotalsValid" @click="saveReviewerWeights">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="小部门豁免" name="small_dept">
        <el-card>
          <el-form label-width="180px">
            <el-form-item label="部门人数阈值">
              <el-input-number v-model="smallDeptExemption.threshold" :min="0" :max="50" :precision="0" />
              <span class="hint"> 人以下视为小部门，不参与强制分布</span>
            </el-form-item>
            <el-form-item label="豁免开关">
              <el-switch v-model="smallDeptExemption.enabled" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveSmallDept">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="协作评分开关" name="peer_review">
        <el-card>
          <el-form label-width="180px">
            <el-form-item label="协作评分全局默认值">
              <el-switch v-model="peerReviewEnabled" />
              <span class="hint"> 关闭后，新创建的考核周期默认不启用协作评分</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="savePeerReviewEnabled">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getGradeRules, updateGradeRules, getDimensionWeights, updateDimensionWeights, getReviewerWeights, updateReviewerWeights, getSmallDeptExemption, updateSmallDeptExemption, getPeerReviewEnabled, updatePeerReviewEnabled } from '@/api/config'

const activeTab = ref('grades')

const gradeRules = reactive({
  A: { min: 90, max: 100, ratio_limit: 20 },
  B: { min: 80, max: 89.9, ratio_limit: 50 },
  C: { min: 60, max: 79.9, ratio_limit: 25 },
  D: { min: 0, max: 59.9, ratio_limit: 5 },
})

const dimensionWeights = reactive({ performance: 60, ability: 20, attitude: 20 })
const reviewerWeights = reactive({
  performance: { self: 30, manager: 70, peer: 0 },
  ability: { self: 20, manager: 60, peer: 20 },
  attitude: { self: 10, manager: 50, peer: 40 }
})
const smallDeptExemption = reactive({ threshold: 5, enabled: false })
const peerReviewEnabled = ref(true)

const weightTotal = computed(() => (dimensionWeights.performance || 0) + (dimensionWeights.ability || 0) + (dimensionWeights.attitude || 0))
const performanceReviewerTotal = computed(() => reviewerWeights.performance.self + reviewerWeights.performance.manager + reviewerWeights.performance.peer)
const abilityReviewerTotal = computed(() => reviewerWeights.ability.self + reviewerWeights.ability.manager + reviewerWeights.ability.peer)
const attitudeReviewerTotal = computed(() => reviewerWeights.attitude.self + reviewerWeights.attitude.manager + reviewerWeights.attitude.peer)
const allReviewerTotalsValid = computed(() => performanceReviewerTotal.value === 100 && abilityReviewerTotal.value === 100 && attitudeReviewerTotal.value === 100)
const ratioTotal = computed(() => {
  let total = 0
  for (const g of ['A', 'B', 'C', 'D']) {
    total += (Number(gradeRules[g]?.ratio_limit) || 0)
  }
  return total
})

function validateGradeRules() {
  const grades = ['A', 'B', 'C', 'D']
  for (const g of grades) {
    const rule = gradeRules[g]
    if (rule === undefined || rule.min === undefined || rule.max === undefined || rule.ratio_limit === undefined) {
      return `缺少等级规则: ${g}`
    }
    if (Number(rule.min) >= Number(rule.max)) {
      return `等级 ${g}: 最低分必须小于最高分`
    }
  }

  const entries = grades.map(g => ({
    name: g,
    min: Number(gradeRules[g].min),
    max: Number(gradeRules[g].max),
    ratioLimit: Number(gradeRules[g].ratio_limit) / 100,
  })).sort((a, b) => a.min - b.min)

  const lowestMin = Math.min(...entries.map(e => e.min))
  const highestMax = Math.max(...entries.map(e => e.max))
  if (lowestMin > 0) return '最低等级最低分必须等于 0'
  if (highestMax < 100) return '最高等级最高分必须等于 100'

  for (let i = 0; i < entries.length - 1; i++) {
    const curr = entries[i]
    const next = entries[i + 1]
    if (curr.max > next.min) {
      return `区间重叠: ${curr.name}(${curr.min}-${curr.max}) 与 ${next.name}(${next.min}-${next.max})`
    }
    if (next.min > curr.max + 1) {
      return `区间不连续: ${curr.name}(${curr.max}) 与 ${next.name}(${next.min})`
    }
  }

  const totalRatio = entries.reduce((sum, e) => sum + e.ratioLimit, 0)
  if (totalRatio > 1.0) {
    return `比例上限合计不能超过 100%，当前为 ${(totalRatio * 100).toFixed(0)}%`
  }

  return null
}

async function loadAll() {
  try {
    const gr = await getGradeRules()
    if (gr) {
      for (const g of ['A', 'B', 'C', 'D']) {
        if (gr[g] !== undefined) {
          if (typeof gr[g] === 'number') {
            gradeRules[g].min = gr[g]
          } else if (typeof gr[g] === 'object' && gr[g] !== null) {
            if (gr[g].min !== undefined) gradeRules[g].min = gr[g].min
            if (gr[g].max !== undefined) gradeRules[g].max = gr[g].max
            if (gr[g].ratio_limit !== undefined) {
              gradeRules[g].ratio_limit = Math.round(gr[g].ratio_limit * 100)
            }
          }
        }
      }
    }

    const dw = await getDimensionWeights()
    if (dw) Object.assign(dimensionWeights, dw)

    const rw = await getReviewerWeights()
    if (rw) {
      if (rw.performance) Object.assign(reviewerWeights.performance, rw.performance)
      if (rw.ability) Object.assign(reviewerWeights.ability, rw.ability)
      if (rw.attitude) Object.assign(reviewerWeights.attitude, rw.attitude)
    }

    const sd = await getSmallDeptExemption()
    if (sd) Object.assign(smallDeptExemption, sd)

    const pr = await getPeerReviewEnabled()
    if (pr && typeof pr.enabled === 'boolean') {
      peerReviewEnabled.value = pr.enabled
    }
  } catch (e) {
    console.error(e)
  }
}

async function saveGradeRules() {
  const error = validateGradeRules()
  if (error) {
    ElMessage.warning(error)
    return
  }
  const payload = {}
  for (const g of ['A', 'B', 'C', 'D']) {
    payload[g] = {
      min: Number(gradeRules[g].min),
      max: Number(gradeRules[g].max),
      ratio_limit: Number(gradeRules[g].ratio_limit) / 100,
    }
  }
  try {
    await updateGradeRules(payload)
    ElMessage.success('保存成功')
  } catch (e) {
    console.error(e)
  }
}

async function saveDimensionWeights() {
  if (weightTotal.value !== 100) {
    ElMessage.warning('权重合计必须为100')
    return
  }
  try {
    await updateDimensionWeights(dimensionWeights)
    ElMessage.success('保存成功')
  } catch (e) {
    console.error(e)
  }
}

async function saveReviewerWeights() {
  if (!allReviewerTotalsValid.value) {
    ElMessage.warning('每个维度内的权重合计必须为100')
    return
  }
  try {
    await updateReviewerWeights(reviewerWeights)
    ElMessage.success('保存成功')
  } catch (e) {
    console.error(e)
  }
}

async function saveSmallDept() {
  try {
    await updateSmallDeptExemption(smallDeptExemption)
    ElMessage.success('保存成功')
  } catch (e) {
    console.error(e)
  }
}

async function savePeerReviewEnabled() {
  try {
    await updatePeerReviewEnabled({ enabled: peerReviewEnabled.value })
    ElMessage.success('保存成功')
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.hint {
  color: #909399;
  margin-left: 8px;
}
</style>
