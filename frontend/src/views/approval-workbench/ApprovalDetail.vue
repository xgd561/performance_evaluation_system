<template>
  <div class="approval-detail">
    <!-- 面包屑 -->
    <el-breadcrumb class="breadcrumb" separator=">">
      <el-breadcrumb-item :to="{ name: 'ApprovalWorkbench' }">审批工作台</el-breadcrumb-item>
      <el-breadcrumb-item>审批详情</el-breadcrumb-item>
    </el-breadcrumb>

    <h2>审批详情</h2>
    <el-card v-loading="loading">
      <div v-if="detail">
        <el-row :gutter="20">
          <!-- 左侧：评分详情 + 协作评分 + 历史绩效 -->
          <el-col :span="16">
            <!-- 员工基本信息 -->
            <el-descriptions title="员工基本信息" :column="3" border>
              <el-descriptions-item label="姓名">{{ detail.record.employee_name }}</el-descriptions-item>
              <el-descriptions-item label="工号">{{ detail.record.employee_no }}</el-descriptions-item>
              <el-descriptions-item label="部门">{{ detail.record.department_name }}</el-descriptions-item>
              <el-descriptions-item label="岗位">{{ detail.record.position_name }}</el-descriptions-item>
              <el-descriptions-item label="周期">{{ detail.record.cycle_name }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="statusType(detail.record.status)">{{ statusText(detail.record.status) }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 评分对比表格 -->
            <el-descriptions title="评分详情对比" :column="1" border class="mt-20">
              <el-descriptions-item>
                <el-table :data="dimensionScores" border size="small">
                  <el-table-column prop="dimension" label="维度" width="120" />
                  <el-table-column prop="self" label="自评" width="120">
                    <template #default="{ row }">
                      <span :class="row.selfClass">{{ row.self }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="manager" label="上级" width="120">
                    <template #default="{ row }">
                      <span :class="row.managerClass">{{ row.manager }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="peer" label="协作" width="120">
                    <template #default="{ row }">
                      <span>{{ row.peer }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="diff" label="差异" width="120">
                    <template #default="{ row }">
                      <span :class="row.diffClass">{{ row.diff }}</span>
                    </template>
                  </el-table-column>
                </el-table>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 加权结果 -->
            <el-descriptions title="加权计算结果" :column="3" border class="mt-20">
              <el-descriptions-item label="业绩维度">{{ detail.record.weighted_performance }}</el-descriptions-item>
              <el-descriptions-item label="能力维度">{{ detail.record.weighted_ability }}</el-descriptions-item>
              <el-descriptions-item label="态度维度">{{ detail.record.weighted_attitude }}</el-descriptions-item>
              <el-descriptions-item label="总分" :span="2">
                <strong :class="scoreClass(detail.record.total_score)">{{ detail.record.total_score }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="等级">
                <el-tag :type="gradeType(detail.record.grade)">{{ detail.record.grade }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 异常提示区 -->
            <div class="mt-20">
              <el-alert
                v-if="detail.record.is_force_adjusted"
                :title="`强制分布调整：原等级 ${detail.record.original_grade} → 调整后 ${detail.record.grade}`"
                type="error"
                show-icon
                class="mb-10"
              />
              <el-alert
                v-if="isAbnormalScore"
                :title="`异常分数（总分：${detail.record.total_score}），请关注`"
                type="error"
                show-icon
                class="mb-10"
              />
              <el-alert
                v-if="hasLargeDiff"
                title="自评与上级评分差异较大，请重点关注"
                type="warning"
                show-icon
                class="mb-10"
              />
            </div>

            <!-- 协作评分明细 -->
            <el-card class="mt-20" v-if="detail.peer_comments && detail.peer_comments.length">
              <template #header>
                <span>协作评分明细</span>
              </template>
              <el-table :data="detail.peer_comments" border size="small">
                <el-table-column prop="reviewer_name" label="评价人" width="150" />
                <el-table-column prop="score" label="评分" width="100" />
                <el-table-column prop="comment" label="评语" />
              </el-table>
            </el-card>

            <!-- 历史绩效 -->
            <el-card class="mt-20" v-if="detail.history && detail.history.length">
              <template #header>
                <span>历史绩效（近3周期）</span>
              </template>
              <el-timeline>
                <el-timeline-item
                  v-for="h in detail.history"
                  :key="h.cycle_name"
                  :type="gradeType(h.grade)"
                  :timestamp="h.cycle_name"
                >
                  总分：<strong>{{ h.total_score }}</strong>，等级：<el-tag :type="gradeType(h.grade)" size="small">{{ h.grade }}</el-tag>
                </el-timeline-item>
              </el-timeline>
            </el-card>
          </el-col>

          <!-- 右侧：审批历史 + 审批操作 -->
          <el-col :span="8">
            <!-- 审批历史 -->
            <el-card class="mb-20" v-if="detail.approval_history && detail.approval_history.length">
              <template #header>
                <span>审批历史</span>
              </template>
              <el-timeline>
                <el-timeline-item
                  v-for="item in detail.approval_history"
                  :key="item.created_at"
                  :type="approvalActionType(item.action)"
                  :timestamp="formatTime(item.created_at)"
                >
                  <strong>{{ approvalActionText(item.action) }}</strong>
                  <div class="approval-step">步骤：Step {{ item.step_index }}</div>
                  <div class="approval-comment" v-if="item.comment">意见：{{ item.comment }}</div>
                </el-timeline-item>
              </el-timeline>
            </el-card>

            <!-- 审批操作区 -->
            <el-card v-if="canShowActions" class="approval-actions">
              <template #header>
                <span>审批操作</span>
              </template>
              <el-form :model="approvalForm" :rules="approvalRules" ref="approvalFormRef" label-width="100px">
                <el-form-item label="审批意见" prop="comment">
                  <el-input
                    v-model="approvalForm.comment"
                    type="textarea"
                    :rows="3"
                    placeholder="请输入审批意见（不少于10字）"
                    maxlength="500"
                    show-word-limit
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="success" @click="handleApprove" :loading="submitting">通过</el-button>
                  <el-button type="danger" @click="handleReject" :loading="submitting">驳回</el-button>
                  <el-button type="warning" @click="handleRollback" :loading="submitting">打回重评</el-button>
                </el-form-item>
              </el-form>
            </el-card>

            <el-card v-else-if="detail.record.status !== 'pending_approval'">
              <el-empty description="当前记录不可审批" />
            </el-card>
          </el-col>
        </el-row>

        <!-- 底部部门等级分布 -->
        <el-card class="mt-20" v-if="deptDistribution">
          <template #header>
            <span>部门当前等级分布</span>
          </template>
          <el-row :gutter="20">
            <el-col :span="6" v-for="item in deptDistribution.grades" :key="item.grade">
              <div class="grade-distribution-item">
                <el-tag :type="gradeType(item.grade)" size="large">{{ item.grade }}</el-tag>
                <span class="grade-count">{{ item.count }} 人</span>
                <span class="grade-ratio">{{ item.ratio }}%</span>
                <el-icon v-if="item.is_over_limit" class="over-limit-icon"><WarningFilled /></el-icon>
              </div>
            </el-col>
          </el-row>
        </el-card>
        <el-card class="mt-20" v-else>
          <template #header>
            <span>部门当前等级分布</span>
          </template>
          <el-empty description="暂无部门分布数据" />
        </el-card>
      </div>
      <el-empty v-else description="未找到考核记录" />
    </el-card>
  </div>
</template>

<script>
import { getApprovalDetail, getDepartmentDistribution, approveRecord, rejectRecord, rollbackRecord } from '@/api/approvals'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'

export default {
  name: 'ApprovalDetail',
  components: {
    WarningFilled,
  },
  data() {
    return {
      loading: false,
      submitting: false,
      detail: null,
      deptDistribution: null,
      approvalForm: {
        comment: '',
      },
      approvalRules: {
        comment: [
          { required: true, message: '请输入审批意见', trigger: 'blur' },
          { min: 10, message: '审批意见不少于10字', trigger: 'blur' },
        ],
      },
    }
  },
  computed: {
    recordId() {
      return this.$route.query.record_id
    },
    canShowActions() {
      return this.detail && this.detail.record && this.detail.record.status === 'pending_approval'
    },
    dimensionScores() {
      if (!this.detail || !this.detail.record) return []
      const record = this.detail.record
      const dims = [
        { key: 'performance', label: '业绩' },
        { key: 'ability', label: '能力' },
        { key: 'attitude', label: '态度' },
      ]
      return dims.map(d => {
        const selfScore = record.self_scores?.[d.key]
        const managerScore = record.manager_scores?.[d.key]
        const peerScore = d.key === 'ability' ? (record.peer_scores?.[d.key] ?? '—') : '—'
        const diff = (selfScore != null && managerScore != null) ? Math.abs(selfScore - managerScore) : null
        const isLargeDiff = diff != null && diff > 20
        return {
          dimension: d.label,
          self: selfScore ?? '—',
          manager: managerScore ?? '—',
          peer: peerScore,
          diff: diff != null ? diff : '—',
          selfClass: isLargeDiff ? 'diff-warning' : '',
          managerClass: isLargeDiff ? 'diff-warning' : '',
          diffClass: isLargeDiff ? 'diff-warning' : '',
        }
      })
    },
    isAbnormalScore() {
      if (!this.detail || !this.detail.record) return false
      const score = this.detail.record.total_score
      return score != null && (score < 60 || score > 98)
    },
    hasLargeDiff() {
      return this.dimensionScores.some(d => d.diffClass === 'diff-warning')
    },
  },
  mounted() {
    if (this.recordId) {
      this.fetchDetail()
    }
  },
  methods: {
    async fetchDetail() {
      this.loading = true
      try {
        const res = await getApprovalDetail(this.recordId)
        this.detail = res
        // 加载部门分布数据
        if (res.record && res.record.department_id) {
          this.loadDepartmentDistribution(res.record.department_id)
        }
      } catch (e) {
        ElMessage.error('加载详情失败')
      } finally {
        this.loading = false
      }
    },
    async loadDepartmentDistribution(departmentId) {
      try {
        const res = await getDepartmentDistribution(departmentId)
        this.deptDistribution = res && res.grades && res.grades.length ? res : null
      } catch (e) {
        // 分布数据属辅助信息，失败时降级为「暂无数据」，但保留日志便于排查
        console.warn('[ApprovalDetail] 加载部门等级分布失败', e)
        this.deptDistribution = null
      }
    },
    async handleApprove() {
      const valid = await this.$refs.approvalFormRef.validate().catch(() => false)
      if (!valid) return
      try {
        await ElMessageBox.confirm('确认通过该审批？', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning',
        })
      } catch {
        return
      }
      this.submitting = true
      try {
        await approveRecord(this.recordId, { comment: this.approvalForm.comment })
        ElMessage.success('审批通过')
        this.approvalForm.comment = ''
        await this.fetchDetail()
      } catch (e) {
        ElMessage.error(e.response?.data?.message || '审批失败')
      } finally {
        this.submitting = false
      }
    },
    async handleReject() {
      const valid = await this.$refs.approvalFormRef.validate().catch(() => false)
      if (!valid) return
      try {
        await ElMessageBox.confirm('确认驳回该审批？', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning',
        })
      } catch {
        return
      }
      this.submitting = true
      try {
        await rejectRecord(this.recordId, { reason: this.approvalForm.comment })
        ElMessage.success('已驳回')
        this.approvalForm.comment = ''
        await this.fetchDetail()
      } catch (e) {
        ElMessage.error(e.response?.data?.message || '驳回失败')
      } finally {
        this.submitting = false
      }
    },
    async handleRollback() {
      const valid = await this.$refs.approvalFormRef.validate().catch(() => false)
      if (!valid) return
      try {
        await ElMessageBox.confirm('确认打回重评？该操作将清空上级评分。', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning',
        })
      } catch {
        return
      }
      this.submitting = true
      try {
        await rollbackRecord(this.recordId, { reason: this.approvalForm.comment })
        ElMessage.success('已打回重评')
        this.approvalForm.comment = ''
        await this.fetchDetail()
      } catch (e) {
        ElMessage.error(e.response?.data?.message || '打回失败')
      } finally {
        this.submitting = false
      }
    },
    goBack() {
      this.$router.push({ name: 'ApprovalWorkbench' })
    },
    statusType(status) {
      const map = { pending_approval: 'warning', pending_interview: 'info', published: 'success', pending_manager: 'danger' }
      return map[status] || ''
    },
    statusText(status) {
      const map = { pending_approval: '待审批', pending_interview: '待面谈', published: '已发布', pending_manager: '待上级评分' }
      return map[status] || status
    },
    scoreClass(score) {
      if (score >= 90) return 'text-success'
      if (score >= 80) return 'text-primary'
      if (score >= 60) return 'text-warning'
      return 'text-danger'
    },
    gradeType(grade) {
      const map = { A: 'success', B: 'primary', C: 'warning', D: 'danger' }
      return map[grade] || ''
    },
    approvalActionType(action) {
      const map = { approve_step1: 'success', approve_step2: 'success', reject: 'danger', rollback: 'warning' }
      return map[action] || 'primary'
    },
    approvalActionText(action) {
      const map = {
        approve_step1: '部门负责人审批通过',
        approve_step2: 'HR负责人审批通过',
        reject: '驳回',
        rollback: '打回重评',
      }
      return map[action] || action
    },
    formatTime(time) {
      if (!time) return ''
      return new Date(time).toLocaleString('zh-CN')
    },
  },
}
</script>

<style scoped>
.approval-detail { padding: 20px; }
.breadcrumb { margin-bottom: 20px; }
.mt-20 { margin-top: 20px; }
.mb-10 { margin-bottom: 10px; }
.mb-20 { margin-bottom: 20px; }
.approval-actions { background: #f5f7fa; }
.approval-step { font-size: 12px; color: #909399; margin-top: 4px; }
.approval-comment { font-size: 12px; color: #606266; margin-top: 4px; }
.text-success { color: #67c23a; }
.text-primary { color: #409eff; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; }
.diff-warning { background-color: #fdf6ec; color: #e6a23c; font-weight: bold; padding: 2px 4px; border-radius: 4px; }
.grade-distribution-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-bottom: 10px;
}
.grade-count { font-size: 14px; color: #606266; }
.grade-ratio { font-size: 14px; color: #909399; }
.over-limit-icon { color: #f56c6c; margin-left: auto; }
</style>
