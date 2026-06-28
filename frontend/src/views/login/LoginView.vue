<template>
  <div class=login-container>
    <el-card class=login-box>
      <h2 class=title>绩效考核评分系统</h2>
      <el-form :model=form :rules=rules ref=formRef @keyup.enter=handleLogin>
        <el-form-item prop=username>
          <el-input v-model=form.username placeholder=用户名 prefix-icon=User />
        </el-form-item>
        <el-form-item prop=password>
          <el-input v-model=form.password type=password placeholder=密码 prefix-icon=Lock show-password />
        </el-form-item>
        <el-form-item>
          <el-button type=primary class=login-btn :loading=loading @click=handleLogin>登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.doLogin(form)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e) {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f0f2f5;
}
.login-box {
  width: 400px;
}
.title {
  text-align: center;
  margin-bottom: 24px;
  color: #303133;
}
.login-btn {
  width: 100%;
}
</style>
