<template>
  <PageContainer title="申诉">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="records.length === 0 && !appealFormVisible" class="empty-wrap">
      <el-empty description="当前没有已发布的考核记录可供申诉" />
    </div>

    <div v-else>
      <!-- 已发布的考核记录列表 -->
      <el-card v-if="!appealFormVisible" class="appeal-list">
        <div class="card-title">可申诉的考核记录</div>
        <el-table :data="records" style="width: 100%">
          <el-table-column prop="cycle_name" label="考核周期" />
          <el-table-column prop="total_score" label="总分" />
          <el-table-column prop="grade" label="等级">
            <template #default="{ row }">
              <el-tag :type="gradeTagType(row.grade)" size="small">{{ row.grade }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="manager_comment" label="上级评语" show-overflow-tooltip />
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="startAppeal(row)">发起申诉</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 申诉表单 -->
      <el-card v-if="appealFormVisible" class="appeal-form">
        <div class="card-title">发起申诉</div>
        <div class="appeal-info">
          <p><strong>考核周期：</strong>{{ selectedRecord?.cycle_name }}</p>
          <p><strong>总分：</strong>{{ selectedRecord?.total_score }}</p>
          <p><strong>等级：</strong>{{ selectedRecord?.grade }}</p>
        </div>
        <el-form :model="appealForm" label-width="100px">
          <el-form-item label="申诉理由" required>
            <el-select v-model="appealForm.reason" placeholder="请选择申诉理由">
              <el-option label="对评分结果有异议" value="对评分结果有异议" />
              <el-option label="对等级划分有异议" value="对等级划分有异议" />
              <el-option label="对上级评语有异议" value="对上级评语有异议" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
          <el-form-item label="详细说明">
            <el-input
              v-model="appealForm.detail"
              type="textarea"
              :rows="4"
              placeholder="请详细说明申诉原因（不少于20字）"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </el-form>
        <div class="form-actions">
          <el-button @click="cancelAppeal">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitAppeal">提交申诉</el-button>
        </div>
      </el-card>

      <!-- 申诉历史 -->
      <el-card v-if="appealHistory.length > 0" class="mt-20">
        <div class="card-title">申诉历史</div>
        <el-timeline>
          <el-timeline-item
            v-for="item in appealHistory"
            :key="item.id"
            :type="timelineType(item.status)"
            :timestamp="item.created_at"
          >
            <div class="appeal-item">
              <div class="appeal-reason">{{ item.reason }}</div>
              <div class="appeal-detail">{{ item.detail }}</div>
              <el-tag :type="appealStatusType(item.status)" size="small">{{ appealStatusText(item.status) }}</el-tag>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import PageContainer from '@/components/PageContainer.vue'
import { getMyAssessment } from '@/api/scores'
import { getMyAppeals, createAppeal } from '@/api/appeals'

const loading = ref(false)
const records = ref([])
const appealHistory = ref([])
const appealFormVisible = ref(false)
const selectedRecord = ref(null)
const submitting = ref(false)

const appealForm = ref({
  reason: '',
  detail: '',
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await getMyAssessment()
    const allRecords = res?.items || []
    records.value = allRecords.filter(r => r.status === 'published')

    const appealRes = await getMyAppeals()
    appealHistory.value = appealRes || []
  } catch (e) {
    console.error(e)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
})

function gradeTagType(grade) {
  const map = { A: 'success', B: 'primary', C: 'warning', D: 'danger' }
  return map[grade] || 'info'
}

function startAppeal(record) {
  selectedRecord.value = record
  appealFormVisible.value = true
  appealForm.value = { reason: '', detail: '' }
}

function cancelAppeal() {
  appealFormVisible.value = false
  selectedRecord.value = null
}

async function submitAppeal() {
  if (!appealForm.value.reason) {
    ElMessage.warning('请选择申诉理由')
    return
  }
  if (!appealForm.value.detail || appealForm.value.detail.length < 20) {
    ElMessage.warning('详细说明不少于20字')
    return
  }

  submitting.value = true
  try {
    await createAppeal({
      record_id: selectedRecord.value.record_id,
      reason: appealForm.value.reason,
      detail: appealForm.value.detail,
    })
    ElMessage.success('申诉提交成功')
    appealFormVisible.value = false
    const appealRes = await getMyAppeals()
    appealHistory.value = appealRes || []
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

function timelineType(status) {
  return status === 'resolved' ? 'success' : status === 'rejected' ? 'danger' : 'warning'
}

function appealStatusType(status) {
  const map = { pending: 'warning', resolved: 'success', rejected: 'danger' }
  return map[status] || 'info'
}

function appealStatusText(status) {
  const map = { pending: '待处理', resolved: '已通过', rejected: '已驳回' }
  return map[status] || status
}
</script>

<style scoped>
.loading-wrap {
  padding: 40px;
}
.empty-wrap {
  padding: 60px 0;
}
.card-title {
  font-weight: bold;
  margin-bottom: 16px;
}
.appeal-list {
  margin-bottom: 20px;
}
.appeal-form {
  margin-bottom: 20px;
}
.appeal-info {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 16px;
}
.appeal-info p {
  margin: 4px 0;
  font-size: 14px;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.mt-20 {
  margin-top: 20px;
}
.appeal-item {
  margin-bottom: 8px;
}
.appeal-reason {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.appeal-detail {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}
</style>
