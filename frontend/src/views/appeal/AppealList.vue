<template>
  <div>
    <h2>申诉管理</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="状态">
          <el-select v-model="queryForm.status" placeholder="全部状态" clearable>
            <el-option label="待处理" value="pending" />
            <el-option label="已通过" value="resolved" />
            <el-option label="已驳回" value="rejected" />
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
            <el-button size="small" type="success" v-if="scope.row.status === 'pending'" @click="openReviewDialog(scope.row, 'approve')">通过</el-button>
            <el-button size="small" type="danger" v-if="scope.row.status === 'pending'" @click="openReviewDialog(scope.row, 'reject')">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="申诉详情" width="500px">
      <div v-if="currentAppeal">
        <p><strong>申诉人：</strong>{{ currentAppeal.employee_name }}（{{ currentAppeal.employee_no }}）</p>
        <p><strong>申诉理由：</strong>{{ currentAppeal.reason }}</p>
        <p><strong>详细说明：</strong>{{ currentAppeal.detail || '无' }}</p>
        <p><strong>状态：</strong>{{ statusText(currentAppeal.status) }}</p>
        <p><strong>考核总分：</strong>{{ currentAppeal.record?.total_score || '—' }}</p>
        <p><strong>考核等级：</strong>{{ currentAppeal.record?.grade || '—' }}</p>
        <p v-if="currentAppeal.review_result"><strong>处理结果：</strong>{{ currentAppeal.review_result }}</p>
        <p v-if="currentAppeal.reviewer_name"><strong>处理人：</strong>{{ currentAppeal.reviewer_name }}</p>
        <p v-if="currentAppeal.resolved_at"><strong>处理时间：</strong>{{ formatDate(currentAppeal.resolved_at) }}</p>
      </div>
    </el-dialog>

    <!-- Review Dialog -->
    <el-dialog v-model="reviewVisible" :title="reviewAction === 'approve' ? '通过申诉' : '驳回申诉'" width="500px">
      <el-form :model="reviewForm" ref="reviewFormRef">
        <el-form-item label="处理意见" prop="review_result" :rules="[{ required: true, message: '请输入处理意见', trigger: 'blur' }]">
          <el-input v-model="reviewForm.review_result" type="textarea" rows="4" placeholder="请输入处理意见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReview" :loading="reviewLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listAppeals, getAppeal, reviewAppeal } from '@/api/appeals'

const loading = ref(false)
const appeals = ref([])
const detailVisible = ref(false)
const reviewVisible = ref(false)
const reviewLoading = ref(false)
const currentAppeal = ref(null)
const reviewAction = ref('approve')
const reviewFormRef = ref(null)

const queryForm = reactive({
  status: '',
})

const reviewForm = reactive({
  review_result: '',
})

function statusText(status) {
  const map = {
    pending: '待处理',
    resolved: '已通过',
    rejected: '已驳回',
  }
  return map[status] || status
}

function statusType(status) {
  if (status === 'pending') return 'warning'
  if (status === 'resolved') return 'success'
  if (status === 'rejected') return 'danger'
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

async function viewDetail(row) {
  try {
    const res = await getAppeal(row.id)
    currentAppeal.value = res
    detailVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

function openReviewDialog(row, action) {
  currentAppeal.value = row
  reviewAction.value = action
  reviewForm.review_result = ''
  reviewVisible.value = true
}

async function submitReview() {
  try {
    await reviewFormRef.value.validate()
    reviewLoading.value = true
    await reviewAppeal(currentAppeal.value.id, {
      action: reviewAction.value,
      review_result: reviewForm.review_result,
    })
    ElMessage.success(reviewAction.value === 'approve' ? '已通过申诉' : '已驳回申诉')
    reviewVisible.value = false
    loadData()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  } finally {
    reviewLoading.value = false
  }
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
