<template>
  <div class="approval-workbench">
    <h2>审批工作台</h2>
    <el-card>
      <!-- 筛选栏 -->
      <el-form :model="filterForm" inline class="filter-bar">
        <el-form-item label="部门">
          <el-select v-model="filterForm.department" placeholder="全部部门" clearable style="width: 160px">
            <el-option
              v-for="dept in departmentList"
              :key="dept.id"
              :label="dept.name"
              :value="dept.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="filterForm.abnormalOnly">仅显示异常分数</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="filterForm.forceAdjustOnly">仅显示强制调整</el-checkbox>
        </el-form-item>
        <el-form-item label="审批步骤">
          <el-radio-group v-model="filterForm.step">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="step1">Step 1 待审批</el-radio-button>
            <el-radio-button label="step2">Step 2 待审批</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="filteredList" v-loading="loading" border :row-class-name="rowClassName">
        <el-table-column prop="employee_name" label="员工姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="department_name" label="部门" width="120" />
        <el-table-column prop="cycle_name" label="考核周期" />
        <el-table-column prop="total_score" label="总分" width="100" />
        <el-table-column prop="grade" label="等级" width="80" />
        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="Step 标签" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.next_approver_role === firstChainRole" type="info">Step 1 待审批</el-tag>
            <el-tag v-else-if="row.next_approver_role === secondChainRole" type="warning">Step 2 待审批</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="异常标记" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_abnormal" type="danger">强制调整</el-tag>
            <el-tag v-if="row.score_diff_alert" type="warning">分数差异</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="380">
          <template #default="{ row }">
            <el-button type="success" size="small" @click="handleApprove(row)">通过</el-button>
            <el-button type="danger" size="small" @click="handleReject(row)">驳回</el-button>
            <el-button type="warning" size="small" @click="handleRollback(row)">打回重评</el-button>
            <el-button type="primary" size="small" @click="goToDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && filteredList.length === 0" description="暂无待审批记录" />
    </el-card>

    <!-- 审批历史 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <span>审批历史</span>
      </template>
      <el-timeline v-if="historyList.length > 0">
        <el-timeline-item
          v-for="item in historyList"
          :key="item.id"
          :type="item.action === 'approved' ? 'success' : item.action === 'rejected' ? 'danger' : 'warning'"
        >
          {{ item.approver_name }} - {{ actionText(item.action) }}
          <p v-if="item.comment">{{ item.comment }}</p>
          <span style="color: #909399; font-size: 12px">{{ item.created_at }}</span>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无审批历史" />
    </el-card>

    <!-- 驳回对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回理由" width="400px">
      <el-input v-model="rejectReason" type="textarea" placeholder="请输入驳回理由" />
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 打回重评对话框 -->
    <el-dialog v-model="rollbackDialogVisible" title="打回重评理由" width="400px">
      <el-input v-model="rollbackReason" type="textarea" placeholder="请输入打回重评理由" />
      <template #footer>
        <el-button @click="rollbackDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRollback">确认打回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPendingApprovals, approveRecord, rejectRecord, rollbackRecord, getApprovalHistory } from '@/api/approvals'
import { listDepartments } from '@/api/departments'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const pendingList = ref([])
const historyList = ref([])
const loading = ref(false)
const rejectDialogVisible = ref(false)
const rollbackDialogVisible = ref(false)
const rejectReason = ref('')
const rollbackReason = ref('')
const currentRecord = ref(null)
const departmentList = ref([])

const filterForm = ref({
  department: '',
  abnormalOnly: false,
  forceAdjustOnly: false,
  step: '',
})

const firstChainRole = ref('direct_manager')
const secondChainRole = ref('dept_head')

const currentRole = computed(() => authStore.role || '')

