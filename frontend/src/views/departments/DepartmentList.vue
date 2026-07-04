<template>
  <div>
    <h2>部门管理</h2>

    <!-- 简化版部门架构图 -->
    <el-card class="mt-20 org-chart-card">
      <template #header>
        <div class="card-header">
          <span>组织架构图</span>
          <el-tag size="small" type="info">可拖拽调整部门归属</el-tag>
        </div>
      </template>
      <el-tree
        v-if="treeData.length > 0"
        :data="treeData"
        :props="{ label: 'name', children: 'children' }"
        :expand-on-click-node="false"
        :draggable="true"
        :allow-drag="allowDrag"
        :allow-drop="allowDrop"
        @node-drop="handleDrop"
        node-key="id"
        default-expand-all
        highlight-current
      >
        <template #default="{ node, data }">
          <span class="tree-node">
            <el-icon class="tree-icon"><OfficeBuilding /></el-icon>
            <span class="tree-label">{{ data.name }}</span>
            <el-tag v-if="data.code" size="small" type="info" class="tree-tag">{{ data.code }}</el-tag>
            <el-tag v-if="data.employee_count" size="small" type="success" class="tree-tag">{{ data.employee_count }}人</el-tag>
          </span>
        </template>
      </el-tree>
      <el-empty v-else description="暂无部门数据" />
    </el-card>

    <!-- 树形表格 -->
    <el-card class="mt-20">
      <template #header>
        <div class="card-header">
          <span>部门列表</span>
          <el-button type="primary" @click="openDeptDialog">新增部门</el-button>
        </div>
      </template>

      <el-table
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        default-expand-all
        border
      >
        <el-table-column prop="code" label="编码" width="120" />
        <el-table-column prop="name" label="名称" min-width="160">
          <template #default="scope">
            <span :style="{ paddingLeft: scope.row.level ? (scope.row.level * 16) + 'px' : '0' }">
              {{ scope.row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="parent_name" label="上级部门" width="140">
          <template #default="scope">
            <span>{{ scope.row.parent_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="head_name" label="负责人" width="120">
          <template #default="scope">
            <span>{{ scope.row.head_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="employee_count" label="员工数" width="90" align="center" />
        <el-table-column prop="position_count" label="岗位数" width="90" align="center" />
        <el-table-column label="操作" width="280" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="editDept(scope.row)">编辑</el-button>
            <el-button size="small" type="primary" @click="managePositions(scope.row)">管理岗位</el-button>
            <el-button size="small" type="danger" @click="deleteDept(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Dept Dialog -->
    <el-dialog v-model="deptDialogVisible" :title="isEdit ? '编辑部门' : '新增部门'" width="500px">
      <el-form :model="deptForm" :rules="deptRules" ref="deptFormRef" label-width="120px">
        <el-form-item label="编码" prop="code">
          <el-input v-model="deptForm.code" placeholder="如 TECH, HR" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="deptForm.name" placeholder="如 技术部" />
        </el-form-item>
        <el-form-item label="上级部门">
          <el-tree-select
            v-model="deptForm.parent_id"
            :data="treeSelectData"
            :render-after-expand="false"
            check-strictly
            clearable
            placeholder="无（一级部门）"
            style="width: 100%"
            :props="{ label: 'name', value: 'id', children: 'children' }"
          />
        </el-form-item>
        <el-form-item label="部门负责人">
          <el-select
            v-model="deptForm.head_id"
            placeholder="选择负责人"
            clearable
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="emp in managerList"
              :key="emp.id"
              :label="`${emp.name} (${emp.employee_no})`"
              :value="emp.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deptDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitDept">确定</el-button>
      </template>
    </el-dialog>

    <!-- Position Dialog -->
    <el-dialog v-model="posDialogVisible" :title="`${currentDept?.name || ''} — 岗位管理`" width="650px">
      <el-alert
        v-if="currentDept"
        :title="`当前部门：${currentDept.name}（编码：${currentDept.code || '—'}）`"
        type="info"
        :closable="false"
        class="mb-16"
      />

      <el-divider content-position="left">{{ isPosEdit ? '编辑岗位' : '新增岗位' }}</el-divider>
      <el-form :model="posForm" :rules="posRules" ref="posFormRef" label-width="80px" inline>
        <el-form-item label="名称" prop="name" style="width: 280px">
          <el-input v-model="posForm.name" placeholder="如 Java工程师" />
        </el-form-item>
        <el-form-item label="职级" style="width: 200px">
          <el-input v-model="posForm.level" placeholder="如 P5, M3" />
        </el-form-item>
        <el-form-item>
          <el-button v-if="isPosEdit" @click="cancelPosEdit">取消</el-button>
          <el-button type="primary" @click="submitPosition">{{ isPosEdit ? '保存' : '新增' }}</el-button>
        </el-form-item>
      </el-form>

      <el-divider content-position="left">岗位列表</el-divider>
      <el-empty v-if="positions.length === 0" description="暂无岗位，请在上方添加" />
      <el-table v-else :data="positions" style="width: 100%" border>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="level" label="职级">
          <template #default="scope">
            <span>{{ scope.row.level || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="scope">
            <el-button size="small" @click="editPosition(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="removePosition(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { OfficeBuilding } from '@element-plus/icons-vue'
import {
  listDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  listPositions,
  createPosition,
  updatePosition,
  deletePosition,
} from '@/api/departments'
import { listEmployees } from '@/api/employees'

const loading = ref(false)
const treeData = ref([])
const tableData = ref([])
const employeeMap = ref({})
const managerList = ref([])

const positions = ref([])
const currentDept = ref(null)

const deptDialogVisible = ref(false)
const isEdit = ref(false)
const deptForm = reactive({ id: null, code: '', name: '', parent_id: null, head_id: null })
const deptFormRef = ref(null)
const deptRules = {
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

const posDialogVisible = ref(false)
const isPosEdit = ref(false)
const posForm = reactive({ id: null, name: '', level: '', department_id: null })
const posFormRef = ref(null)
const posRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

// 构建部门负责人选择器的数据（排除自身及其子部门）
const treeSelectData = computed(() => {
  if (!isEdit.value || !deptForm.id) return treeData.value
  // 编辑时，不能选择自己及其子部门作为上级
  const excludeIds = new Set()
  const collectIds = (nodes) => {
    nodes.forEach((n) => {
      excludeIds.add(n.id)
      if (n.children) collectIds(n.children)
    })
  }
  const selfNode = findNode(treeData.value, deptForm.id)
  if (selfNode) {
    excludeIds.add(selfNode.id)
    if (selfNode.children) collectIds(selfNode.children)
  }
  return treeData.value.filter((n) => !excludeIds.has(n.id))
})

function findNode(nodes, id) {
  for (const n of nodes) {
    if (n.id === id) return n
    if (n.children) {
      const found = findNode(n.children, id)
      if (found) return found
    }
  }
  return null
}

function enrichTree(nodes) {
  return nodes.map((n) => {
    const head = employeeMap.value[n.head_id]
    const enriched = {
      ...n,
      head_name: head ? head.name : null,
      employee_count: n.employee_count ?? 0,
      position_count: n.position_count ?? 0,
    }
    if (n.children && n.children.length) {
      enriched.children = enrichTree(n.children)
    }
    return enriched
  })
}

async function loadData() {
  loading.value = true
  try {
    // 并行加载：扁平部门列表 + 员工列表
    const [deptRes, empRes] = await Promise.all([
      listDepartments(),
      listEmployees({ size: 1000 }),
    ])

    const flatList = deptRes || []
    const emps = empRes.items || empRes.data?.items || empRes || []
    employeeMap.value = {}
    managerList.value = []
    for (const e of emps) {
      if (e.id) employeeMap.value[e.id] = e
      if (e.user?.role === 'manager' || e.role === 'manager') {
        managerList.value.push(e)
      }
    }

    // 使用扁平列表构建树形结构（保留 employee_count / position_count 等字段）
    const tree = buildTree(flatList)
    treeData.value = enrichTree(tree)
    tableData.value = treeData.value
  } catch (e) {
    console.error(e)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function buildTree(flatList, parentId = null, level = 0) {
  const roots = []
  for (const item of flatList) {
    if ((item.parent_id || null) === parentId) {
      const node = { ...item, level, children: [] }
      node.children = buildTree(flatList, item.id, level + 1)
      roots.push(node)
    }
  }
  return roots
}

function openDeptDialog() {
  isEdit.value = false
  Object.assign(deptForm, { id: null, code: '', name: '', parent_id: null, head_id: null })
  deptDialogVisible.value = true
}

function editDept(row) {
  isEdit.value = true
  Object.assign(deptForm, {
    id: row.id,
    code: row.code,
    name: row.name,
    parent_id: row.parent_id,
    head_id: row.head_id,
  })
  deptDialogVisible.value = true
}

async function submitDept() {
  try {
    await deptFormRef.value.validate()
    const payload = {
      code: deptForm.code,
      name: deptForm.name,
      parent_id: deptForm.parent_id || null,
      head_id: deptForm.head_id || null,
    }
    if (isEdit.value) {
      await updateDepartment(deptForm.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createDepartment(payload)
      ElMessage.success('创建成功')
    }
    deptDialogVisible.value = false
    loadData()
  } catch (e) {
    if (e?.response?.data?.detail) {
      ElMessage.error(e.response.data.detail)
    } else {
      console.error(e)
    }
  }
}

async function deleteDept(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除部门 <strong>${row.name}</strong>？<br><small>该部门下现有 ${row.position_count || 0} 个岗位、${row.employee_count || 0} 名员工，若有子部门则不可删除。</small>`,
      '删除确认',
      { type: 'warning', dangerouslyUseHTMLString: true }
    )
    await deleteDepartment(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e === 'cancel') return
    const detail = e?.response?.data?.detail || ''
    if (detail.includes('子部门')) {
      ElMessage.error('该部门存在子部门，无法删除')
    } else if (detail.includes('员工')) {
      ElMessage.error('该部门下存在员工，无法删除')
    } else if (detail.includes('岗位')) {
      ElMessage.error('该部门下存在岗位，无法删除')
    } else {
      ElMessage.error(detail || '删除失败')
    }
    console.error(e)
  }
}

// 拖拽相关
function allowDrag(draggingNode) {
  return true
}

function allowDrop(draggingNode, dropNode, type) {
  // 不允许拖到自己或自己的子节点中
  if (type === 'inner') {
    // 检查 dropNode 是否是 draggingNode 的子节点
    let p = dropNode
    while (p) {
      if (p.data.id === draggingNode.data.id) return false
      p = p.parent
    }
  }
  return true
}

async function handleDrop(draggingNode, dropNode, dropType) {
  const deptId = draggingNode.data.id
  let newParentId = null
  if (dropType === 'inner') {
    newParentId = dropNode.data.id
  } else if (dropType === 'before' || dropType === 'after') {
    newParentId = dropNode.data.parent_id || null
  }
  try {
    await updateDepartment(deptId, { parent_id: newParentId })
    ElMessage.success('部门归属调整成功')
    loadData()
  } catch (e) {
    ElMessage.error('调整失败')
    loadData()
    console.error(e)
  }
}

// 岗位管理相关
async function managePositions(row) {
  currentDept.value = row
  try {
    const res = await listPositions({ department_id: row.id })
    positions.value = res.items || []
    isPosEdit.value = false
    Object.assign(posForm, { id: null, name: '', level: '', department_id: row.id })
    posDialogVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

function editPosition(row) {
  isPosEdit.value = true
  Object.assign(posForm, { id: row.id, name: row.name, level: row.level || '', department_id: currentDept.value.id })
}

function cancelPosEdit() {
  isPosEdit.value = false
  Object.assign(posForm, { id: null, name: '', level: '', department_id: currentDept.value.id })
}

async function submitPosition() {
  try {
    await posFormRef.value.validate()
    if (isPosEdit.value) {
      await updatePosition(posForm.id, { name: posForm.name, level: posForm.level })
      ElMessage.success('更新成功')
    } else {
      await createPosition({ name: posForm.name, level: posForm.level, department_id: posForm.department_id })
      ElMessage.success('创建成功')
    }
    cancelPosEdit()
    const res = await listPositions({ department_id: currentDept.value.id })
    positions.value = res.items || []
  } catch (e) {
    console.error(e)
  }
}

async function removePosition(row) {
  try {
    await ElMessageBox.confirm(`确认删除岗位 ${row.name}？`, '提示', { type: 'warning' })
    await deletePosition(row.id)
    ElMessage.success('删除成功')
    const res = await listPositions({ department_id: currentDept.value.id })
    positions.value = res.items || []
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
.mb-16 {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.toolbar {
  margin-bottom: 16px;
}
.org-chart-card :deep(.el-tree-node__content) {
  height: 36px;
}
.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
}
.tree-icon {
  color: #409eff;
  font-size: 16px;
}
.tree-label {
  font-weight: 500;
}
.tree-tag {
  margin-left: 4px;
}
</style>
