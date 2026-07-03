<template>
  <PageContainer title="协作评分待办">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="reviews.length === 0" class="empty-wrap">
      <el-empty description="暂无协作评分记录" />
    </div>

    <div v-else>
      <!-- 待办评分 -->
      <div v-if="pendingReviews.length > 0" class="section">
        <h3 class="section-title">待办评分</h3>
        <el-card
          v-for="item in pendingReviews"
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

      <!-- 已评分记录 -->
      <div v-if="completedReviews.length > 0" class="section completed-section">
        <h3 class="section-title">已评分记录</h3>
        <el-card
          v-for="item in completedReviews"
          :key="item.id"
          class="review-card completed"
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
            <el-tag type="success" size="small">已评分</el-tag>
          </div>

          <el-divider />

          <div class="score-preview my-score">
            <div class="score-row">
              <span class="label">我的协作评分：</span>
              <span class="value">
                <el-tag type="success" size="small">能力 {{ item.peer_scores?.ability ?? '-' }} 分</el-tag>
              </span>
            </div>
          </div>

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
            <el-button @click="goScore(item)">
              查看
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMyPeerReviews } from '@/api/scores'

const router = useRouter()
const loading = ref(false)
const reviews = ref([])

function sortByDueDate(list) {
  return [...list].sort((a, b) => {
    if (!a.peer_due_date && !b.peer_due_date) return 0
    if (!a.peer_due_date) return 1
    if (!b.peer_due_date) return -1
    return new Date(a.peer_due_date) - new Date(b.peer_due_date)
  })
}

const pendingReviews = computed(() =>
  sortByDueDate(reviews.value.filter(r => r.peer_relation_status !== 'completed'))
)
const completedReviews = computed(() =>
  sortByDueDate(reviews.value.filter(r => r.peer_relation_status === 'completed'))
)

onMounted(async () => {
  loading.value = true
  try {
    const res = await getMyPeerReviews()
    reviews.value = res?.items || []
  } catch (e) {
    console.error(e)
    ElMessage.error('获取协作评分列表失败')
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
.section {
  margin-bottom: 24px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px;
  padding-left: 4px;
}
.completed-section .section-title {
  color: #67c23a;
}
.review-card {
  margin-bottom: 16px;
}
.review-card.completed {
  background: #f6ffed;
  border-color: #b7eb8f;
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
.score-preview.my-score {
  background: #e6f7ff;
  border: 1px solid #91d5ff;
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
