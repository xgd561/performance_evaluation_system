<template>
  <div>
    <h2>{{ isEdit ? '编辑考核周期' : '新增考核周期' }}</h2>
    <el-card class="mt-20">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="140px" style="max-width: 600px">
        <el-form-item label="周期名称" prop="name">
          <el-input v-model="form.name" placeholder="如：2026Q1" />
        </el-form-item>
        <el-form-item label="考核类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio label="quarterly">季度</el-radio>
            <el-radio label="annual">年度</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker v-model="form.start_date" type="date" placeholder="选择开始日期" />
        </el-form-item>
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker v-model="form.end_date" type="date" placeholder="选择结束日期" />
        </el-form-item>
        <el-form-item label="自评截止" prop="self_deadline">
          <el-date-picker v-model="form.self_deadline" type="date" placeholder="自评截止时间" />
        </el-form-item>
        <el-form-item label="上级评分截止" prop="manager_deadline">
          <el-date-picker v-model="form.manager_deadline" type="date" placeholder="上级评分截止时间" />
        </el-form-item>
        <el-form-item label="是否启用" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSubmit">保存</el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { createCycle, updateCycle } from '@/api/cycles'

export default {
  name: 'CycleEdit',
  data() {
    return {
      form: {
        name: '',
        type: 'quarterly',
        start_date: '',
        end_date: '',
        self_deadline: '',
        manager_deadline: '',
        is_active: true,
      },
      rules: {
        name: [{ required: true, message: '周期名称不能为空', trigger: 'blur' }],
        type: [{ required: true, message: '请选择考核类型', trigger: 'change' }],
        start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
        end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
        self_deadline: [{ required: true, message: '请选择自评截止', trigger: 'change' }],
        manager_deadline: [{ required: true, message: '请选择上级评分截止', trigger: 'change' }],
      },
    }
  },
  computed: {
    isEdit() {
      return !!this.$route.query.id
    },
  },
  mounted() {
    if (this.isEdit) {
      this.loadCycleData()
    }
  },
  methods: {
    loadCycleData() {
      const q = this.$route.query
      this.form = {
        name: q.name || '',
        type: q.type || 'quarterly',
        start_date: q.start_date || '',
        end_date: q.end_date || '',
        self_deadline: q.self_deadline || '',
        manager_deadline: q.manager_deadline || '',
        is_active: q.is_active === 'true' || q.is_active === true,
      }
    },
    async handleSubmit() {
      const valid = await this.$refs.formRef.validate().catch(() => false)
      if (!valid) return
      const payload = { ...this.form }
      ;['start_date', 'end_date', 'self_deadline', 'manager_deadline'].forEach(key => {
        if (payload[key]) {
          payload[key] = new Date(payload[key]).toISOString().split('T')[0]
        }
      })
      try {
        if (this.isEdit) {
          await updateCycle(this.$route.query.id, payload)
          this.$message.success('更新成功')
        } else {
          await createCycle(payload)
          this.$message.success('创建成功')
        }
        this.goBack()
      } catch (e) {
        this.$message.error(e.response?.data?.message || '保存失败')
      }
    },
    goBack() {
      this.$router.push({ name: 'Cycles' })
    },
  },
}
</script>

<style scoped>
.mt-20 { margin-top: 20px; }
</style>
