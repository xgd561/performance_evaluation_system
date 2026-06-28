<template>
  <div>
    <h2>仪表盘</h2>
    <el-row :gutter="20">
      <el-col :span="6" v-for="item in stats" :key="item.label">
        <el-card>
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value">{{ item.value }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card class="mt-20">
      <div class="card-title">最近考核周期</div>
      <el-table :data="recentCycles" style="width: 100%">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="type" label="类型" />
        <el-table-column prop="status" label="状态" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listCycles, getCycleProgress } from '@/api/cycles'
import { listEmployees } from '@/api/employees'
import { listDepartments } from '@/api/departments'

const stats = ref([
  { label: '员工总数', value: 0 },
  { label: '部门数量', value: 0 },
  { label: '考核周期', value: 0 },
  { label: '进行中', value: 0 },
])

const recentCycles = ref([])

onMounted(async () => {
  try {
    const empRes = await listEmployees({ page: 1, size: 1 })
    stats.value[0].value = empRes.total || 0

    const deptRes = await listDepartments()
    stats.value[1].value = (deptRes.length || deptRes.items?.length) || 0

    const cycleRes = await listCycles()
    const cycles = cycleRes || []
    stats.value[2].value = cycles.length
    const active = cycles.filter(c => c.status !== 'not_started').length
    stats.value[3].value = active

    recentCycles.value = cycles.slice(0, 5)
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.mt-20 {
  margin-top: 20px;
}
.stat-label {
  color: #909399;
  font-size: 14px;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-top: 8px;
}
.card-title {
  font-weight: bold;
  margin-bottom: 16px;
}
</style>
