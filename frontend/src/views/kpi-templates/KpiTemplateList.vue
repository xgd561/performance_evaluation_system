<template>
  <div>
    <h2>KPI 模板管理</h2>
    <el-card class="mt-20">
      <div class="toolbar">
        <el-button type="primary" @click="openDialog">新增模板</el-button>
      </div>
      <el-table :data="templates" style="width: 100%" v-loading="loading">
        <el-table-column prop="position_name" label="岗位" />
        <el-table-column prop="name" label="指标名称" />
        <el-table-column prop="weight" label="权重" width="100" />
        <el-table-column prop="target_value" label="目标值" />
        <el-table-column prop="description" label="说明" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button size="small" @click="editTemplate(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteTemplate(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑模板' : '新增模板'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="岗位" prop="position_id">
          <el-select v-model="form.position_id" placeholder="请选择岗位" filterable>
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="指标名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="权重" prop="weight">
          <el-input-number v-model="form.weight" :min="0" :max="100" :precision="2" />
        </el-form-item>
        <el-form-item label="目标值">
          <el-input v-model="form.target_value" placeholder="如 100万, 95%" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" />
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
import { listKpiTemplates, createKpiTemplate, updateKpiTemplate, deleteKpiTemplate } from '@/api/kpi-templates'
import { listPositions } from '@/api/departments'

const loading = ref(false)
const templates = ref([])
const positions = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({ id: null, position_id: null, name: '', weight: 0, target_value: '', description: '' })
const formRef = ref(null)
const rules = {
  position_id: [{ required: true, message: '请选择岗位', trigger: 'change' }],
  name: [{ required: true, message: '请输入指标名称', trigger: 'blur' }],
  weight: [{ required: true, message: '请输入权重', trigger: 'blur' }],
}

async function loadData() {
  loading.value = true
  try {
    const res = await listKpiTemplates()
    templates.value = res || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadPositions() {
  try {
    const res = await listPositions()
    positions.value = res.items || []
  } catch (e) {
    console.error(e)
  }
}

function openDialog() {
  isEdit.value = false
  Object.assign(form, { id: null, position_id: null, name: '', weight: 0, target_value: '', description: '' })
  dialogVisible.value = true
}

function editTemplate(row) {
  isEdit.value = true
  Object.assign(form, { id: row.id, position_id: row.position_id, name: row.name, weight: row.weight, target_value: row.target_value || '', description: row.description || '' })
  dialogVisible.value = true
}

async function submitForm() {
  try {
    await formRef.value.validate()
    const payload = {
      position_id: form.position_id,
      name: form.name,
      weight: form.weight,
      target_value: form.target_value || null,
      description: form.description || null,
    }
    if (isEdit.value) {
      await updateKpiTemplate(form.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createKpiTemplate(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    console.error(e)
  }
}

async function deleteTemplate(row) {
  try {
    await ElMessageBox.confirm(`确认删除模板 ${row.name}？`, '提示', { type: 'warning' })
    await deleteKpiTemplate(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

onMounted(() => {
  loadData()
  loadPositions()
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
