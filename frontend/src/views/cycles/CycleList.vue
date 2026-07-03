<template>
  <div>
    <h2>考核周期管理</h2>
    <el-card class="mt-20">
      <div class="toolbar">
        <el-button type="primary" @click="openDialog">新增周期</el-button>
      </div>
      <el-table :data="cycles" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="scope">
            <el-tag>{{ scope.row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120" />
        <el-table-column prop="self_due_date" label="自评截止" width="120">
          <template #default="scope">
            <span>{{ scope.row.self_due_date || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="manager_due_date" label="上级评截止" width="120">
          <template #default="scope">
            <span>{{ scope.row.manager_due_date || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="peer_due_date" label="协作评截止" width="120">
          <template #default="scope">
            <span>{{ scope.row.peer_due_date || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ statusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="scope">
            <el-button size="small" v-if="scope.row.status === 'not_started'" @click="editCycle(scope.row)">编辑</el-button>
            <el-button size="small" type="success" v-if="scope.row.status === 'not_started'" @click="openLaunchDialog(scope.row)">发起</el-button>
            <el-button size="small" type="primary" v-if="scope.row.status !== 'archived'" @click="openPeerDialog(scope.row)">协作人</el-button>
            <el-button size="small" type="warning" v-if="canPublish(scope.row.status)" @click="handlePublish(scope.row)">发布结果</el-button>
            <el-button size="small" @click="viewProgress(scope.row)">进度</el-button>
            <el-button size="small" type="danger" v-if="scope.row.status === 'not_started'" @click="removeCycle(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Add/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑周期' : '新增周期'" width="550px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="form.type">
            <el-option label="月度" value="monthly" />
            <el-option label="季度" value="quarterly" />
            <el-option label="年度" value="annual" />
          </el-select>
        </el-form-item>
        <el-form-item label="考核时间" prop="dateRange">
          <el-date-picker v-model="form.dateRange" type="daterange" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="自评截止日期">
          <el-date-picker v-model="form.self_due_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="上级评截止日期">
          <el-date-picker v-model="form.manager_due_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="协作评截止日期">
          <el-date-picker v-model="form.peer_due_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- Launch Dialog -->
    <el-dialog v-model="launchDialogVisible" title="发起考核" width="500px">
      <p>选择参与考核的员工：</p>
      <el-transfer v-model="selectedEmployees" :data="employeeOptions" :titles="['全部员工', '已选']" filterable />
      <template #footer>
        <el-button @click="launchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitLaunch" :loading="launchLoading">确定发起</el-button>
      </template>
    </el-dialog>

    <!-- Progress Dialog -->
    <el-dialog v-model="progressDialogVisible" title="考核进度" width="500px">
      <div v-if="progress">
        <p>状态：{{ statusText(progress.status) }}</p>
        <p>总员工：{{ progress.total_employees }}，已完成：{{ progress.completed }}</p>
        <el-progress :percentage="progress.overall_progress" />
        <el-timeline class="mt-20">
          <el-timeline-item v-for="s in progress.stages" :key="s.name" :type="s.status === 'completed' ? 'success' : 'warning'">
            {{ s.name }} — {{ s.status === 'completed' ? '已完成' : '进行中' }}
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>

    <!-- Peer Reviewer Dialog -->
    <el-dialog v-model="peerDialogVisible" :title="`分配协作人 - ${peerCycleName}`" width="750px">
      <div v-if="peerLoading" class="loading-wrap">
        <el-skeleton :rows="6" animated />
      </div>
      <div v-else>
        <el-alert type="info" :closable="false" show-icon class="mb-12">
          <template #title>为每个参与员工选择协作评分人，协作人可查看该员工的自评和上级评分并进行协作评价。</template>
        </el-alert>
        <el-table :data="cycleEmployees" style="width: 100%" size="small">
          <el-table-column prop="name" label="员工" width="100" />
          <el-table-column prop="department_name" label="部门" width="120" />
          <el-table-column label="已分配协作人" min-width="180">
            <template #default="{ row }">
              <div class="peer-tags">
                <el-tag
                  v-for="p in getEmployeePeers(row.employee_id)"
                  :key="p.id"
                  closable
                  @close="handleRemovePeer(p.id)"
                  type="success"
                  size="small"
                  class="peer-tag"
                >
                  {{ p.peer_name }}
                </el-tag>
                <span v-if="getEmployeePeers(row.employee_id).length === 0" class="empty-text">未分配</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="添加协作人" width="220">
            <template #default="{ row }">
              <div class="add-peer-row">
                <el-select v-model="row._selectedPeer" size="small" placeholder="选择" style="width: 140px" clearable filterable>
                  <el-option
                    v-for="opt in getAvailablePeers(row.employee_id)"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
                <el-button size="small" type="primary" @click="handleAddPeer(row)">添加</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listCycles, createCycle, updateCycle, deleteCycle, launchCycle, getCycleProgress, publishCycle, listCycleEmployees } from '@/api/cycles'
import { listEmployees } from '@/api/employees'
import { listPeersByCycle, assignPeer, removePeer } from '@/api/peers'

const loading = ref(false)
const cycles = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({
  id: null,
  name: '',
  type: 'monthly',
  start_date: '',
  end_date: '',
  self_due_date: '',
  manager_due_date: '',
  peer_due_date: '',
  dateRange: [],
})
const formRef = ref(null)
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  dateRange: [{ required: true, message: '请选择考核时间', trigger: 'change', type: 'array' }],
}

const launchDialogVisible = ref(false)
const launchLoading = ref(false)
const selectedEmployees = ref([])
const employeeOptions = ref([])
const currentCycleId = ref(null)

const progressDialogVisible = ref(false)
const progress = ref(null)

// 协作人分配
const peerDialogVisible = ref(false)
const peerLoading = ref(false)
const peerCycleId = ref(null)
const peerCycleName = ref('')
const cycleEmployees = ref([])
const peerRelations = ref([])
const peerEmployeeOptions = ref([])

function statusText(status) {
  const map = {
    not_started: '未开始',
    pending_self: '自评中',
    pending_manager: '上级评中',
    pending_peer: '协作评中',
    pending_summary: '汇总中',
    pending_approval: '审批中',
    pending_interview: '待发布',
    published: '已发布',
    archived: '已归档',
  }
  return map[status] || status
}

function statusType(status) {
  if (status === 'not_started') return 'info'
  if (status === 'pending_self') return 'primary'
  if (status === 'pending_manager' || status === 'pending_peer') return 'warning'
  if (status === 'pending_summary' || status === 'pending_approval') return 'warning'
  if (status === 'pending_interview') return 'warning'
  if (status === 'published' || status === 'archived') return 'success'
  return 'info'
}

function canPublish(status) {
  return ['pending_self', 'pending_manager', 'pending_peer', 'pending_summary', 'pending_approval', 'pending_interview'].includes(status)
}

async function handlePublish(row) {
  try {
    await ElMessageBox.confirm(`确认发布考核周期 ${row.name} 的结果？发布后员工将可查看自己的考核结果。`, '提示', { type: 'warning' })
    await publishCycle(row.id)
    ElMessage.success('发布成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error(e?.response?.data?.message || '发布失败')
    }
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await listCycles()
    console.log('[DEBUG] listCycles response:', res)
    if (res && res.length > 0) {
      console.log('[DEBUG] first item fields:', Object.keys(res[0]))
      console.log('[DEBUG] first item self_due_date:', res[0].self_due_date)
      console.log('[DEBUG] first item manager_due_date:', res[0].manager_due_date)
      console.log('[DEBUG] first item peer_due_date:', res[0].peer_due_date)
    }
    cycles.value = res || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function openDialog() {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', type: 'monthly', start_date: '', end_date: '', self_due_date: '', manager_due_date: '', peer_due_date: '', dateRange: [] })
  dialogVisible.value = true
}

function editCycle(row) {
  isEdit.value = true
  Object.assign(form, {
    id: row.id,
    name: row.name,
    type: row.type,
    start_date: row.start_date,
    end_date: row.end_date,
    self_due_date: row.self_due_date || '',
    manager_due_date: row.manager_due_date || '',
    peer_due_date: row.peer_due_date || '',
    dateRange: [row.start_date, row.end_date],
  })
  console.log('[DEBUG] editCycle form:', JSON.parse(JSON.stringify(form)))
  dialogVisible.value = true
}

async function submitForm() {
  try {
    await formRef.value.validate()
    const payload = {
      name: form.name,
      type: form.type,
      start_date: form.dateRange?.[0] || '',
      end_date: form.dateRange?.[1] || '',
      self_due_date: form.self_due_date || null,
      manager_due_date: form.manager_due_date || null,
      peer_due_date: form.peer_due_date || null,
      weights: { self: 30, manager: 50, peer: 20 },
      grade_rules: { A: 90, B: 80, C: 60, D: 0 },
    }
    console.log('[DEBUG] submitForm payload:', payload)
    if (isEdit.value) {
      const updateRes = await updateCycle(form.id, payload)
      console.log('[DEBUG] updateCycle response:', updateRes)
      ElMessage.success('更新成功')
    } else {
      const createRes = await createCycle(payload)
      console.log('[DEBUG] createCycle response:', createRes)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    console.error(e)
  }
}

async function removeCycle(row) {
  try {
    await ElMessageBox.confirm(`确认删除考核周期 ${row.name}？`, '提示', { type: 'warning' })
    await deleteCycle(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

async function openLaunchDialog(row) {
  currentCycleId.value = row.id
  try {
    const res = await listEmployees({ page: 1, size: 100 })
    const items = res.items || []
    employeeOptions.value = items.map(emp => ({ key: emp.id, label: `${emp.name} (${emp.employee_no})` }))
    selectedEmployees.value = []
    launchDialogVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

async function submitLaunch() {
  if (!selectedEmployees.value.length) {
    ElMessage.warning('请选择至少一名员工')
    return
  }
  launchLoading.value = true
  try {
    await launchCycle({ cycle_id: currentCycleId.value, employee_ids: selectedEmployees.value })
    ElMessage.success('发起成功')
    launchDialogVisible.value = false
    loadData()
  } catch (e) {
    console.error(e)
  } finally {
    launchLoading.value = false
  }
}

async function viewProgress(row) {
  try {
    const res = await getCycleProgress(row.id)
    progress.value = res
    progressDialogVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

// 协作人分配
async function openPeerDialog(row) {
  peerCycleId.value = row.id
  peerCycleName.value = row.name
  peerDialogVisible.value = true
  await loadPeerData()
}

async function loadPeerData() {
  peerLoading.value = true
  try {
    const [empRes, peerRes, allEmpRes] = await Promise.all([
      listCycleEmployees(peerCycleId.value),
      listPeersByCycle(peerCycleId.value),
      listEmployees({ page: 1, size: 100 }),
    ])
    cycleEmployees.value = (empRes || []).map(emp => ({ ...emp, _selectedPeer: null }))
    peerRelations.value = peerRes || []
    const items = allEmpRes.items || []
    peerEmployeeOptions.value = items.map(emp => ({ value: emp.id, label: `${emp.name} (${emp.employee_no})` }))
  } catch (e) {
    console.error(e)
    ElMessage.error('加载协作人数据失败')
  } finally {
    peerLoading.value = false
  }
}

function getEmployeePeers(employeeId) {
  return peerRelations.value.filter(p => p.employee_id === employeeId)
}

function getAvailablePeers(employeeId) {
  const existingPeerIds = new Set(getEmployeePeers(employeeId).map(p => p.peer_id))
  return peerEmployeeOptions.value.filter(opt => opt.value !== employeeId && !existingPeerIds.has(opt.value))
}

async function handleAddPeer(employee) {
  const peerId = employee._selectedPeer
  if (!peerId) {
    ElMessage.warning('请选择协作人')
    return
  }
  try {
    await assignPeer({ cycle_id: peerCycleId.value, employee_id: employee.employee_id, peer_id: peerId })
    ElMessage.success('分配成功')
    employee._selectedPeer = null
    await loadPeerData()
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.message || '分配失败')
  }
}

async function handleRemovePeer(relationId) {
  try {
    await ElMessageBox.confirm('确认移除该协作人？', '提示', { type: 'warning' })
    await removePeer(relationId)
    ElMessage.success('移除成功')
    await loadPeerData()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
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
.toolbar {
  margin-bottom: 16px;
}
.loading-wrap {
  padding: 24px;
}
.mb-12 {
  margin-bottom: 12px;
}
.peer-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.peer-tag {
  margin-right: 0;
}
.empty-text {
  color: #909399;
  font-size: 12px;
}
.add-peer-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
