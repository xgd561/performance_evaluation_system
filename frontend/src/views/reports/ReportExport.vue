<template>
  <div>
    <h2>报表导出</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="考核周期">
          <el-select v-model="queryForm.cycle_id" placeholder="选择周期" clearable>
            <el-option v-for="c in cycles" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleExport" :loading="exportLoading" :disabled="!queryForm.cycle_id">导出 Excel</el-button>
        </el-form-item>
      </el-form>

      <el-divider v-if="reportData">预览</el-divider>

      <el-table v-if="reportData" :data="reportData.rows" style="width: 100%" max-height="500">
        <el-table-column prop="工号" label="工号" width="120" />
        <el-table-column prop="姓名" label="姓名" width="120" />
        <el-table-column prop="部门" label="部门" />
        <el-table-column prop="总分" label="总分" width="100" />
        <el-table-column prop="等级" label="等级" width="100" />
        <el-table-column prop="业绩分" label="业绩分" width="100" />
        <el-table-column prop="能力分" label="能力分" width="100" />
        <el-table-column prop="态度分" label="态度分" width="100" />
        <el-table-column prop="是否特批" label="是否特批" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { exportCycleReport } from '@/api/reports'
import { listCycles } from '@/api/cycles'

const exportLoading = ref(false)
const cycles = ref([])
const reportData = ref(null)

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

async function handleExport() {
  if (!queryForm.cycle_id) {
    ElMessage.warning('请选择考核周期')
    return
  }
  exportLoading.value = true
  try {
    const res = await exportCycleReport(queryForm.cycle_id)
    reportData.value = res
    ElMessage.success(`加载成功，共 ${res.total} 条记录`)
  } catch (e) {
    console.error(e)
  } finally {
    exportLoading.value = false
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
</style>
