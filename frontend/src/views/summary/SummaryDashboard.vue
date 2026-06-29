<template>
  <div>
    <h2>绩效汇总</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="考核周期">
          <el-select v-model="queryForm.cycle_id" placeholder="选择周期" clearable @change="onCycleChange">
            <el-option v-for="c in cycles" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="queryForm.department_id" placeholder="全部部门" clearable>
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button type="primary" @click="handleCalculate" :loading="calcLoading" :disabled="!queryForm.cycle_id">触发汇总计算</el-button>
      </div>

      <el-table :data="summaryData" style="width: 100%" v-loading="loading">
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="employee_name" label="姓名" width="120" />
        <el-table-column prop="department_name" label="部门" />
        <el-table-column prop="position_name" label="岗位" />
        <el-table-column prop="total_score" label="总分" width="100">
          <template #default="scope">
            <el-tag :type="scoreTagType(scope.row.total_score)">{{ scope.row.total_score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="grade" label="等级" width="100">
          <template #default="scope">
            <el-tag :type="gradeTagType(scope.row.grade)">{{ scope.row.grade || '—' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="weighted_performance" label="业绩分" width="100" />
        <el-table-column prop="weighted_ability" label="能力分" width="100" />
        <el-table-column prop="weighted_attitude" label="态度分" width="100" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <span>{{ statusText(scope.row.status) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Distribution Card -->
    <el-card class="mt-20" title="等级分布" v-if="distribution">
      <template #header>
        <span>等级分布</span>
      </template>
      <div v-if="distribution">
        <p>总人数：{{ distribution.total_records }}</p>
        <el-row :gutter="20" class="mt-20">
          <el-col :span="6" v-for="(count, grade) in distribution.overall_distribution" :key="grade">
            <el-statistic :title="grade + ' 等级'" :value="count" />
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getScoreSummary, calculateScores } from '@/api/scores'
import { getDistribution } from '@/api/reports'
import { listCycles } from '@/api/cycles'
import { listDepartments } from '@/api/departments'

const loading = ref(false)
const calcLoading = ref(false)
const summaryData = ref([])
const cycles = ref([])
const departments = ref([])
const distribution = ref(null)

const queryForm = reactive({
  cycle_id: null,
  department_id: null,
})

function scoreTagType(score) {
  if (!score) return 'info'
  const s = parseFloat(score)
  if (s >= 90) return 'success'
  if (s >= 80) return ''
  if (s >= 60) return 'warning'
  return 'danger'
}

function gradeTagType(grade) {
  if (grade === 'A') return 'success'
  if (grade === 'B') return ''
  if (grade === 'C') return 'warning'
  if (grade === 'D') return 'danger'
  return 'info'
}

function statusText(status) {
  const map = {
    pending_self: '待自评',
    pending_manager: '待上级评',
    pending_peer: '待协作评',
    pending_summary: '汇总中',
    pending_approval: '审批中',
    published: '已发布',
    archived: '已归档',
  }
  return map[status] || status
}

async function loadCycles() {
  try {
    const res = await listCycles()
    cycles.value = res || []
  } catch (e) {
    console.error(e)
  }
}

async function loadDepartments() {
  try {
    const res = await listDepartments()
    departments.value = res.length ? res : res.items || []
  } catch (e) {
    console.error(e)
  }
}

async function handleSearch() {
  if (!queryForm.cycle_id) {
    ElMessage.warning('请选择考核周期')
    return
  }
  loading.value = true
  try {
    const params = {}
    if (queryForm.department_id) {
      params.department_id = queryForm.department_id
    }
    const res = await getScoreSummary(queryForm.cycle_id, params)
    summaryData.value = res || []

    const dist = await getDistribution(queryForm.cycle_id)
    distribution.value = dist
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  queryForm.cycle_id = null
  queryForm.department_id = null
  summaryData.value = []
  distribution.value = null
}

function onCycleChange() {
  summaryData.value = []
  distribution.value = null
}

async function handleCalculate() {
  if (!queryForm.cycle_id) return
  try {
    await ElMessageBox.confirm('确认触发汇总计算？', '提示', { type: 'warning' })
    calcLoading.value = true
    await calculateScores(queryForm.cycle_id)
    ElMessage.success('汇总计算完成')
    handleSearch()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  } finally {
    calcLoading.value = false
  }
}

onMounted(() => {
  loadCycles()
  loadDepartments()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.search-form {
  margin-bottom: 16px;
}
.toolbar {
  margin-bottom: 16px;
}
</style>
