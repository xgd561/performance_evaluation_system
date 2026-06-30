<template>
  <div>
    <h2>KPI 调整审批</h2>
    <el-card class="mt-20" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>待审批申请</span>
          <el-tag type="warning">共 {{ pendingList.length }} 条</el-tag>
        </div>
      </template>

      <el-table :data="pendingList" border stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="申请ID" width="80" />
        <el-table-column prop="record_id" label="记录ID" width="80" />
        <el-table-column label="原始 KPI" min-width="200">
          <template #default="{ row }">
            <pre class="kpi-json">{{ formatKpi(row.original_kpi) }}</pre>
          </template>
        </el-table-column>
        <el-table-column label="调整后" min-width="200">
          <template #default="{ row }">
            <pre class="kpi-json">{{ formatAdjusted(row.adjusted_kpi) }}</pre>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="调整原因" min-width="150" />
        <el-table-column prop="created_at" label="提交时间" width="160">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="success" size="small" @click="handleApprove(row.id)">通过</el-button>
            <el-button type="danger" size="small" @click="handleReject(row.id)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="pendingList.length === 0 && !loading" description="暂无待审批申请" />

      <div class="batch-actions" v-if="selectedRows.length > 0">
        <el-button type="success" @click="handleBatchApprove">批量通过</el-button>
        <el-button type="danger" @click="handleBatchReject">批量驳回</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPendingKpiAdjustments, approveKpiAdjustment, rejectKpiAdjustment } from '@/api/kpiAdjustment'

const loading = ref(false)
const pendingList = ref([])
const selectedRows = ref([])

function formatKpi(originalKpi) {
  try {
    const data = JSON.parse(originalKpi)
    if (Array.isArray(data)) {
      return data.map(item => `${item.name || item.kpi_name}: ${item.target_value || item.target || '-'} (权重${item.weight || 0}%)`).join('\n')
    }
    if (data && data.items) {
      return data.items.map(item => `${item.name || item.kpi_name}: ${item.target_value || item.target || '-'} (权重${item.weight || 0}%)`).join('\n')
    }
    return JSON.stringify(data, null, 2)
  } catch (e) {
    return originalKpi
  }
}

function formatAdjusted(adjustedKpi) {
  try {
    const data = JSON.parse(adjustedKpi)
    if (data.kpi_id && data.new_target) {
      return `KPI ID: ${data.kpi_id}\n新目标值: ${data.new_target}`
    }
    return JSON.stringify(data, null, 2)
  } catch (e) {
    return adjustedKpi
  }
}

async function loadPending() {
  loading.value = true
  try {
    const res = await getPendingKpiAdjustments()
    pendingList.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error(e)
    ElMessage.error('获取待审批列表失败')
  } finally {
    loading.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function handleApprove(id) {
  try {
    await ElMessageBox.confirm('确认通过该 KPI 调整申请？', '提示', { type: 'warning' })
    await approveKpiAdjustment(id)
    ElMessage.success('已通过')
    loadPending()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

async function handleReject(id) {
  try {
    await ElMessageBox.confirm('确认驳回该 KPI 调整申请？', '提示', { type: 'warning' })
    await rejectKpiAdjustment(id)
    ElMessage.success('已驳回')
    loadPending()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

async function handleBatchApprove() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请选择要通过的记录')
    return
  }
  try {
    await ElMessageBox.confirm(`确认通过选中的 ${selectedRows.value.length} 条申请？`, '提示', { type: 'warning' })
    for (const row of selectedRows.value) {
      await approveKpiAdjustment(row.id)
    }
    ElMessage.success('批量通过成功')
    selectedRows.value = []
    loadPending()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

async function handleBatchReject() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请选择要驳回的记录')
    return
  }
  try {
    await ElMessageBox.confirm(`确认驳回选中的 ${selectedRows.value.length} 条申请？`, '提示', { type: 'warning' })
    for (const row of selectedRows.value) {
      await rejectKpiAdjustment(row.id)
    }
    ElMessage.success('批量驳回成功')
    selectedRows.value = []
    loadPending()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

onMounted(() => {
  loadPending()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.batch-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}
.kpi-json {
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #606266;
}
</style>
