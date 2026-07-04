<template>
  <div>
    <h2>KPI 模板管理</h2>
    <el-card class="mt-20">
      <div class="toolbar">
        <el-button type="primary" @click="goToCreate">新建模板</el-button>
      </div>
      <el-table :data="templates" style="width: 100%" v-loading="loading">
        <el-table-column prop="position_name" label="岗位" />
        <el-table-column prop="name" label="指标名称" />
        <el-table-column prop="weight" label="权重" width="100" />
        <el-table-column prop="target_value" label="目标值" />
        <el-table-column prop="description" label="说明" />
        <el-table-column label="操作" width="220">
          <template #default="scope">
            <el-button size="small" @click="editTemplate(scope.row)">编辑</el-button>
            <el-button size="small" type="info" @click="copyTemplate(scope.row)">复制</el-button>
            <el-button size="small" type="danger" @click="deleteTemplate(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listKpiTemplates, deleteKpiTemplate, copyKpiTemplate } from '@/api/kpi-templates'

const loading = ref(false)
const templates = ref([])
const router = useRouter()

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

function goToCreate() {
  router.push('/kpi-templates/create')
}

function editTemplate(row) {
  router.push(`/kpi-templates/${row.id}/edit`)
}

async function copyTemplate(row) {
  try {
    await ElMessageBox.confirm(`确认复制模板 ${row.name}？`, '提示', { type: 'info' })
    await copyKpiTemplate(row.id)
    ElMessage.success('复制成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
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
