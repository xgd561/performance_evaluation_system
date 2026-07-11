<template>
  <div>
    <h2>强制分布处理</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="考核周期">
          <el-select v-model="queryForm.cycle_id" placeholder="选择周期" clearable @change="handleCycleChange">
            <el-option v-for="c in cycles" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData" :loading="loading" :disabled="!queryForm.cycle_id">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt-20" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>智能调整预览（已调整记录）</span>
          <el-tag type="warning">共 {{ adjustments.length }} 条</el-tag>
        </div>
      </template>
      <el-table :data="adjustments" border stripe>
        <el-table-column prop="record_id" label="记录ID" width="80" />
        <el-table-column prop="employee_no" label="工号" width="100" />
        <el-table-column prop="employee_name" label="姓名" width="100" />
        <el-table-column prop="total_score" label="总分" width="80" />
        <el-table-column prop="original_grade" label="原始等级" width="100">
          <template #default="scope">
            <el-tag type="success">{{ scope.row.original_grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="adjusted_grade" label="调整后等级" width="100">
          <template #default="scope">
            <el-tag type="danger">{{ scope.row.adjusted_grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_override" label="是否特批" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.is_override" type="success">已特批</el-tag>
            <el-tag v-else type="info">未特批</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="override_reason" label="特批原因" min-width="150" />
      </el-table>
      <el-empty v-if="!adjustments.length && !loading" description="暂无调整记录" />
    </el-card>

    <el-card class="mt-20" v-loading="overrideLoading">
      <template #header>
        <div class="card-header">
          <span>特批候选人</span>
          <div>
            <el-tag type="primary">共 {{ overrides.length }} 条</el-tag>
            <el-button
              type="success"
              size="small"
              class="ml-10"
              :disabled="selectedOverrides.length === 0"
              @click="handleBatchApprove"
            >一键特批</el-button>
            <el-button
              type="danger"
              size="small"
              :disabled="selectedOverrides.length === 0"
              @click="handleBatchReject"
            >批量驳回</el-button>
          </div>
        </div>
      </template>
      <el-table
        :data="overrides"
        border
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="record_id" label="记录ID" width="80" />
        <el-table-column prop="employee_no" label="工号" width="100" />
        <el-table-column prop="employee_name" label="姓名" width="100" />
        <el-table-column prop="total_score" label="总分" width="80" />
        <el-table-column prop="original_grade" label="原始等级" width="100">
          <template #default="scope">
            <el-tag type="success">{{ scope.row.original_grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="adjusted_grade" label="调整后等级" width="100">
          <template #default="scope">
            <el-tag type="danger">{{ scope.row.adjusted_grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="override_reason" label="特批原因" min-width="200" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button type="success" size="small" @click="handleApprove(scope.row.record_id)">特批</el-button>
            <el-button type="danger" size="small" @click="handleReject(scope.row.record_id)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!overrides.length && !overrideLoading" description="暂无特批申请" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listCycles } from '@/api/cycles'
import { getDistributionAdjustments, getDistributionOverrides, approveDistributionOverride, rejectDistributionOverride } from '@/api/distribution'

const loading = ref(false)
const overrideLoading = ref(false)
const cycles = ref([])
const adjustments = ref([])
const overrides = ref([])
const selectedOverrides = ref([])

const queryForm = reactive({
  cycle_id: null,
})

async function loadCycles() {
  try {
    const res = await listCycles()
    cycles.value = res || []
  } catch (e) {
    console.error(e)
  }
}

function handleCycleChange() {
  adjustments.value = []
  overrides.value = []
  selectedOverrides.value = []
}

async function loadAdjustments() {
  if (!queryForm.cycle_id) return
  loading.value = true
  try {
    const res = await getDistributionAdjustments(queryForm.cycle_id)
    adjustments.value = res.adjustments || []
  } catch (e) {
    console.error(e)
    ElMessage.error('获取调整明细失败')
  } finally {
    loading.value = false
  }
}

async function loadOverrides() {
  if (!queryForm.cycle_id) return
  overrideLoading.value = true
  try {
    console.log('[DistributionReview] loadOverrides cycle_id:', queryForm.cycle_id)
    const res = await getDistributionOverrides(queryForm.cycle_id)
    console.log('[DistributionReview] overrides response:', res)
    overrides.value = res || []
  } catch (e) {
    console.error('[DistributionReview] overrides error:', e)
    ElMessage.error('获取特批申请失败')
  } finally {
    overrideLoading.value = false
  }
}

async function loadData() {
  await Promise.all([loadAdjustments(), loadOverrides()])
}

function handleSelectionChange(selection) {
  selectedOverrides.value = selection
}

async function handleApprove(recordId) {
  try {
    await ElMessageBox.confirm('确认批准该特批申请？', '提示', { type: 'warning' })
    await approveDistributionOverride(recordId)
    ElMessage.success('特批已通过')
    loadOverrides()
    loadAdjustments()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

async function handleReject(recordId) {
  try {
    await ElMessageBox.confirm('确认驳回该特批申请？', '提示', { type: 'warning' })
    await rejectDistributionOverride(recordId)
    ElMessage.success('已驳回')
    loadOverrides()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

async function handleBatchApprove() {
  if (selectedOverrides.value.length === 0) {
    ElMessage.warning('请选择要特批的记录')
    return
  }
  try {
    await ElMessageBox.confirm(`确认批准选中的 ${selectedOverrides.value.length} 条特批申请？`, '提示', { type: 'warning' })
    const ids = selectedOverrides.value.map(item => item.record_id)
    for (const id of ids) {
      await approveDistributionOverride(id)
    }
    ElMessage.success('批量特批成功')
    selectedOverrides.value = []
    loadOverrides()
    loadAdjustments()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

async function handleBatchReject() {
  if (selectedOverrides.value.length === 0) {
    ElMessage.warning('请选择要驳回的记录')
    return
  }
  try {
    await ElMessageBox.confirm(`确认驳回选中的 ${selectedOverrides.value.length} 条特批申请？`, '提示', { type: 'warning' })
    const ids = selectedOverrides.value.map(item => item.record_id)
    for (const id of ids) {
      await rejectDistributionOverride(id)
    }
    ElMessage.success('批量驳回成功')
    selectedOverrides.value = []
    loadOverrides()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

onMounted(() => {
  loadCycles()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.search-form {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ml-10 {
  margin-left: 10px;
}
</style>
