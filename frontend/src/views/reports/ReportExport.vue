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
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { exportCycleReportExcel } from '@/api/reports'
import { listCycles } from '@/api/cycles'

const exportLoading = ref(false)
const cycles = ref([])

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
    const res = await exportCycleReportExcel(queryForm.cycle_id)
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const contentDisposition = res.headers['content-disposition']
    let filename = '考核结果.xlsx'
    if (contentDisposition) {
      const filenameStar = contentDisposition.match(/filename\*=UTF-8''(.+)/)
      if (filenameStar && filenameStar[1]) {
        filename = decodeURIComponent(filenameStar[1])
      } else {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1]
        }
      }
    }
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    console.error(e)
    ElMessage.error('导出失败')
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
