<template>
  <div>
    <h2>申诉管理</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="状态">
          <el-select v-model="queryForm.status" placeholder="全部状态" clearable>
            <el-option label="待处理" value="pending" />
            <el-option label="已处理" value="resolved" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="appeals" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="employee_name" label="申诉人" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="reason" label="申诉理由" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ statusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reviewer_name" label="处理人" width="120">
          <template #default="scope">
            <span>{{ scope.row.reviewer_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="180">
          <template #default="scope">
            <span>{{ formatDate(scope.row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="viewDetail(scope.row)">查看</el-button>
            <el-button
              v-if="scope.row.status === 'pending'"
              size="small"
              type="primary"
              @click="goResolve(scope.row)"
            >处理</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listAppeals } from '@/api/appeals'

const router = useRouter()
const loading = ref(false)
const appeals = ref([])

const queryForm = reactive({
  status: '',
})

function statusText(status) {
  const map = { pending: '待处理', resolved: '已处理' }
  return map[status] || status
}

function statusType(status) {
  if (status === 'pending') return 'warning'
  if (status === 'resolved') return 'success'
  return 'info'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN')
}

async function loadData() {
  loading.value = true
  try {
    const res = await listAppeals({ status: queryForm.status || undefined })
    appeals.value = res || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  loadData()
}

function resetQuery() {
  queryForm.status = ''
  loadData()
}

function viewDetail(row) {
  router.push({ name: 'AppealDetail', query: { id: row.id, mode: 'view' } })
}

function goResolve(row) {
  router.push({ name: 'AppealDetail', query: { id: row.id, mode: 'resolve' } })
}

onMounted(() => {
  loadData()
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
