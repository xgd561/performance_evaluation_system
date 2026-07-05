
<template>
  <PageContainer title="申诉处理">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="appeal" class="appeal-detail">
      <!-- 申诉基本信息 -->
      <el-card>
        <div class="section-title">申诉信息</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="申诉人">{{ appeal.employee_name }}（{{ appeal.employee_no }}）</el-descriptions-item>
          <el-descriptions-item label="申诉状态">
            <el-tag :type="statusType(appeal.status)" size="small">{{ statusText(appeal.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="申诉理由" :span="2">{{ appeal.reason }}</el-descriptions-item>
          <el-descriptions-item label="详细说明" :span="2">{{ appeal.detail || '—' }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ formatDate(appeal.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="考核总分">{{ appeal.record?.total_score || '—' }}</el-descriptions-item>
          <el-descriptions-item label="考核等级">
            <el-tag :type="gradeTagType(appeal.record?.grade)" size="small">{{ appeal.record?.grade || '—' }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 评分原始数据 -->
      <el-card class="mt-20" v-if="recordDetail">
        <div class="section-title">评分原始数据</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="自评 - 业绩">{{ recordDetail.self_scores?.performance ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="上级评 - 业绩">{{ recordDetail.manager_scores?.performance ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="自评 - 能力">{{ recordDetail.self_scores?.ability ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="上级评 - 能力">{{ recordDetail.manager_scores?.ability ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="自评 - 态度">{{ recordDetail.self_scores?.attitude ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="上级评 - 态度">{{ recordDetail.manager_scores?.attitude ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="加权业绩">{{ recordDetail.weighted_performance ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="加权能力">{{ recordDetail.weighted_ability ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="加权态度">{{ recordDetail.weighted_attitude ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ recordDetail.total_score ?? '—' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 强制分布记录 -->
        <div v-if="recordDetail.is_distribution_override" class="mt-20">
          <el-alert type="warning" :closable="false" show-icon>
            <template #default>
              <span>强制分布调整：{{ recordDetail.override_reason || '等级被强制调整' }}</span>
            </template>
          </el-alert>
        </div>
      </el-card>

      <!-- 处理区 -->
      <el-card class="mt-20" v-if="mode === 'resolve' && appeal.status === 'pending'">
        <div class="section-title">复核处理</div>
        <el-form :model="resolveForm" label-width="100px">
          <el-form-item label="处理方式" required>
            <el-radio-group v-model="resolveForm.resolution">
              <el-radio-button label="maintain">维持原结果</el-radio-button>
              <el-radio-button label="adjust">调整等级</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="resolveForm.resolution === 'adjust'" label="新等级" required>
            <el-select v-model="resolveForm.new_grade" placeholder="请选择新等级">
              <el-option label="A" value="A" />
              <el-option label="B" value="B" />
              <el-option label="C" value="C" />
              <el-option label="D" value="D" />
            </el-select>
          </el-form-item>
          <el-form-item label="复核结论" required>
            <el-input
              v-model="resolveForm.comment"
              type="textarea"
              :rows="4"
              placeholder="请填写复核结论"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </el-form>
        <div class="form-actions">
          <el-button @click="goBack">返回</el-button>
          <el-button type="primary" :loading="submitting" @click="submitResolve">提交复核</el-button>
        </div>
      </el-card>

      <!-- 只读模式 -->
      <el-card class="mt-20" v-if="mode === 'view' || appeal.status !== 'pending'">
        <div class="section-title">处理结果</div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="处理状态">{{ statusText(appeal.status) }}</el-descriptions-item>
          <el-descriptions-item v-if="appeal.review_result" label="复核结论">{{ appeal.review_result }}</el-descriptions-item>
          <el-descriptions-item v-if="appeal.reviewer_name" label="处理人">{{ appeal.reviewer_name }}</el-descriptions-item>
          <el-descriptions-item v-if="appeal.resolved_at" label="处理时间">{{ formatDate(appeal.resolved_at) }}</el-descriptions-item>
        </el-descriptions>
        <div class="form-actions" v-if="mode === 'view'">
          <el-button @click="goBack">返回</el-button>
        </div>
      </el-card>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getAppeal, resolveAppeal } from '@/api/appeals'
import { getAssessmentDetail } from '@/api/scores'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const appeal = ref(null)
const recordDetail = ref(null)
const submitting = ref(false)
const mode = ref(route.query.mode || 'view')

const resolveForm = ref({
  resolution: 'maintain',
  new_grade: '',
  comment: '',
})

onMounted(async () => {
  const appealId = route.query.id
  if (!appealId) {
    ElMessage.error('缺少申诉ID')
    goBack()
    return
  }
  loading.value = true
  try {
    const res = await getAppeal(appealId)
    appeal.value = res
    if (res.record_id) {
      try {
        const detail = await getAssessmentDetail(res.record_id)
        recordDetail.value = detail
      } catch (e) {
        console.error(e)
      }
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载申诉详情失败')
  } finally {
    loading.value = false
  }
})

function statusText(status) {
  const map = { pending: '待处理', resolved: '已处理' }
  return map[status] || status
}

function statusType(status) {
  if (status === 'pending') return 'warning'
  if (status === 'resolved') return 'success'
  return 'info'
}

function gradeTagType(grade) {
  const map = { A: 'success', B: 'primary', C: 'warning', D: 'danger' }
  return map[grade] || 'info'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN')
}

function goBack() {
  router.push({ name: 'Appeals' })
}

async function submitResolve() {
  if (!resolveForm.value.comment) {
    ElMessage.warning('请填写复核结论')
    return
  }
  if (resolveForm.value.resolution === 'adjust' && !resolveForm.value.new_grade) {
    ElMessage.warning('请选择新等级')
    return
  }

  submitting.value = true
  try {
    const payload = {
      resolution: resolveForm.value.resolution,
      comment: resolveForm.value.comment,
    }
    if (resolveForm.value.resolution === 'adjust') {
      payload.new_grade = resolveForm.value.new_grade
    }
    await resolveAppeal(appeal.value.id, payload)
    ElMessage.success('复核处理成功')
    goBack()
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.message || '处理失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.loading-wrap {
  padding: 40px;
}
.section-title {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 16px;
}
.mt-20 {
  margin-top: 20px;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}
</style>
