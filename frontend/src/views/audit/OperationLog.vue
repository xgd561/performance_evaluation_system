<template>
  <div>
    <h2>操作日志审计</h2>

    <el-card class="mt-20">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="操作类型">
          <el-select v-model="filters.action" placeholder="全部" clearable>
            <el-option
              v-for="act in actionOptions"
              :key="act"
              :label="act"
              :value="act"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标类型">
          <el-input v-model="filters.target_type" placeholder="如 assessment_cycle" clearable />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="filters.start_date" type="date" placeholder="选择开始日期" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="filters.end_date" type="date" placeholder="选择结束日期" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="logs" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="操作用户" width="120" />
        <el-table-column prop="action" label="操作类型" width="150" />
        <el-table-column prop="target_type" label="目标类型" width="130" />
        <el-table-column prop="target_id" label="目标ID" width="90" />
        <el-table-column label="变更内容" min-width="200">
          <template #default="{ row }">
            <div v-if="row.old_value || row.new_value">
              <div v-if="row.old_value"><strong>旧值:</strong> {{ formatJson(row.old_value) }}</div>
              <div v-if="row.new_value"><strong>新值:</strong> {{ formatJson(row.new_value) }}</div>
            </div>
            <span v-else class="empty">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="130" />
        <el-table-column prop="created_at" label="操作时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="mt-20"
        background
        layout="total, sizes, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getLogs, getLogActions } from '@/api/logs'

const loading = ref(false)
const logs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const actionOptions = ref([])

const filters = reactive({
  action: '',
  target_type: '',
  start_date: '',
  end_date: '',
})

async function loadActions() {
  try {
    const res = await getLogActions()
    if (Array.isArray(res)) {
      actionOptions.value = res
    } else if (res && Array.isArray(res.data)) {
      actionOptions.value = res.data
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadLogs() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      size: pageSize.value,
    }
    if (filters.action) params.action = filters.action
    if (filters.target_type) params.target_type = filters.target_type
    if (filters.start_date) params.start_date = filters.start_date
    if (filters.end_date) params.end_date = filters.end_date

    const res = await getLogs(params)
    if (res && res.items) {
      logs.value = res.items
      total.value = res.total
    } else if (res && res.data && res.data.items) {
      logs.value = res.data.items
      total.value = res.data.total
    }
  } catch (e) {
    ElMessage.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadLogs()
}

function handleReset() {
  filters.action = ''
  filters.target_type = ''
  filters.start_date = ''
  filters.end_date = ''
  page.value = 1
  loadLogs()
}

function handlePageChange(newPage) {
  page.value = newPage
  loadLogs()
}

function handleSizeChange(newSize) {
  pageSize.value = newSize
  page.value = 1
  loadLogs()
}

function formatJson(val) {
  if (!val) return '-'
  try {
    const obj = JSON.parse(val)
    return JSON.stringify(obj).slice(0, 100)
  } catch {
    return String(val).slice(0, 100)
  }
}

function formatDate(val) {
  if (!val) return '-'
  const d = new Date(val)
  if (isNaN(d.getTime())) return val
  return d.toLocaleString('zh-CN')
}

onMounted(() => {
  loadActions()
  loadLogs()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.filter-form {
  margin-bottom: 20px;
}
.empty {
  color: #909399;
}
</style>
