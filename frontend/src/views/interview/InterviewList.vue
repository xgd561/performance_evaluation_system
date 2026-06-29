<template>
  <div class="interview-list">
    <h2>绩效面谈</h2>
    <el-card>
      <el-table :data="pendingList" v-loading="loading" border>
        <el-table-column prop="employee_name" label="员工姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="cycle_name" label="考核周期" />
        <el-table-column prop="total_score" label="总分" width="100" />
        <el-table-column prop="grade" label="等级" width="80" />
        <el-table-column label="面谈状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.has_interview ? 'success' : 'warning'">
              {{ row.has_interview ? '已记录' : '待面谈' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openDialog(row)">
              {{ row.has_interview ? '查看/编辑' : '记录面谈' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && pendingList.length === 0" description="暂无待面谈记录" />
    </el-card>

    <!-- 面谈记录对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="面谈时间">
          <el-date-picker v-model="form.interview_time" type="datetime" placeholder="选择面谈时间" />
        </el-form-item>
        <el-form-item label="面谈地点">
          <el-input v-model="form.location" placeholder="请输入面谈地点" />
        </el-form-item>
        <el-form-item label="沟通内容">
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="请输入沟通内容" />
        </el-form-item>
        <el-form-item label="改进计划" v-if="currentRow?.grade === 'C' || currentRow?.grade === 'D'">
          <el-input v-model="form.improvement_plan" type="textarea" :rows="3" placeholder="C/D等级必填改进计划" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getPendingInterviews, createInterview, getInterview, updateInterview } from '@/api/interviews'

const pendingList = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('记录面谈')
const currentRow = ref(null)
const form = ref({
  interview_time: '',
  location: '',
  content: '',
  improvement_plan: ''
})

async function loadPending() {
  loading.value = true
  try {
    const res = await getPendingInterviews()
    pendingList.value = res || []
  } catch (e) {
    ElMessage.error('加载待面谈列表失败')
  } finally {
    loading.value = false
  }
}

async function openDialog(row) {
  currentRow.value = row
  dialogTitle.value = row.has_interview ? '编辑面谈记录' : '记录面谈'
  form.value = { interview_time: '', location: '', content: '', improvement_plan: '' }

  if (row.has_interview) {
    try {
      const res = await getInterview(row.record_id)
      form.value = {
        interview_time: res.interview_time || '',
        location: res.location || '',
        content: res.content || '',
        improvement_plan: res.improvement_plan || ''
      }
    } catch (e) {
      ElMessage.error('加载面谈详情失败')
    }
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    const data = {
      interview_time: form.value.interview_time || null,
      location: form.value.location || null,
      content: form.value.content || null,
      improvement_plan: form.value.improvement_plan || null
    }
    if (currentRow.value.has_interview) {
      await updateInterview(currentRow.value.record_id, data)
      ElMessage.success('更新成功')
    } else {
      await createInterview(currentRow.value.record_id, data)
      ElMessage.success('记录成功')
    }
    dialogVisible.value = false
    loadPending()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  }
}

onMounted(loadPending)
</script>

<style scoped>
.interview-list { padding: 20px; }
</style>
