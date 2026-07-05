<template>
  <div>
    <h2>组织架构</h2>
    <el-card class="mt-20">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-tree
            :data="treeData"
            :props="defaultProps"
            @node-click="handleNodeClick"
            default-expand-all
            highlight-current
            node-key="id"
            ref="treeRef"
          />
        </el-col>
        <el-col :span="16">
          <el-descriptions title="部门详情" :column="2" border v-if="selectedDept">
            <el-descriptions-item label="部门名称">{{ selectedDept.name }}</el-descriptions-item>
            <el-descriptions-item label="部门编码">{{ selectedDept.code }}</el-descriptions-item>
            <el-descriptions-item label="上级部门">{{ selectedDept.parent_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="负责人">{{ selectedDept.leader_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="人数">{{ selectedDept.employee_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="selectedDept.is_active ? 'success' : 'danger'">
                {{ selectedDept.is_active ? '启用' : '停用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ selectedDept.description || '—' }}</el-descriptions-item>
          </el-descriptions>

          <el-divider v-if="selectedDept" content-position="left">岗位列表</el-divider>
          <el-table :data="positions" class="position-table" style="width: 100%" v-if="selectedDept">
            <el-table-column prop="name" label="岗位名称" />
            <el-table-column prop="level" label="职级" width="100" />
            <el-table-column prop="employee_count" label="人数" width="80" />
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button size="small" @click="editPosition(scope.row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider v-if="selectedDept" content-position="left">员工列表</el-divider>
          <el-table :data="employees" class="employee-table" style="width: 100%" v-if="selectedDept" border>
            <el-table-column prop="name" label="姓名" />
            <el-table-column prop="employee_no" label="工号" width="120" />
            <el-table-column prop="position_name" label="岗位" />
            <el-table-column prop="manager_name" label="直属上级" />
          </el-table>
          <el-empty v-if="selectedDept && employees.length === 0" description="暂无员工" />

          <el-empty v-if="!selectedDept" description="请选择一个部门" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script>
import { listDepartments, listPositions } from '@/api/departments'
import { listEmployees } from '@/api/employees'

export default {
  name: 'OrganizationChart',
  data() {
    return {
      departments: [],
      positions: [],
      employees: [],
      selectedDept: null,
      defaultProps: {
        children: 'children',
        label: 'name',
      },
    }
  },
  computed: {
    treeData() {
      return this.buildTree(this.departments)
    },
  },
  mounted() {
    this.fetchDepartments()
  },
  methods: {
    async fetchDepartments() {
      try {
        const res = await listDepartments()
        this.departments = res || []
      } catch (e) {
        this.$message.error('加载部门失败')
      }
    },
    buildTree(list, parentId = null) {
      return list
        .filter(item => item.parent_id === parentId)
        .map(item => ({
          ...item,
          children: this.buildTree(list, item.id),
        }))
    },
    async handleNodeClick(data) {
      this.selectedDept = data
      this.positions = []
      this.employees = []
      try {
        const [posRes, empRes] = await Promise.all([
          listPositions({ department_id: data.id }),
          listEmployees({ department_id: data.id, size: 1000 }),
        ])
        this.positions = posRes || []
        this.employees = empRes?.items || []
      } catch (e) {
        this.positions = []
        this.employees = []
      }
    },
    editPosition(row) {
      this.$message.info('岗位编辑功能待完善：' + row.name)
    },
  },
}
</script>

<style scoped>
.mt-20 { margin-top: 20px; }
</style>
