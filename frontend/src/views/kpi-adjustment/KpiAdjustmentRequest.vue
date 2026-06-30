<template>
  <div>
    <h2>KPI 动态调整申请</h2>
    <el-card class="mt-20">
      <template #header>
        <div class="card-header">
          <span>选择考核记录</span>
        </div>
      </template>
      <el-select
        v-model="selectedRecordId"
        placeholder="选择被评人"
        style="width: 300px"
        @change="handleRecordChange"
      >
        <el-option
          v-for="item in toReviewList"
          :key="item.record_id"
          :label="`${item.employee_name} (${item.employee_no}) — ${item.cycle_name || ''}`"
          :value="item.record_id"
        />
      </el-select>
      <el-empty v-if="toReviewList.length === 0 && !loading" description="暂无待调整记录" />
    </el-card>

    <el-card v-if="selectedRecord" class="mt-20" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>当前 KPI 指标</span>
          <el-tag type="info">{{ selectedRecord.employee_name }}</el-tag>
        </div>
      </template>
      <el-table :data="kpiItems" border stripe style="margin-bottom: 20px">
        <el-table-column prop="name" label="指标名称" min-width="150" />
        <el-table-column prop="target" label="当前目标值" min-width="120" />
        <el-table-column prop="weight" label="权重" width="100">
          <template #default="{ row }">{{ row.weight }}%</template>
        </el-table-column>
      </el-table>

      <h4 style="margin-bottom: 16px">填写调整内容</h4>
      <el-form :model="adjustForm" label-width="120px" :rules="rules" ref="adjustFormRef">
        <el-form-item label="选择指标" prop="kpi_id">
          <el-select v-model="adjustForm.kpi_id" placeholder="选择要调整的 KPI" style="width: 300px">
            <el-option
              v-for="kpi in kpiItems"
              :key="kpi.id"
              :label="kpi.name"
              :value="kpi.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="新目标值" prop="new_target">
          <el-input v-model="adjustForm.new_target" placeholder="请输入新的目标值" style="width: 300px" />
        </el-form-item>
        <el-form-item label="调整原因" prop="reason">
          <el-input
            v-model="adjustForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请输入调整原因（不少于5字）"
            style="width: 400px"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">提交申请</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getToReviewList } from '@/api/scores'
import { requestKpiAdjustment } from '@/api/kpiAdjustment'

const loading = ref(false)
const submitting = ref(false)
const toReviewList = ref([])
const selectedRecordId = ref(null)
const adjustFormRef = ref(null)

const adjustForm = ref({
  kpi_id: null,
  new_target: '',
  reason: '',
})

const selectedRecord = computed(() => {
  if (!selectedRecordId.value) return null
  return toReviewList.value.find(r => r.record_id === selectedRecordId.value) || null
})

const kpiItems = computed(() => {
  if (!selectedRecord.value || !selectedRecord.value.kpi_snapshot) return []
  const snapshot = selectedRecord.value.kpi_snapshot
  if (Array.isArray(snapshot)) {
    return snapshot.map((item, index) => ({
      id: item.id || item.kpi_template_id || index,
      name: item.name || item.kpi_name || `KPI ${index + 1}`,
      target: item.target_value || item.target || '-',
      weight: item.weight || 0,
    }))
  }
  if (typeof snapshot === 'object' && snapshot.items) {
    return snapshot.items.map((item, index) => ({
      id: item.id || item.kpi_template_id || index,
      name: item.name || item.kpi_name || `KPI ${index + 1}`,
      target: item.target_value || item.target || '-',
      weight: item.weight || 0,
    }))
  }
  return []
})

const rules = {
  kpi_id: [{ required: true, message: '请选择要调整的指标', trigger: 'change' }],
  new_target: [{ required: true, message: '请输入新目标值', trigger: 'blur' }],
  reason: [
    { required: true, message: '请输入调整原因', trigger: 'blur' },
    { min: 5, message: '调整原因不少于5字', trigger: 'blur' },
  ],
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await getToReviewList()
    toReviewList.value = res || []
  } catch (e) {
    console.error(e)
    ElMessage.error('获取待评列表失败')
  } finally {
    loading.value = false
  }
}

function handleRecordChange() {
  adjustForm.value = { kpi_id: null, new_target: '', reason: '' }
}

function handleReset() {
  adjustForm.value = { kpi_id: null, new_target: '', reason: '' }
}

async function handleSubmit() {
  if (!adjustFormRef.value) return
  await adjustFormRef.value.validate(async (valid) => {
    if (!valid) return
    if (!selectedRecordId.value) {
      ElMessage.warning('请选择考核记录')
      return
    }
    try {
      await ElMessageBox.confirm('确认提交该 KPI 调整申请？', '提示', { type: 'warning' })
      submitting.value = true
      await requestKpiAdjustment(selectedRecordId.value, adjustForm.value)
      ElMessage.success('申请已提交，等待审批')
      handleReset()
      selectedRecordId.value = null
    } catch (e) {
      if (e !== 'cancel') {
        console.error(e)
        ElMessage.error(e?.response?.data?.message || '提交失败')
      }
    } finally {
      submitting.value = false
    }
  })
}

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
