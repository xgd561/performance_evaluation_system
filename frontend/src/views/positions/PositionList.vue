<template>
  <div>
    <h2>岗位管理</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="所属部门">
          <el-select v-model="queryForm.department_id" placeholder="全部部门" clearable @change="handleSearch">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button type="primary" @click="openAddDialog">新增岗位</el-button>
      </div>

      <el-table :data="positions" style="width: 100%" v-loading="loading" border>
        <el-table-column prop="name" label="岗位名称" />
        <el-table-column prop="department_name" label="所属部门" />
        <el-table-column prop="level" label="职级" />
        <el-table-column prop="employee_count" label="人数" width="90" align="center">
          <template #default="scope">
            <span>{{ scope.row.employee_count ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="scope">
            <el-button size="small" @click="editPosition(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeletePosition(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Add/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑岗位' : '新增岗位'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="岗位名称" prop="name">
          <el-input v-model="form.name" placeholder="如 Java工程师" />
        </el-form-item>
        <el-form-item label="所属部门" prop="department_id">
          <el-select v-model="form.department_id" placeholder="请选择部门" style="width: 100%">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="职级">
          <el-input v-model="form.level" placeholder="如 P5, M3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listPositions, createPosition, updatePosition, deletePosition as apiDeletePosition } from '@/api/departments'
import { listDepartments } from '@/api/departments'
import { listEmployees } from '@/api/employees'

const loading = ref(false)
const positions = ref([])
const departments = ref([])
const allEmployees = ref([])

const queryForm = reactive({ department_id: '' })
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({ id: null, name: '', department_id: '', level: '' })
const formRef = ref(null)
const rules = {
  name: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
  department_id: [{ required: true, message: '请选择所属部门', trigger: 'change' }],
}

async function loadDepartments() {
  try {
    const res = await listDepartments()
    departments.value = res || []
  } catch (e) {
    console.error(e)
  }
}

async function loadEmployees() {
  try {
    const res = await listEmployees({ size: 1000 })
    allEmployees.value = res.items || []
  } catch (e) {
    console.error(e)
  }
}

async function loadPositions() {
  loading.value = true
  try {
    const res = await listPositions({ department_id: queryForm.department_id || undefined })
    const raw = res.items || []
    // 计算每个岗位的人数
    const countMap = {}
    for (const emp of allEmployees.value) {
      if (emp.position_id) {
        countMap[emp.position_id] = (countMap[emp.position_id] || 0) + 1
      }
    }
    // 补充部门名称
    const deptMap = {}
    for (const d of departments.value) {
      deptMap[d.id] = d.name
    }
    positions.value = raw.map(p => ({
      ...p,
      department_name: deptMap[p.department_id] || '—',
      employee_count: countMap[p.id] || 0,
    }))
  } catch (e) {
    console.error(e)
    ElMessage.error('加载岗位失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  loadPositions()
}

function resetQuery() {
  queryForm.department_id = ''
  loadPositions()
}

function openAddDialog() {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', department_id: '', level: '' })
  dialogVisible.value = true
}

function editPosition(row) {
  isEdit.value = true
  Object.assign(form, { id: row.id, name: row.name, department_id: row.department_id, level: row.level || '' })
  dialogVisible.value = true
}

async function submitForm() {
  try {
    await formRef.value.validate()
    if (isEdit.value) {
      await updatePosition(form.id, { name: form.name, level: form.level, department_id: form.department_id })
      ElMessage.success('更新成功')
    } else {
      await createPosition({ name: form.name, level: form.level, department_id: form.department_id })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadPositions()
  } catch (e) {
    if (e?.response?.data?.detail) {
      ElMessage.error(e.response.data.detail)
    } else {
      console.error(e)
    }
  }
}

async function handleDeletePosition(row) {
  try {
    await ElMessageBox.confirm(`确认删除岗位 ${row.name}？`, '提示', { type: 'warning' })
    await apiDeletePosition(row.id)
    ElMessage.success('删除成功')
    loadPositions()
  } catch (e) {
    if (e === 'cancel') return
    const detail = e?.response?.data?.detail || ''
    if (detail.includes('员工')) {
      ElMessage.error('该岗位下存在员工，无法删除')
    } else {
      ElMessage.error(detail || '删除失败')
    }
  }
}

onMounted(() => {
  loadDepartments()
  loadEmployees()
  loadPositions()
})
</script>

<style scoped>
.mt-20 { margin-top: 20px; }
.search-form { margin-bottom: 20px; }
.toolbar { margin-bottom: 16px; }
</style>
