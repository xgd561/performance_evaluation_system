<template>
  <div>
    <h2>报表导出</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="考核周期">
          <el-select v-model="queryForm.cycle_id" placeholder="选择周期" clearable style="width: 240px">
            <el-option v-for="c in cycles" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select
            v-model="queryForm.department_ids"
            multiple
            collapse-tags
            placeholder="选择部门（可多选）"
            clearable
            style="width: 280px"
          >
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="导出格式">
          <el-radio-group v-model="queryForm.format">
            <el-radio-button label="excel">Excel</el-radio-button>
            <el-radio-button label="pdf">PDF</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="handleExport"
            :loading="exportLoading"
            :disabled="!queryForm.cycle_id"
          >
            导出
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 进度条 -->
      <el-progress
        v-if="showProgress"
        :percentage="progressPercent"
        :status="progressStatus"
        :stroke-width="18"
        class="mt-10"
      />
    </el-card>

    <!-- 历史导出记录 -->
    <el-card class="mt-20" title="历史导出记录">
      <template #header>
        <span>历史导出记录</span>
      </template>
      <el-table :data="exportHistory" style="width: 100%">
        <el-table-column prop="filename" label="文件名" min-width="200" />
        <el-table-column prop="format" label="格式" width="80">
          <template #default="{ row }">
            <el-tag :type="row.format === 'excel' ? 'success' : 'warning'">{{ row.format === 'excel' ? 'Excel' : 'PDF' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="导出时间" width="180" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button v-if="row.status === 'success'" type="primary" link @click="downloadAgain(row)">
              重新下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="exportHistory.length === 0" description="暂无导出记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { exportCycleReportExcel, exportCycleReportPdf } from '@/api/reports'
import { listCycles } from '@/api/cycles'
import { listDepartments } from '@/api/departments'

const exportLoading = ref(false)
const cycles = ref([])
const departments = ref([])
const showProgress = ref(false)
const progressPercent = ref(0)
const progressStatus = ref('')

const queryForm = reactive({
  cycle_id: null,
  department_ids: [],
  format: 'excel',
})

const exportHistory = ref([])

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
    departments.value = res || []
  } catch (e) {
    console.error(e)
  }
}

function statusType(status) {
  const map = { success: 'success', pending: 'info', failed: 'danger' }
  return map[status] || 'info'
}

function statusText(status) {
  const map = { success: '成功', pending: '进行中', failed: '失败' }
  return map[status] || status
}

async function handleExport() {
  if (!queryForm.cycle_id) {
    ElMessage.warning('请选择考核周期')
    return
  }
  exportLoading.value = true
  showProgress.value = true
  progressPercent.value = 0
  progressStatus.value = ''

  // 模拟进度条
  const timer = setInterval(() => {
    if (progressPercent.value < 90) {
      progressPercent.value += Math.floor(Math.random() * 10) + 5
      if (progressPercent.value > 90) progressPercent.value = 90
    }
  }, 300)

  try {
    let res
    if (queryForm.format === 'excel') {
      res = await exportCycleReportExcel(queryForm.cycle_id, queryForm.department_ids)
    } else {
      res = await exportCycleReportPdf(queryForm.cycle_id, queryForm.department_ids)
    }

    const blob = new Blob([res.data], {
      type: queryForm.format === 'excel'
        ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        : 'application/pdf'
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    const contentDisposition = res.headers['content-disposition']
    let filename = queryForm.format === 'excel' ? '考核结果.xlsx' : '考核档案.pdf'
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

    clearInterval(timer)
    progressPercent.value = 100
    progressStatus.value = 'success'
    ElMessage.success('导出成功')

    // 添加到历史记录
    exportHistory.value.unshift({
      filename,
      format: queryForm.format,
      created_at: new Date().toLocaleString(),
      status: 'success',
      url,
    })
  } catch (e) {
    clearInterval(timer)
    progressPercent.value = 100
    progressStatus.value = 'exception'
    console.error(e)
    ElMessage.error('导出失败')
    exportHistory.value.unshift({
      filename: queryForm.format === 'excel' ? '考核结果.xlsx' : '考核档案.pdf',
      format: queryForm.format,
      created_at: new Date().toLocaleString(),
      status: 'failed',
    })
  } finally {
    exportLoading.value = false
    setTimeout(() => {
      showProgress.value = false
    }, 2000)
  }
}

function downloadAgain(row) {
  if (row.url) {
    const link = document.createElement('a')
    link.href = row.url
    link.download = row.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
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
.mt-10 {
  margin-top: 10px;
}
.search-form {
  margin-bottom: 16px;
}
</style>
