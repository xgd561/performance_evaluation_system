<template>
  <div class="login-container">
    <el-card class="login-box" shadow="hover">
      <h2 class="title">绩效考核评分系统</h2>
      <el-form
        :model="form"
        :rules="rules"
        ref="formRef"
        @keyup.enter="handleLogin"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            size="large"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.rememberMe">记住我</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            class="login-btn"
            :loading="loading"
            size="large"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 首次登录强制修改密码弹窗 -->
    <el-dialog
      v-model="showChangePasswordDialog"
      title="首次登录 — 修改密码"
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      draggable
    >
      <p class="dialog-tip">检测到您是首次登录，请先修改初始密码。</p>
      <el-form
        :model="pwdForm"
        :rules="pwdRules"
        ref="pwdFormRef"
        @keyup.enter="handleChangePassword"
        label-width="80px"
      >
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="pwdForm.newPassword"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="pwdForm.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
      </el-form>

      <!-- 密码强度提示 -->
      <div class="strength-bar" v-if="pwdForm.newPassword">
        <div class="strength-label">密码强度：{{ strengthLabel }}</div>
        <div class="strength-track">
          <div class="strength-fill" :style="strengthStyle" :class="strengthClass"></div>
        </div>
        <ul class="strength-tips">
          <li :class="{ ok: hasLength }">8-16 位字符</li>
          <li :class="{ ok: hasLower }">包含小写字母</li>
          <li :class="{ ok: hasUpper }">包含大写字母</li>
          <li :class="{ ok: hasDigit }">包含数字</li>
          <li :class="{ ok: hasSpecial }">包含特殊字符 (!@#$%^&*)</li>
        </ul>
      </div>

      <template #footer>
        <el-button type="primary" :loading="pwdLoading" @click="handleChangePassword">
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  rememberMe: false,
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
    const res = await authStore.login({
      username: form.username,
      password: form.password,
      remember_me: form.rememberMe,
    })

    if (res.user?.is_first_login) {
      showChangePasswordDialog.value = true
      // 预填用户名，用于修改密码时旧密码就是当前密码
      pwdForm.oldPassword = form.password
      return
    }

    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e) {
    // request.js 拦截器已统一弹出错误提示
    console.error('登录失败', e)
  } finally {
    loading.value = false
  }
}

/* ---------- 首次登录修改密码 ---------- */
const showChangePasswordDialog = ref(false)
const pwdFormRef = ref()
const pwdLoading = ref(false)

const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const pwdRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!value || value.length < 8 || value.length > 16) {
          callback(new Error('密码长度应为 8-16 位'))
          return
        }
        if (!hasLower.value || !hasUpper.value || !hasDigit.value || !hasSpecial.value) {
          callback(new Error('密码必须包含大小写字母、数字和特殊字符'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== pwdForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

// 密码强度计算
const hasLength = computed(() => pwdForm.newPassword.length >= 8 && pwdForm.newPassword.length <= 16)
const hasLower = computed(() => /[a-z]/.test(pwdForm.newPassword))
const hasUpper = computed(() => /[A-Z]/.test(pwdForm.newPassword))
const hasDigit = computed(() => /\d/.test(pwdForm.newPassword))
const hasSpecial = computed(() => /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pwdForm.newPassword))

const strengthScore = computed(() => {
  let score = 0
  if (hasLength.value) score++
  if (hasLower.value) score++
  if (hasUpper.value) score++
  if (hasDigit.value) score++
  if (hasSpecial.value) score++
  return score
})

const strengthLabel = computed(() => {
  const labels = ['', '弱', '弱', '中', '强', '极强']
  return labels[strengthScore.value] || '弱'
})

const strengthClass = computed(() => {
  const classes = ['', 'weak', 'weak', 'medium', 'strong', 'strong']
  return classes[strengthScore.value] || 'weak'
})

const strengthStyle = computed(() => ({
  width: `${(strengthScore.value / 5) * 100}%`,
}))

async function handleChangePassword() {
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return
  pwdLoading.value = true
  try {
    await authStore.changePassword({
      old_password: pwdForm.oldPassword,
      new_password: pwdForm.newPassword,
    })
    ElMessage.success('密码修改成功，请重新登录')
    showChangePasswordDialog.value = false
    authStore.logout()
    // 清空表单
    form.password = ''
    pwdForm.newPassword = ''
    pwdForm.confirmPassword = ''
  } catch (e) {
    console.error('修改密码失败', e)
  } finally {
    pwdLoading.value = false
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
  width: 420px;
  padding: 20px 30px 10px;
}

.title {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
  font-size: 22px;
  font-weight: 600;
}

.login-btn {
  width: 100%;
}

.dialog-tip {
  color: #606266;
  margin-bottom: 16px;
  font-size: 14px;
}

/* 密码强度条 */
.strength-bar {
  margin-top: 12px;
}

.strength-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
}

.strength-track {
  height: 6px;
  background: #e4e7ed;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.strength-fill {
  height: 100%;
  transition: width 0.3s, background-color 0.3s;
}

.strength-fill.weak {
  background-color: #f56c6c;
}

.strength-fill.medium {
  background-color: #e6a23c;
}

.strength-fill.strong {
  background-color: #67c23a;
}

.strength-tips {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 12px;
  color: #909399;
}

.strength-tips li {
  padding-left: 16px;
  position: relative;
  margin-bottom: 4px;
}

.strength-tips li::before {
  content: '○';
  position: absolute;
  left: 0;
  font-size: 10px;
}

.strength-tips li.ok {
  color: #67c23a;
}

.strength-tips li.ok::before {
  content: '✓';
}
</style>
