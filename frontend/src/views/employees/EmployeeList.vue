<template>
  <div>
    <h2>员工管理</h2>
    <el-card class="mt-20">
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="queryForm.keyword" placeholder="姓名/工号" clearable />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="queryForm.department_id" placeholder="全部部门" clearable>
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button type="primary" @click="openAddDialog">新增员工</el-button>
        <el-button @click="handleDownloadTemplate">下载模板</el-button>
        <el-button @click="importDialogVisible = true">导入员工</el-button>
      </div>

      <el-table :data="employees" style="width: 100%" v-loading="loading">
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="department_name" label="部门" />
        <el-table-column prop="position_name" label="岗位" />
        <el-table-column prop="manager_name" label="直属上级" />
        <el-table-column prop="is_department_head" label="部门负责人" width="110">
          <template #default="scope">
            <el-tag v-if="scope.row.is_department_head" type="success">是</el-tag>
            <el-tag v-else type="info">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.is_active" type="success">在职</el-tag>
            <el-tag v-else type="danger">离职</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="openEditDialog(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        v-model:current-page="queryForm.page"
        v-model:page-size="queryForm.size"
        :total="total"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        @size-change="handlePageChange"
        @current-change="handlePageChange"
      />
    </el-card>

    <!-- Add/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑员工' : '新增员工'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="工号" prop="employee_no">
          <el-input v-model="form.employee_no" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="部门" prop="department_id">
          <el-select v-model="form.department_id" placeholder="请选择部门" @change="onDeptChange">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="岗位" prop="position_id">
          <el-select v-model="form.position_id" placeholder="请选择岗位">
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="直属上级">
          <el-input v-model="form.manager_employee_no" placeholder="上级工号" />
        </el-form-item>
        <el-form-item label="部门负责人">
          <el-switch v-model="form.is_department_head" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- Import Dialog -->
    <el-dialog v-model="importDialogVisible" title="导入员工" width="400px">
      <el-upload
        ref="uploadRef"
        action=""
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".xlsx"
      >
        <el-button type="primary">选择Excel文件</el-button>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importLoading">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listEmployees, createEmployee, updateEmployee, deleteEmployee, importEmployees, downloadTemplate } from '@/api/employees'
import { listDepartments } from '@/api/departments'
import { listPositions } from '@/api/departments'

const loading = ref(false)
const importLoading = ref(false)
const dialogVisible = ref(false)
const importDialogVisible = ref(false)
const isEdit = ref(false)
const employees = ref([])
const departments = ref([])
const positions = ref([])
const total = ref(0)
const uploadRef = ref(null)
const importFile = ref(null)

const queryForm = reactive({
  page: 1,
  size: 20,
  keyword: '',
  department_id: null,
})

const form = reactive({
  id: null,
  employee_no: '',
  name: '',
  department_id: null,
  position_id: null,
  manager_employee_no: '',
  is_department_head: false,
})

const formRef = ref(null)
const rules = {
  employee_no: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  department_id: [{ required: true, message: '请选择部门', trigger: 'change' }],
  position_id: [{ required: true, message: '请选择岗位', trigger: 'change' }],
}

async function loadData() {
  loading.value = true
  try {
    const res = await listEmployees(queryForm)
    employees.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadDepartments() {
  try {
    const res = await listDepartments()
    departments.value = res.length ? res : res.items || []
  } catch (e) {
    console.error(e)
  }
}

async function loadPositions(deptId) {
  try {
    const res = await listPositions({ department_id: deptId })
    positions.value = res.items || []
  } catch (e) {
    console.error(e)
  }
}

function handleSearch() {
  queryForm.page = 1
  loadData()
}

function handlePageChange() {
  loadData()
}

function resetQuery() {
  queryForm.keyword = ''
  queryForm.department_id = null
  queryForm.page = 1
  loadData()
}

function openAddDialog() {
  isEdit.value = false
  Object.assign(form, {
    id: null,
    employee_no: '',
    name: '',
    department_id: null,
    position_id: null,
    manager_employee_no: '',
    is_department_head: false,
  })
  positions.value = []
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  Object.assign(form, {
    id: row.id,
    employee_no: row.employee_no,
    name: row.name,
    department_id: row.department_id,
    position_id: row.position_id,
    manager_employee_no: row.manager_employee_no || '',
    is_department_head: row.is_department_head,
  })
  loadPositions(row.department_id)
  dialogVisible.value = true
}

async function submitForm() {
  try {
    await formRef.value.validate()
    if (isEdit.value) {
      await updateEmployee(form.id, {
        name: form.name,
        department_id: form.department_id,
        position_id: form.position_id,
        manager_employee_no: form.manager_employee_no || undefined,
        is_department_head: form.is_department_head,
      })
      ElMessage.success('更新成功')
    } else {
      await createEmployee({
        employee_no: form.employee_no,
        name: form.name,
        department_id: form.department_id,
        position_id: form.position_id,
        manager_employee_no: form.manager_employee_no || undefined,
        is_department_head: form.is_department_head,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    console.error(e)
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除员工 ${row.name}（${row.employee_no}）？`, '提示', { type: 'warning' })
    await deleteEmployee(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
    }
  }
}

async function handleDownloadTemplate() {
  try {
    const blob = await downloadTemplate('sample')
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'employees_template_sample.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
  }
}

function handleFileChange(file) {
  importFile.value = file.raw
}

async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  importLoading.value = true
  try {
    const res = await importEmployees(importFile.value)
    ElMessage.success(`导入成功: ${res.success || 0} 条, 失败: ${res.failed || 0} 条`)
    importDialogVisible.value = false
    loadData()
  } catch (e) {
    console.error(e)
  } finally {
    importLoading.value = false
  }
}

function onDeptChange(val) {
  form.position_id = null
  loadPositions(val)
}

onMounted(() => {
  loadData()
  loadDepartments()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.search-form {
  margin-bottom: 16px;
}
.toolbar {
  margin-bottom: 16px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
