<template>
  <div class="interview-list">
    <h2>绩效面谈</h2>

    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="搜索">
          <el-input
            v-model="queryForm.keyword"
            placeholder="姓名/工号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 待面谈 -->
    <el-card class="mt-20">
      <template #header>
        <div class="card-header">
          <span>待面谈</span>
          <el-tag v-if="pendingList.length > 0" type="warning">{{ pendingList.length }}</el-tag>
        </div>
      </template>
      <el-table
        :data="pendingList"
        v-loading="loading"
        border
        :row-class-name="rowClassName"
        @row-click="handleRowClick"
        style="cursor: pointer"
      >
        <el-table-column prop="employee_name" label="员工姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="department_name" label="部门" />
        <el-table-column prop="position_name" label="岗位" />
        <el-table-column prop="cycle_name" label="考核周期" />
        <el-table-column prop="total_score" label="总分" width="100" />
        <el-table-column prop="grade" label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="gradeTagType(row.grade)">{{ row.grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click.stop="goToForm(row)">
              进入面谈
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && pendingList.length === 0" description="暂无待面谈记录" />
    </el-card>

    <!-- 已面谈 -->
    <el-card class="mt-20">
      <template #header>
        <div class="card-header">
          <span>已面谈</span>
          <el-tag v-if="completedList.length > 0" type="success">{{ completedList.length }}</el-tag>
        </div>
      </template>
      <el-table
        :data="completedList"
        v-loading="loading"
        border
        :row-class-name="rowClassName"
        @row-click="handleRowClick"
        style="cursor: pointer"
      >
        <el-table-column prop="employee_name" label="员工姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="department_name" label="部门" />
        <el-table-column prop="position_name" label="岗位" />
        <el-table-column prop="cycle_name" label="考核周期" />
        <el-table-column prop="total_score" label="总分" width="100" />
        <el-table-column prop="grade" label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="gradeTagType(row.grade)">{{ row.grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="info" size="small" @click.stop="goToForm(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && completedList.length === 0" description="暂无已面谈记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getManagerInterviewList } from '@/api/interviews'

const router = useRouter()
const loading = ref(false)
const pendingList = ref([])
const completedList = ref([])
const queryForm = ref({ keyword: '' })

async function loadData() {
  loading.value = true
  try {
    const res = await getManagerInterviewList(queryForm.value.keyword)
    pendingList.value = res.pending || []
    completedList.value = res.completed || []
  } catch (e) {
    ElMessage.error('加载面谈列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  loadData()
}

function resetQuery() {
  queryForm.value.keyword = ''
  loadData()
}

function gradeTagType(grade) {
  if (grade === 'C' || grade === 'D') return 'danger'
  const map = { A: 'success', B: 'primary' }
  return map[grade] || ''
}

function rowClassName({ row }) {
  if (row.grade === 'C' || row.grade === 'D') {
    return 'highlight-cd'
  }
  return ''
}

function goToForm(row) {
  router.push({ name: 'InterviewForm', query: { record_id: row.record_id } })
}

function handleRowClick(row) {
  goToForm(row)
}

onMounted(loadData)
</script>

<style scoped>
.interview-list { padding: 20px; }
.search-card { margin-bottom: 20px; }
.mt-20 { margin-top: 20px; }
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: bold;
}
:deep(.highlight-cd) {
  background-color: #fef0f0 !important;
}
</style>
