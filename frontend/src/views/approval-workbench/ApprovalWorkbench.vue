<template>
  <div class="approval-workbench">
    <h2>审批工作台</h2>
    <el-card>
      <el-table :data="pendingList" v-loading="loading" border>
        <el-table-column prop="employee_name" label="员工姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="cycle_name" label="考核周期" />
        <el-table-column prop="total_score" label="总分" width="100" />
        <el-table-column prop="grade" label="等级" width="80" />
        <el-table-column label="异常标记" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_abnormal" type="danger">强制调整</el-tag>
            <el-tag v-if="row.score_diff_alert" type="warning">分数差异</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300">
          <template #default="{ row }">
            <el-button type="success" size="small" @click="handleApprove(row)">通过</el-button>
            <el-button type="danger" size="small" @click="handleReject(row)">驳回</el-button>
            <el-button type="warning" size="small" @click="handleRollback(row)">打回重评</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && pendingList.length === 0" description="暂无待审批记录" />
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
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPendingApprovals, approveRecord, rejectRecord, rollbackRecord, getApprovalHistory } from '@/api/approvals'

const pendingList = ref([])
const historyList = ref([])
const loading = ref(false)
const rejectDialogVisible = ref(false)
const rollbackDialogVisible = ref(false)
const rejectReason = ref('')
const rollbackReason = ref('')
const currentRecord = ref(null)

function actionText(action) {
  const map = { approved: '通过', rejected: '驳回', rollback: '打回重评' }
  return map[action] || action
}

async function loadPending() {
  loading.value = true
  try {
    const res = await getPendingApprovals()
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

async function handleApprove(row) {
  try {
    await ElMessageBox.confirm('确认通过该员工的绩效结果？', '确认通过', { type: 'warning' })
    await approveRecord(row.record_id, { comment: 'approved' })
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
  loadPending()
  loadHistory()
})
</script>

<style scoped>
.approval-workbench { padding: 20px; }
</style>
