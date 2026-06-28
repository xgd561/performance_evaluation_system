<template>
  <div>
    <h2>系统配置</h2>
    <el-tabs v-model="activeTab" class="mt-20">
      <el-tab-pane label="等级规则" name="grades">
        <el-card>
          <el-form label-width="120px">
            <el-form-item v-for="(rule, grade) in gradeRules" :key="grade" :label="grade">
              <el-row :gutter="10">
                <el-col :span="8">
                  <el-input-number v-model="gradeRules[grade].min" placeholder="最低分" :precision="1" />
                </el-col>
                <el-col :span="2" style="text-align: center">~</el-col>
                <el-col :span="8">
                  <el-input-number v-model="gradeRules[grade].max" placeholder="最高分" :precision="1" />
                </el-col>
              </el-row>
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
            <el-form-item label="自评权重">
              <el-input-number v-model="dimensionWeights.self" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="上级评权重">
              <el-input-number v-model="dimensionWeights.manager" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="协作评权重">
              <el-input-number v-model="dimensionWeights.peer" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item>
              <el-tag :type="weightTotal === 100 ? 'success' : 'danger'">当前合计: {{ weightTotal }}% ({{ weightTotal === 100 ? '正确' : '应为100' }})</el-tag>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveDimensionWeights">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="评价人权重" name="reviewers">
        <el-card>
          <el-form label-width="120px">
            <el-form-item label="自评">
              <el-input-number v-model="reviewerWeights.self" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="上级">
              <el-input-number v-model="reviewerWeights.manager" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item label="协作">
              <el-input-number v-model="reviewerWeights.peer" :min="0" :max="100" :precision="0" />
            </el-form-item>
            <el-form-item>
              <el-tag :type="reviewerTotal === 100 ? 'success' : 'danger'">当前合计: {{ reviewerTotal }}% ({{ reviewerTotal === 100 ? '正确' : '应为100' }})</el-tag>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveReviewerWeights">保存</el-button>
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
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getGradeRules, updateGradeRules, getDimensionWeights, updateDimensionWeights, getReviewerWeights, updateReviewerWeights, getSmallDeptExemption, updateSmallDeptExemption } from '@/api/config'

const activeTab = ref('grades')

const gradeRules = reactive({
  A: { min: 90, max: 100 },
  B: { min: 80, max: 89.9 },
  C: { min: 60, max: 79.9 },
  D: { min: 0, max: 59.9 },
})

const dimensionWeights = reactive({ self: 30, manager: 50, peer: 20 })
const reviewerWeights = reactive({ self: 10, manager: 70, peer: 20 })
const smallDeptExemption = reactive({ threshold: 5, enabled: false })

const weightTotal = computed(() => (dimensionWeights.self || 0) + (dimensionWeights.manager || 0) + (dimensionWeights.peer || 0))
const reviewerTotal = computed(() => (reviewerWeights.self || 0) + (reviewerWeights.manager || 0) + (reviewerWeights.peer || 0))

async function loadAll() {
  try {
    const gr = await getGradeRules()
    if (gr) Object.assign(gradeRules, gr)

    const dw = await getDimensionWeights()
    if (dw) Object.assign(dimensionWeights, dw)

    const rw = await getReviewerWeights()
    if (rw) Object.assign(reviewerWeights, rw)

    const sd = await getSmallDeptExemption()
    if (sd) Object.assign(smallDeptExemption, sd)
  } catch (e) {
    console.error(e)
  }
}

async function saveGradeRules() {
  try {
    await updateGradeRules(gradeRules)
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
  if (reviewerTotal.value !== 100) {
    ElMessage.warning('权重合计必须为100')
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
