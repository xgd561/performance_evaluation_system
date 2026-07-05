<template>
  <div>
    <h2>上级评分列表</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="状态">
          <el-select v-model="queryForm.status" placeholder="全部状态" clearable>
            <el-option label="待上级评分" value="pending_manager" />
            <el-option label="待协作评分" value="pending_peer" />
            <el-option label="待汇总" value="pending_summary" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="queryForm.department_id" placeholder="全部部门" clearable>
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="queryForm.keyword" placeholder="姓名/工号" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="filteredList" style="width: 100%" v-loading="loading">
        <el-table-column prop="employee_name" label="姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="department_name" label="部门" />
        <el-table-column prop="position_name" label="岗位" />
        <el-table-column prop="status" label="当前状态" width="140">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ statusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="self_scores" label="自评完成时间" width="160">
          <template #default="scope">
            <span>{{ scope.row.created_at ? formatDate(scope.row.created_at) : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="manager_due_date" label="剩余截止" width="120">
          <template #default="scope">
            <span :class="dueClass(scope.row.manager_due_date)">{{ remainingDays(scope.row.manager_due_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" type="primary" @click="goToScore(scope.row)">去评分</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="mt-20"
        v-model:current-page="queryForm.page"
        v-model:page-size="queryForm.size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="handleSearch"
      />
    </el-card>
  </div>
</template>

<script>
import { getToReviewList } from '@/api/scores'
import { listDepartments } from '@/api/departments'

export default {
  name: 'ScoreSheetList',
  data() {
    return {
      loading: false,
      list: [],
      departments: [],
      total: 0,
      queryForm: {
        status: '',
        department_id: '',
        keyword: '',
        page: 1,
        size: 20,
      },
    }
  },
  computed: {
    filteredList() {
      let data = this.list
      if (this.queryForm.status) {
        data = data.filter(item => item.status === this.queryForm.status)
      }
      if (this.queryForm.department_id) {
        data = data.filter(item => item.department_id === this.queryForm.department_id)
      }
      if (this.queryForm.keyword) {
        const kw = this.queryForm.keyword.toLowerCase()
        data = data.filter(item =>
          (item.employee_name && item.employee_name.toLowerCase().includes(kw)) ||
          (item.employee_no && item.employee_no.toLowerCase().includes(kw))
        )
      }
      return data
    },
  },
  mounted() {
    this.fetchData()
    this.fetchDepartments()
  },
  methods: {
    async fetchData() {
      this.loading = true
      try {
        const res = await getToReviewList()
        this.list = res || []
        this.total = this.list.length
      } catch (e) {
        this.$message.error('加载列表失败')
      } finally {
        this.loading = false
      }
    },
    async fetchDepartments() {
      try {
        const res = await listDepartments()
        this.departments = res || []
      } catch (e) {
        console.error(e)
      }
    },
    handleSearch() {
      // 前端筛选即可
    },
    resetQuery() {
      this.queryForm = { status: '', department_id: '', keyword: '', page: 1, size: 20 }
    },
    goToScore(row) {
      this.$router.push({ name: 'ScoreSheet', query: { record_id: row.record_id } })
    },
    statusType(status) {
      const map = {
        pending_manager: 'warning',
        pending_peer: 'info',
        pending_summary: 'success',
      }
      return map[status] || ''
    },
    statusText(status) {
      const map = {
        pending_manager: '待上级评分',
        pending_peer: '待协作评分',
        pending_summary: '待汇总',
      }
      return map[status] || status
    },
    formatDate(iso) {
      if (!iso) return '—'
      const d = new Date(iso)
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    },
    remainingDays(dueDate) {
      if (!dueDate) return '—'
      const diff = new Date(dueDate) - new Date()
      const days = Math.ceil(diff / (1000 * 60 * 60 * 24))
      return days > 0 ? `${days}天` : '已逾期'
    },
    dueClass(dueDate) {
      if (!dueDate) return ''
      const diff = new Date(dueDate) - new Date()
      const days = Math.ceil(diff / (1000 * 60 * 60 * 24))
      return days < 3 ? 'text-danger' : ''
    },
  },
}
</script>

<style scoped>
.mt-20 { margin-top: 20px; }
.search-form { margin-bottom: 20px; }
.text-danger { color: #f56c6c; font-weight: bold; }
</style>
