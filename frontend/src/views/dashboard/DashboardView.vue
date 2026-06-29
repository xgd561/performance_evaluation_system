<template>
  <div>
    <h2>仪表盘</h2>
    <!-- Admin / HR 通用统计 -->
    <el-row :gutter="20" v-if="userRole === 'admin' || userRole === 'hr'">
      <el-col :span="6" v-for="item in stats" :key="item.label">
        <el-card>
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value">{{ item.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Manager 专属统计 -->
    <el-row :gutter="20" v-if="userRole === 'manager'">
      <el-col :span="6">
        <el-card>
          <div class="stat-label">下属人数</div>
          <div class="stat-value">{{ managerStats.subordinate_count }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-label">待评分</div>
          <div class="stat-value" style="color: #e6a23c">{{ managerStats.to_review }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-label">待审批</div>
          <div class="stat-value" style="color: #f56c6c">{{ managerStats.pending_approval }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-label">待面谈</div>
          <div class="stat-value" style="color: #67c23a">{{ managerStats.pending_interview }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Peer 专属统计 -->
    <el-row :gutter="20" v-if="userRole === 'peer'">
      <el-col :span="8">
        <el-card>
          <div class="stat-label">待协作评分</div>
          <div class="stat-value" style="color: #e6a23c">{{ peerStats.pending_reviews }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="stat-label">已完成评分</div>
          <div class="stat-value" style="color: #67c23a">{{ peerStats.completed_reviews }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="stat-label">总协作评分</div>
          <div class="stat-value">{{ peerStats.total_reviews }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Employee 专属统计 -->
    <el-row :gutter="20" v-if="userRole === 'employee'">
      <el-col :span="6">
        <el-card>
          <div class="stat-label">考核记录</div>
          <div class="stat-value">{{ employeeStats.total_records }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-label">待自评</div>
          <div class="stat-value" style="color: #e6a23c">{{ employeeStats.pending_self }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-label">当前考核</div>
          <div class="stat-value" style="color: #409eff">{{ employeeStats.current_cycle ? employeeStats.current_cycle.cycle_name : '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-label">当前状态</div>
          <div class="stat-value" style="color: #67c23a">{{ statusText(employeeStats.self_status) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作入口 -->
    <el-card class="mt-20" v-if="userRole === 'manager'">
      <div class="card-title">快捷操作</div>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-button type="primary" size="large" style="width: 100%" @click="$router.push('/score-sheet')">
            批量评分
          </el-button>
        </el-col>
        <el-col :span="8">
          <el-button type="warning" size="large" style="width: 100%" @click="$router.push('/approval-workbench')">
            审批下属绩效
          </el-button>
        </el-col>
        <el-col :span="8">
          <el-button type="success" size="large" style="width: 100%" @click="$router.push('/interviews')">
            记录面谈
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="mt-20" v-if="userRole === 'peer'">
      <div class="card-title">快捷操作</div>
      <el-row :gutter="20">
        <el-col :span="24">
          <el-button type="primary" size="large" style="width: 100%" @click="$router.push('/peer-review')">
            进入协作评分
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="mt-20" v-if="userRole === 'employee'">
      <div class="card-title">快捷操作</div>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-button type="primary" size="large" style="width: 100%" @click="$router.push('/self-assessment')">
            进入自评
          </el-button>
        </el-col>
        <el-col :span="8">
          <el-button type="success" size="large" style="width: 100%" @click="$router.push('/my-performance')">
            查看历史绩效
          </el-button>
        </el-col>
        <el-col :span="8">
          <el-button type="warning" size="large" style="width: 100%" @click="$router.push('/appeal')">
            发起申诉
          </el-button>
        </el-col>
      </el-row>
    </el-card>

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
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { listCycles } from '@/api/cycles'
import { listEmployees } from '@/api/employees'
import { listDepartments } from '@/api/departments'
import request from '@/api/request'

const router = useRouter()
const authStore = useAuthStore()
const userRole = computed(() => authStore.user?.role)

const stats = ref([
  { label: '员工总数', value: 0 },
  { label: '部门数量', value: 0 },
  { label: '考核周期', value: 0 },
  { label: '进行中', value: 0 },
])

const managerStats = ref({
  subordinate_count: 0,
  to_review: 0,
  pending_approval: 0,
  pending_interview: 0,
})

const peerStats = ref({
  pending_reviews: 0,
  completed_reviews: 0,
  total_reviews: 0,
})

const employeeStats = ref({
  total_records: 0,
  pending_self: 0,
  current_cycle: null,
  self_status: 'none',
})

const recentCycles = ref([])

onMounted(async () => {
  try {
    const cycleRes = await listCycles()
    const cycles = cycleRes || []
    recentCycles.value = cycles.slice(0, 5)

    if (userRole.value === 'manager') {
      const res = await request.get('/dashboard/manager')
      managerStats.value = res || managerStats.value
    } else if (userRole.value === 'peer') {
      const res = await request.get('/dashboard/peer')
      peerStats.value = res || peerStats.value
    } else if (userRole.value === 'employee') {
      const res = await request.get('/dashboard/employee')
      employeeStats.value = res || employeeStats.value
    } else {
      const empRes = await listEmployees({ page: 1, size: 1 })
      stats.value[0].value = empRes.total || 0
      const deptRes = await listDepartments()
      stats.value[1].value = (deptRes.length || deptRes.items?.length) || 0
      stats.value[2].value = cycles.length
      const active = cycles.filter(c => c.status !== 'not_started').length
      stats.value[3].value = active
    }
  } catch (e) {
    console.error(e)
  }
})

function statusText(status) {
  const map = {
    pending_self: '待自评',
    pending_manager: '待上级评',
    pending_peer: '待协作评',
    pending_summary: '汇总中',
    pending_approval: '审批中',
    published: '已发布',
    none: '无',
  }
  return map[status] || status
}
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