function actionText(action) {
  const map = { approved: '通过', rejected: '驳回', rollback: '打回重评' }
  return map[action] || action
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function loadDepartments() {
  try {
    const res = await listDepartments()
    departmentList.value = res || []
  } catch (e) {
    // 静默失败，不影响主功能
  }
}

async function loadPending() {
  loading.value = true
  try {
    const params = {}
    if (filterForm.value.department) {
      params.department = filterForm.value.department
    }
    if (filterForm.value.abnormalOnly) {
      params.abnormal = true
    }
    if (filterForm.value.forceAdjustOnly) {
      params.force_adjust = true
    }
    if (filterForm.value.step) {
      const stepMap = { step1: 1, step2: 2 }
      params.step = stepMap[filterForm.value.step] || filterForm.value.step
    }
    const res = await getPendingApprovals(params)
    pendingList.value = res || []
  } catch (e) {
    ElMessage.error('加载待审批列表失败')
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    const res = await getApprovalHistory()
    historyList.value = res || []
  } catch (e) {
    ElMessage.error('加载审批历史失败')
  }
}

const filteredList = computed(() => {
  let list = pendingList.value

  // 角色过滤：manager 默认只显示 Step 1（除非显式选了 step2）
  if (currentRole.value === 'manager') {
    const step = filterForm.value.step
    if (!step || step === 'step1') {
      list = list.filter(r => r.next_approver_role === firstChainRole.value)
    } else if (step === 'step2') {
      list = list.filter(r => r.next_approver_role === secondChainRole.value)
    }
  } else {
    if (filterForm.value.step === 'step1') {
      list = list.filter(r => r.next_approver_role === firstChainRole.value)
    } else if (filterForm.value.step === 'step2') {
      list = list.filter(r => r.next_approver_role === secondChainRole.value)
    }
  }

  if (filterForm.value.department) {
    list = list.filter(r => r.department_name === filterForm.value.department)
  }
  if (filterForm.value.abnormalOnly) {
    list = list.filter(r => r.score_diff_alert)
  }
  if (filterForm.value.forceAdjustOnly) {
    list = list.filter(r => r.is_abnormal)
  }
  return list
})

function rowClassName({ row }) {
  if (row.is_abnormal) {
    return 'force-adjust-row'
  }
  return ''
}

function handleFilter() {
  loadPending()
}

function handleReset() {
  filterForm.value = {
    department: '',
    abnormalOnly: false,
    forceAdjustOnly: false,
    step: currentRole.value === 'manager' ? 'step1' : '',
  }
  loadPending()
}

function goToDetail(row) {
  router.push({ name: 'ApprovalDetail', query: { record_id: row.record_id } })
}

async function handleApprove(row) {
  try {
    await ElMessageBox.confirm('确认通过该员工的绩效结果？', '确认通过', { type: 'warning' })
    await approveRecord(row.record_id, { comment: '审批通过，同意该员工的绩效结果。' })
    ElMessage.success('审批通过')
    loadPending()
    loadHistory()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.message || '操作失败')
  }
}

function handleReject(row) {
  currentRecord.value = row
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  if (!rejectReason.value.trim()) {
    ElMessage.warning('请输入驳回理由')
    return
  }
  try {
    await rejectRecord(currentRecord.value.record_id, { reason: rejectReason.value })
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    loadPending()
    loadHistory()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  }
}

function handleRollback(row) {
  currentRecord.value = row
  rollbackReason.value = ''
  rollbackDialogVisible.value = true
}

async function confirmRollback() {
  if (!rollbackReason.value.trim()) {
    ElMessage.warning('请输入打回重评理由')
    return
  }
  try {
    await rollbackRecord(currentRecord.value.record_id, { reason: rollbackReason.value })
    ElMessage.success('已打回重评')
    rollbackDialogVisible.value = false
    loadPending()
    loadHistory()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  }
}

onMounted(() => {
  // manager 默认只看 Step 1
  if (currentRole.value === 'manager') {
    filterForm.value.step = 'step1'
  }
  loadDepartments()
  loadPending()
  loadHistory()
})
</script>

<style scoped>
.approval-workbench { padding: 20px; }
.filter-bar { margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #ebeef5; }
:deep(.force-adjust-row) { background-color: #fdf6ec; }
</style>
