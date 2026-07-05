<template>
  <div>
    <h2>绩效面谈</h2>
    <el-card class="mt-20" v-loading="loading">
      <div v-if="record">
        <!-- 员工基本信息 -->
        <el-descriptions title="员工基本信息" :column="3" border>
          <el-descriptions-item label="姓名">{{ record.employee_name }}</el-descriptions-item>
          <el-descriptions-item label="工号">{{ record.employee_no }}</el-descriptions-item>
          <el-descriptions-item label="部门">{{ record.department_name }}</el-descriptions-item>
          <el-descriptions-item label="岗位">{{ record.position_name }}</el-descriptions-item>
          <el-descriptions-item label="考核周期">{{ record.cycle_name }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ record.total_score }}</el-descriptions-item>
          <el-descriptions-item label="等级">
            <el-tag :type="gradeType(record.grade)">{{ record.grade }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 各维度得分参考 -->
        <el-descriptions title="各维度得分参考" :column="1" border class="mt-20">
          <el-descriptions-item>
            <el-table :data="dimensionScores" border size="small">
              <el-table-column prop="dimension" label="维度" width="120" />
              <el-table-column prop="self" label="自评" width="120" />
              <el-table-column prop="manager" label="上级" width="120" />
              <el-table-column prop="peer" label="协作" width="120" />
            </el-table>
          </el-descriptions-item>
        </el-descriptions>

        <el-form :model="form" label-width="120px" class="mt-20" :rules="rules" ref="formRef">
          <el-form-item label="面谈时间" prop="interview_time">
            <el-date-picker
              v-model="form.interview_time"
              type="datetime"
              placeholder="选择面谈时间"
              value-format="YYYY-MM-DDTHH:mm:ss"
            />
          </el-form-item>
          <el-form-item label="面谈地点" prop="location">
            <el-input v-model="form.location" placeholder="请输入面谈地点" />
          </el-form-item>
          <el-form-item label="沟通内容" prop="content">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="4"
              placeholder="请输入沟通内容（不少于50字）"
              maxlength="1000"
              show-word-limit
            />
          </el-form-item>
          <el-form-item
            label="改进计划"
            prop="improvement_plan"
            v-if="record.grade === 'C' || record.grade === 'D'"
          >
            <el-input
              v-model="form.improvement_plan"
              type="textarea"
              :rows="3"
              placeholder="C/D等级必须填写改进计划（不少于30字）"
              maxlength="500"
              show-word-limit
            />
            <div class="hint">C/D 等级员工必填，不少于30字</div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSubmit">提交</el-button>
            <el-button @click="goBack">返回</el-button>
          </el-form-item>
        </el-form>
      </div>
      <el-empty v-else description="未找到考核记录" />
    </el-card>
  </div>
</template>

<script>
import { getAssessmentDetail } from '@/api/scores'
import { getInterview, submitInterview } from '@/api/interviews'
import { ElMessageBox } from 'element-plus'

export default {
  name: 'InterviewForm',
  data() {
    const validateInterviewTime = (rule, value, callback) => {
      if (!value) {
        callback(new Error('请选择面谈时间'))
        return
      }
      const selected = new Date(value)
      const now = new Date()
      if (selected > now) {
        callback(new Error('面谈时间不能大于当前时间'))
        return
      }
      callback()
    }

    const validateImprovementPlan = (rule, value, callback) => {
      if (this.record && (this.record.grade === 'C' || this.record.grade === 'D')) {
        if (!value || value.trim().length < 30) {
          callback(new Error('C/D等级必须填写改进计划，不少于30字'))
          return
        }
      }
      callback()
    }

    return {
      loading: false,
      record: null,
      existingInterview: null,
      form: {
        interview_time: '',
        location: '',
        content: '',
        improvement_plan: '',
      },
      rules: {
        interview_time: [
          { required: true, message: '请选择面谈时间', trigger: 'change' },
          { validator: validateInterviewTime, trigger: 'change' },
        ],
        content: [
          { required: true, message: '沟通内容不能为空', trigger: 'blur' },
          { min: 50, message: '沟通内容不少于50字', trigger: 'blur' },
        ],
        improvement_plan: [
          { validator: validateImprovementPlan, trigger: 'blur' },
        ],
      },
    }
  },
  computed: {
    recordId() {
      return this.$route.query.record_id
    },
    dimensionScores() {
      if (!this.record) return []
      const dimensions = ['work_quality', 'work_quantity', 'ability', 'attitude', 'collaboration']
      const labels = { work_quality: '工作质量', work_quantity: '工作数量', ability: '能力', attitude: '态度', collaboration: '协作' }
      const result = []
      for (const key of dimensions) {
        const self = this.record.self_scores?.[key] ?? '—'
        const manager = this.record.manager_scores?.[key] ?? '—'
        const peer = key === 'ability' ? (this.record.peer_scores?.[key] ?? '—') : '—'
        result.push({
          dimension: labels[key] || key,
          self,
          manager,
          peer,
        })
      }
      return result
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
        const [recordRes, interviewRes] = await Promise.all([
          getAssessmentDetail(this.recordId),
          getInterview(this.recordId).catch(() => null),
        ])
        this.record = recordRes
        if (interviewRes) {
          this.existingInterview = interviewRes
          this.form.interview_time = interviewRes.interview_time
          this.form.location = interviewRes.location
          this.form.content = interviewRes.content
          this.form.improvement_plan = interviewRes.improvement_plan || ''
        }
      } catch (e) {
        this.$message.error('加载详情失败')
      } finally {
        this.loading = false
      }
    },
    async handleSubmit() {
      const valid = await this.$refs.formRef.validate().catch(() => false)
      if (!valid) return

      try {
        await ElMessageBox.confirm('确认提交面谈记录？提交后不可修改。', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning',
        })
      } catch {
        return
      }

      const payload = {
        interview_time: this.form.interview_time,
        location: this.form.location,
        content: this.form.content,
        improvement_plan: this.form.improvement_plan,
      }

      try {
        await submitInterview(this.recordId, payload)
        this.$message.success('面谈记录已提交')
        this.goBack()
      } catch (e) {
        this.$message.error(e.response?.data?.message || '提交失败')
      }
    },
    goBack() {
      this.$router.push({ name: 'Interviews' })
    },
    gradeType(grade) {
      const map = { A: 'success', B: 'primary', C: 'warning', D: 'danger' }
      return map[grade] || ''
    },
  },
}
</script>

<style scoped>
.mt-20 { margin-top: 20px; }
.hint { color: #e6a23c; font-size: 12px; margin-top: 5px; }
</style>
