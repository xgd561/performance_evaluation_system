<template>
  <div>
    <h2>部门管理</h2>
    <el-card class="mt-20">
      <div class="toolbar">
        <el-button type="primary" @click="openDeptDialog">新增部门</el-button>
      </div>

      <el-table :data="departments" style="width: 100%" v-loading="loading" row-key="id">
        <el-table-column prop="code" label="编码" width="120" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="parent_name" label="上级部门" />
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="editDept(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteDept(scope.row)">删除</el-button>
            <el-button size="small" @click="managePositions(scope.row)">岗位</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Dept Dialog -->
    <el-dialog v-model="deptDialogVisible" :title="isEdit ? '编辑部门' : '新增部门'" width="450px">
      <el-form :model="deptForm" :rules="deptRules" ref="deptFormRef" label-width="100px">
        <el-form-item label="编码" prop="code">
          <el-input v-model="deptForm.code" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="deptForm.name" />
        </el-form-item>
        <el-form-item label="上级部门">
          <el-select v-model="deptForm.parent_id" placeholder="无" clearable>
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deptDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitDept">确定</el-button>
      </template>
    </el-dialog>

    <!-- Position Dialog -->
    <el-dialog v-model="posDialogVisible" title="岗位管理" width="600px">
      <div class="toolbar">
        <el-button type="primary" size="small" @click="openAddPosition">新增岗位</el-button>
      </div>
      <el-table :data="positions" style="width: 100%">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="level" label="职级" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button size="small" @click="editPosition(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="removePosition(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="posEditDialogVisible" :title="isPosEdit ? '编辑岗位' : '新增岗位'" width="400px">
      <el-form :model="posForm" :rules="posRules" ref="posFormRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="posForm.name" />
        </el-form-item>
        <el-form-item label="职级">
          <el-input v-model="posForm.level" placeholder="如 P5, M3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="posEditDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPosition">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listDepartments, createDepartment, updateDepartment, deleteDepartment } from '@/api/departments'
import { listPositions, createPosition, updatePosition, deletePosition } from '@/api/departments'

const loading = ref(false)
const departments = ref([])
const positions = ref([])
const currentDept = ref(null)

const deptDialogVisible = ref(false)
const isEdit = ref(false)
const deptForm = reactive({ id: null, code: '', name: '', parent_id: null })
const deptFormRef = ref(null)
const deptRules = {
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

const posDialogVisible = ref(false)
const posEditDialogVisible = ref(false)
const isPosEdit = ref(false)
const posForm = reactive({ id: null, name: '', level: '', department_id: null })
const posFormRef = ref(null)
const posRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

async function loadDepartments() {
  loading.value = true
  try {
    const res = await listDepartments()
    departments.value = res.length ? res : res.items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function openDeptDialog() {
  isEdit.value = false
  Object.assign(deptForm, { id: null, code: '', name: '', parent_id: null })
  deptDialogVisible.value = true
}

function editDept(row) {
  isEdit.value = true
  Object.assign(deptForm, { id: row.id, code: row.code, name: row.name, parent_id: row.parent_id })
  deptDialogVisible.value = true
}

async function submitDept() {
  try {
    await deptFormRef.value.validate()
    if (isEdit.value) {
      await updateDepartment(deptForm.id, { code: deptForm.code, name: deptForm.name, parent_id: deptForm.parent_id })
      ElMessage.success('更新成功')
    } else {
      await createDepartment({ code: deptForm.code, name: deptForm.name, parent_id: deptForm.parent_id })
      ElMessage.success('创建成功')
    }
    deptDialogVisible.value = false
    loadDepartments()
  } catch (e) {
    console.error(e)
  }
}

async function deleteDept(row) {
  try {
    await ElMessageBox.confirm(`确认删除部门 ${row.name}？`, '提示', { type: 'warning' })
    await deleteDepartment(row.id)
    ElMessage.success('删除成功')
    loadDepartments()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

async function managePositions(row) {
  currentDept.value = row
  try {
    const res = await listPositions({ department_id: row.id })
    positions.value = res.items || []
    posDialogVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

function openAddPosition() {
  isPosEdit.value = false
  Object.assign(posForm, { id: null, name: '', level: '', department_id: currentDept.value.id })
  posEditDialogVisible.value = true
}

function editPosition(row) {
  isPosEdit.value = true
  Object.assign(posForm, { id: row.id, name: row.name, level: row.level, department_id: currentDept.value.id })
  posEditDialogVisible.value = true
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
    posEditDialogVisible.value = false
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
  loadDepartments()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.toolbar {
  margin-bottom: 16px;
}
</style>
