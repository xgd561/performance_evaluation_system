<template>
  <div>
    <h2>{{ isEdit ? '编辑 KPI 模板' : '新建 KPI 模板' }}</h2>
    <el-card class="mt-20">
      <el-form :model="form" label-width="120px" ref="formRef" :rules="baseRules">
        <el-form-item label="关联岗位" prop="position_id">
          <el-select v-model="form.position_id" placeholder="请选择岗位" filterable :disabled="isEdit">
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <h3>指标列表</h3>
      <el-table :data="form.items" style="width: 100%" border>
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column label="指标名称" min-width="140">
          <template #default="scope">
            <el-input v-model="scope.row.name" placeholder="请输入指标名称" />
          </template>
        </el-table-column>
        <el-table-column label="权重 (%)" width="120">
          <template #default="scope">
            <el-input-number v-model="scope.row.weight" :min="0" :max="100" :precision="2" style="width: 100%" />
          </template>
        </el-table-column>
        <el-table-column label="目标值" min-width="120">
          <template #default="scope">
            <el-input v-model="scope.row.target_value" placeholder="如 100万, 95%" />
          </template>
        </el-table-column>
        <el-table-column label="计分方式" width="130">
          <template #default="scope">
            <el-select v-model="scope.row.scoring_method" placeholder="请选择">
              <el-option label="百分比" value="percentage" />
              <el-option label="定性评价" value="qualitative" />
              <el-option label="定量计数" value="quantitative" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="评分标准" min-width="180">
          <template #default="scope">
            <el-input v-model="scope.row.description" type="textarea" :rows="2" placeholder="评分标准说明" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="scope">
            <el-button size="small" type="danger" @click="removeItem(scope.$index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="toolbar">
        <el-button type="primary" @click="addItem">+ 添加指标</el-button>
      </div>

      <div class="summary-row">
        <el-tag :type="weightTotal === 100 ? 'success' : 'danger'" size="large">
          权重合计: {{ weightTotal }}% ({{ weightTotal === 100 ? '正确' : '应为100%' }})
        </el-tag>
      </div>

      <div class="actions">
        <el-button @click="goBack">取消</el-button>
        <el-button type="primary" :disabled="weightTotal !== 100 || form.items.length === 0 || !form.position_id" @click="save">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listPositions } from '@/api/departments'
import {
  listKpiTemplates,
  getKpiTemplate,
  createKpiTemplatesBatch,
  updateKpiTemplatesBatch,
} from '@/api/kpi-templates'

const route = useRoute()
const router = useRouter()
const templateId = computed(() => route.params.id)
const isEdit = computed(() => !!templateId.value)

const positions = ref([])
const formRef = ref(null)
const form = reactive({
  position_id: null,
  items: [
    { name: '', weight: 0, target_value: '', scoring_method: 'percentage', description: '' },
  ],
})

const baseRules = {
  position_id: [{ required: true, message: '请选择岗位', trigger: 'change' }],
}

const weightTotal = computed(() => {
  const total = form.items.reduce((sum, item) => sum + (Number(item.weight) || 0), 0)
  return Math.round(total * 100) / 100
})

function addItem() {
  form.items.push({ name: '', weight: 0, target_value: '', scoring_method: 'percentage', description: '' })
}

function removeItem(index) {
  if (form.items.length <= 1) {
    ElMessage.warning('至少需要保留一个指标')
    return
  }
  form.items.splice(index, 1)
}

function goBack() {
  router.push('/kpi-templates')
}

async function loadPositions() {
  try {
    const res = await listPositions()
    positions.value = res.items || []
  } catch (e) {
    console.error(e)
  }
}

async function loadEditData() {
  if (!isEdit.value) return
  try {
    const detail = await getKpiTemplate(templateId.value)
    const positionId = detail.position_id
    form.position_id = positionId

    // Load all active templates for this position
    const allRes = await listKpiTemplates()
    const allTemplates = Array.isArray(allRes) ? allRes : []
    const positionTemplates = allTemplates.filter(
      (t) => t.position_id === positionId && t.is_active !== false
    )

    if (positionTemplates.length > 0) {
      form.items = positionTemplates.map((t) => ({
        name: t.name || '',
        weight: Number(t.weight) || 0,
        target_value: t.target_value || '',
        scoring_method: t.scoring_method || 'percentage',
        description: t.description || '',
      }))
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载模板数据失败')
  }
}

async function save() {
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }

  // Frontend validation: items non-empty, names non-empty, no duplicate names
  if (form.items.length === 0) {
    ElMessage.warning('请至少添加一个指标')
    return
  }
  const names = form.items.map((i) => i.name.trim()).filter((n) => n)
  if (names.length !== form.items.length) {
    ElMessage.warning('所有指标名称不能为空')
    return
  }
  if (new Set(names).size !== names.length) {
    ElMessage.warning('指标名称不能重复')
    return
  }
  if (weightTotal.value !== 100) {
    ElMessage.warning('权重合计必须等于100%')
    return
  }

  const payload = {
    position_id: form.position_id,
    items: form.items.map((item) => ({
      name: item.name.trim(),
      weight: item.weight,
      target_value: item.target_value || null,
      scoring_method: item.scoring_method || 'percentage',
      description: item.description || null,
    })),
  }

  try {
    if (isEdit.value) {
      await updateKpiTemplatesBatch(templateId.value, { items: payload.items })
      ElMessage.success('更新成功')
    } else {
      await createKpiTemplatesBatch(payload)
      ElMessage.success('创建成功')
    }
    router.push('/kpi-templates')
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadPositions()
  loadEditData()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.toolbar {
  margin-top: 16px;
  margin-bottom: 16px;
}
.summary-row {
  margin-top: 16px;
  margin-bottom: 16px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}
</style>
