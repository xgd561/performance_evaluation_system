<template>
  <div>
    <h2>{{ isEdit ? '编辑员工' : '新增员工' }}</h2>
    <el-card class="mt-20">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px" style="max-width: 600px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="工号" prop="employee_no">
          <el-input v-model="form.employee_no" placeholder="请输入工号" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="部门" prop="department_id">
          <el-select v-model="form.department_id" placeholder="请选择部门" @change="handleDeptChange">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="岗位" prop="position_id">
          <el-select v-model="form.position_id" placeholder="请选择岗位">
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="职级" prop="level">
          <el-select v-model="form.level" placeholder="请选择职级">
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
            <el-option label="P4" value="P4" />
            <el-option label="P5" value="P5" />
            <el-option label="M1" value="M1" />
            <el-option label="M2" value="M2" />
            <el-option label="M3" value="M3" />
          </el-select>
        </el-form-item>
        <el-form-item label="入职日期" prop="hire_date">
          <el-date-picker v-model="form.hire_date" type="date" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-radio-group v-model="form.is_active">
            <el-radio :label="true">在职</el-radio>
            <el-radio :label="false">离职</el-radio>
          </el-radio-group>
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
import { createEmployee, updateEmployee } from '@/api/employees'
import { listDepartments, listPositions } from '@/api/departments'

export default {
  name: 'EmployeeEdit',
  data() {
    return {
      departments: [],
      positions: [],
      form: {
        name: '',
        employee_no: '',
        department_id: '',
        position_id: '',
        level: '',
        hire_date: '',
        is_active: true,
      },
      rules: {
        name: [{ required: true, message: '姓名不能为空', trigger: 'blur' }],
        employee_no: [{ required: true, message: '工号不能为空', trigger: 'blur' }],
        department_id: [{ required: true, message: '请选择部门', trigger: 'change' }],
        position_id: [{ required: true, message: '请选择岗位', trigger: 'change' }],
        level: [{ required: true, message: '请选择职级', trigger: 'change' }],
      },
    }
  },
  computed: {
    isEdit() {
      return !!this.$route.query.id
    },
  },
  mounted() {
    this.fetchDepartments()
    if (this.isEdit) {
      this.loadEmployeeData()
    }
  },
  methods: {
    async fetchDepartments() {
      try {
        const res = await listDepartments()
        this.departments = res || []
      } catch (e) {
        console.error(e)
      }
    },
    async handleDeptChange(deptId) {
      this.form.position_id = ''
      try {
        const res = await listPositions({ department_id: deptId })
        this.positions = res || []
      } catch (e) {
        this.positions = []
      }
    },
    loadEmployeeData() {
      const row = this.$route.query
      this.form = {
        name: row.name || '',
        employee_no: row.employee_no || '',
        department_id: row.department_id ? Number(row.department_id) : '',
        position_id: row.position_id ? Number(row.position_id) : '',
        level: row.level || '',
        hire_date: row.hire_date || '',
        is_active: row.is_active === 'true' || row.is_active === true,
      }
      if (this.form.department_id) {
        this.handleDeptChange(this.form.department_id)
      }
    },
    async handleSubmit() {
      const valid = await this.$refs.formRef.validate().catch(() => false)
      if (!valid) return
      const payload = { ...this.form }
      if (payload.hire_date) {
        payload.hire_date = new Date(payload.hire_date).toISOString().split('T')[0]
      }
      try {
        if (this.isEdit) {
          await updateEmployee(this.$route.query.id, payload)
          this.$message.success('更新成功')
        } else {
          await createEmployee(payload)
          this.$message.success('创建成功')
        }
        this.goBack()
      } catch (e) {
        this.$message.error(e.response?.data?.message || '保存失败')
      }
    },
    goBack() {
      this.$router.push({ name: 'Employees' })
    },
  },
}
</script>

<style scoped>
.mt-20 { margin-top: 20px; }
</style>
