<template>
  <PageContainer title="协作评分待办">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="reviews.length === 0" class="empty-wrap">
      <el-empty description="暂无待办协作评分任务" />
    </div>

    <div v-else>
      <el-card
        v-for="item in reviews"
        :key="item.id"
        class="review-card"
        shadow="hover"
      >
        <div class="review-header">
          <div class="review-info">
            <el-avatar :size="40" :icon="UserFilled" />
            <div class="info-text">
              <div class="name">{{ item.employee_name }}（{{ item.employee_no }}）</div>
              <div class="meta">{{ item.department_name }} · {{ item.position_name }}</div>
              <div class="meta">考核周期：{{ item.cycle_name }}</div>
            </div>
          </div>
          <el-tag :type="statusTagType(item.status)" size="small">{{ statusText(item.status) }}</el-tag>
        </div>

        <el-divider />

        <div class="score-preview" v-if="item.self_scores || item.manager_scores">
          <div class="score-row" v-if="item.self_scores && Object.keys(item.self_scores).length">
            <span class="label">员工自评：</span>
            <span class="value">业绩 {{ item.self_scores.performance || '-' }} | 能力 {{ item.self_scores.ability || '-' }} | 态度 {{ item.self_scores.attitude || '-' }}</span>
          </div>
          <div class="score-row" v-if="item.manager_scores && Object.keys(item.manager_scores).length">
            <span class="label">上级评分：</span>
            <span class="value">业绩 {{ item.manager_scores.performance || '-' }} | 能力 {{ item.manager_scores.ability || '-' }} | 态度 {{ item.manager_scores.attitude || '-' }}</span>
          </div>
        </div>

        <div class="review-footer">
          <div class="due-date" v-if="item.peer_due_date">
            <el-icon><Calendar /></el-icon>
            <span>截止：{{ item.peer_due_date }}</span>
          </div>
          <el-button type="primary" @click="goScore(item)">
            开始评分
          </el-button>
        </div>
      </el-card>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMyPeerReviews } from '@/api/scores'

const router = useRouter()
const loading = ref(false)
const reviews = ref([])

onMounted(async () => {
  loading.value = true
  try {
    const res = await getMyPeerReviews()
    reviews.value = res?.items || []
  } catch (e) {
    console.error(e)
    ElMessage.error('获取协作评分待办失败')
  } finally {
    loading.value = false
  }
})

function statusTagType(status) {
  const map = {
    pending_self: 'info',
    pending_manager: 'info',
    pending_peer: 'warning',
    pending_summary: 'success',
    pending_approval: 'success',
    published: 'success',
  }
  return map[status] || 'info'
}

function statusText(status) {
  const map = {
    pending_self: '待自评',
    pending_manager: '待上级评',
    pending_peer: '待协作评',
    pending_summary: '汇总中',
    pending_approval: '审批中',
    published: '已发布',
  }
  return map[status] || status
}

function goScore(item) {
  router.push(`/peer-review/${item.record_id}`)
}
</script>

<style scoped>
.loading-wrap {
  padding: 40px;
}
.empty-wrap {
  padding: 60px 0;
}
.review-card {
  margin-bottom: 16px;
}
.review-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.review-info {
  display: flex;
  gap: 12px;
  align-items: center;
}
.info-text .name {
  font-weight: 600;
  color: #303133;
}
.info-text .meta {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.score-preview {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 12px;
}
.score-row {
  font-size: 13px;
  color: #606266;
  margin-bottom: 4px;
}
.score-row .label {
  color: #909399;
}
.score-row .value {
  color: #303133;
  font-weight: 500;
}
.review-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.due-date {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #909399;
}
</style>
