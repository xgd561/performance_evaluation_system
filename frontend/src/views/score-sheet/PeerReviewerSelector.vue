<template>
  <div>
    <el-dialog
      :title="dialogTitle"
      v-model="visible"
      width="700px"
      :close-on-click-modal="false"
      @close="handleClose"
    >
      <el-form :inline="true" class="search-form">
        <el-form-item>
          <el-input v-model="searchKeyword" placeholder="姓名/工号" clearable />
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchDepartment" placeholder="全部部门" clearable>
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table
        :data="filteredCandidates"
        style="width: 100%"
        height="300px"
        @selection-change="handleSelectionChange"
        ref="multipleTable"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="department_name" label="部门" />
        <el-table-column prop="position_name" label="岗位" />
      </el-table>

      <div class="selected-area">
        <strong>已选协作人（{{ selected.length }}/3）：</strong>
        <el-tag
          v-for="s in selected"
          :key="s.id"
          closable
          @close="removeSelected(s)"
          class="selected-tag"
        >
          {{ s.name }}（{{ s.employee_no }}）
        </el-tag>
        <span v-if="selected.length === 0" class="text-muted">未选择</span>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleClose">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :disabled="selected.length === 0 || selected.length > 3">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { listEmployees } from '@/api/employees'
import { listDepartments } from '@/api/departments'

export default {
  name: 'PeerReviewerSelector',
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    excludeEmployeeId: {
      type: Number,
      default: null,
    },
    existingReviewerIds: {
      type: Array,
      default: () => [],
    },
  },
  emits: ['update:modelValue', 'confirm'],
  data() {
    return {
      visible: false,
      candidates: [],
      departments: [],
      searchKeyword: '',
      searchDepartment: '',
      selected: [],
    }
  },
  computed: {
    dialogTitle() {
      return '选择协作评分人'
    },
    filteredCandidates() {
      let data = this.candidates.filter(c => c.id !== this.excludeEmployeeId)
      if (this.searchKeyword) {
        const kw = this.searchKeyword.toLowerCase()
        data = data.filter(c =>
          (c.name && c.name.toLowerCase().includes(kw)) ||
          (c.employee_no && c.employee_no.toLowerCase().includes(kw))
        )
      }
      if (this.searchDepartment) {
        data = data.filter(c => c.department_id === this.searchDepartment)
      }
      return data
    },
  },
  watch: {
    modelValue(val) {
      this.visible = val
      if (val) {
        this.fetchData()
        this.fetchDepartments()
      }
    },
  },
  methods: {
    async fetchData() {
      try {
        const res = await listEmployees({ page: 1, size: 1000, is_active: true })
        this.candidates = res.items || []
      } catch (e) {
        this.$message.error('加载候选协作人失败')
      }
    },
    async fetchDepartments() {
      try {
        const res = await listDepartments()
        this.departments = res || []
      } catch (e) {
        console.error(e)
      }
    },
    handleSearch() {
      // 前端筛选
    },
    handleSelectionChange(val) {
      if (val.length > 3) {
        this.$message.warning('最多选择 3 位协作人')
        const allowed = val.slice(0, 3)
        this.$refs.multipleTable.clearSelection()
        allowed.forEach(row => this.$refs.multipleTable.toggleRowSelection(row, true))
        this.selected = allowed
        return
      }
      this.selected = val
    },
    removeSelected(item) {
      this.selected = this.selected.filter(s => s.id !== item.id)
      this.$refs.multipleTable.toggleRowSelection(item, false)
    },
    handleSubmit() {
      if (this.selected.length === 0) {
        this.$message.warning('请至少选择 1 位协作人')
        return
      }
      if (this.selected.length > 3) {
        this.$message.warning('最多选择 3 位协作人')
        return
      }
      this.$emit('confirm', this.selected.map(s => s.id))
      this.handleClose()
    },
    handleClose() {
      this.selected = []
      this.searchKeyword = ''
      this.searchDepartment = ''
      this.$emit('update:modelValue', false)
    },
  },
}
</script>

<style scoped>
.search-form { margin-bottom: 15px; }
.selected-area { margin-top: 15px; padding: 10px; background: #f5f7fa; border-radius: 4px; }
.selected-tag { margin-right: 8px; margin-bottom: 5px; }
.text-muted { color: #909399; }
</style>
