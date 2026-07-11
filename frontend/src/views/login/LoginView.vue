<template>
  <div class="login-container">
    <div class="login-wrapper">
      <div class="login-brand">
        <div class="brand-icon-large">
          <el-icon :size="40"><Histogram /></el-icon>
        </div>
        <div class="brand-title">绩效考核评分系统</div>
        <div class="brand-subtitle">PERFORMANCE EVALUATION SYSTEM</div>
        <div class="brand-divider"></div>
        <div class="brand-desc">
          科学、公正、高效的数字化绩效管理解决方案
        </div>
      </div>

      <div class="login-card">
        <div class="login-card-header">
          <div class="login-card-title">欢迎登录</div>
          <div class="login-card-subtitle">请输入您的账号信息</div>
        </div>

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
              class="login-input"
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
              class="login-input"
            />
          </el-form-item>
          <el-form-item>
            <div class="login-options">
              <el-checkbox v-model="form.rememberMe" class="remember-checkbox">记住我</el-checkbox>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              class="login-btn"
              :loading="loading"
              size="large"
              @click="handleLogin"
            >
              <span class="btn-text">登录</span>
              <el-icon class="btn-icon"><ArrowRight /></el-icon>
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 首次登录强制修改密码弹窗 -->
    <el-dialog
      v-model="showChangePasswordDialog"
      title="首次登录 — 修改密码"
      width="420px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      draggable
      class="password-dialog"
    >
      <div class="dialog-tip">
        <el-icon class="tip-icon"><InfoFilled /></el-icon>
        检测到您是首次登录，请先修改初始密码。
      </div>
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
        <div class="strength-header">
          <span class="strength-label">密码强度</span>
          <span class="strength-value" :class="strengthClass">{{ strengthLabel }}</span>
        </div>
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
        <el-button type="primary" :loading="pwdLoading" @click="handleChangePassword" class="confirm-btn">
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
import { User, Lock, ArrowRight, Histogram, InfoFilled } from '@element-plus/icons-vue'
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
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 40%, #312e81 100%);
  position: relative;
  overflow: hidden;
  padding: 24px;
}

/* Decorative background elements */
.login-container::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -20%;
  width: 80%;
  height: 150%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
  pointer-events: none;
}

.login-container::after {
  content: '';
  position: absolute;
  bottom: -30%;
  right: -10%;
  width: 60%;
  height: 100%;
  background: radial-gradient(circle, rgba(245, 158, 11, 0.08) 0%, transparent 60%);
  pointer-events: none;
}

.login-wrapper {
  display: flex;
  width: 100%;
  max-width: 960px;
  min-height: 520px;
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
  position: relative;
  z-index: 1;
}

/* Brand side */
.login-brand {
  flex: 1;
  background: linear-gradient(160deg, var(--primary-color) 0%, var(--primary-dark) 60%, #312e81 100%);
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  color: #fff;
  position: relative;
  overflow: hidden;
}

.login-brand::before {
  content: '';
  position: absolute;
  top: -40px;
  right: -40px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  pointer-events: none;
}

.login-brand::after {
  content: '';
  position: absolute;
  bottom: -60px;
  left: -20px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: rgba(245, 158, 11, 0.08);
  pointer-events: none;
}

.brand-icon-large {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.brand-title {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.3px;
  margin-bottom: 6px;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 2px;
  opacity: 0.7;
  text-transform: uppercase;
  margin-bottom: 20px;
}

.brand-divider {
  width: 40px;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-color), rgba(245, 158, 11, 0.3));
  border-radius: 2px;
  margin-bottom: 20px;
}

.brand-desc {
  font-size: 14px;
  opacity: 0.8;
  line-height: 1.6;
  font-weight: 400;
  max-width: 280px;
}

/* Login card side */
.login-card {
  flex: 1;
  background: var(--bg-card);
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-card-header {
  margin-bottom: 28px;
}

.login-card-title {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 6px;
  letter-spacing: -0.2px;
}

.login-card-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
  padding: 2px 14px;
  box-shadow: 0 0 0 1px var(--border-color) inset;
  transition: all var(--transition-fast);
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--primary-light) inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-color) inset, 0 0 0 4px rgba(99, 102, 241, 0.08);
}

.login-form :deep(.el-input__inner) {
  height: 44px;
  font-size: 14px;
  font-weight: 500;
}

.login-form :deep(.el-input__prefix) {
  color: var(--text-muted);
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.remember-checkbox :deep(.el-checkbox__label) {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.remember-checkbox :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 1px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border: none;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
  transition: all var(--transition-fast);
}

.login-btn:hover {
  background: linear-gradient(135deg, var(--primary-dark) 0%, #4338ca 100%);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
  transform: translateY(-1px);
}

.login-btn:active {
  transform: translateY(0);
}

.btn-text {
  position: relative;
  top: 1px;
}

.btn-icon {
  transition: transform var(--transition-fast);
}

.login-btn:hover .btn-icon {
  transform: translateX(3px);
}

/* Password Dialog */
.password-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  padding: 20px 24px;
  margin-right: 0;
}

.password-dialog :deep(.el-dialog__title) {
  color: #fff;
  font-weight: 700;
  font-size: 16px;
}

.password-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: rgba(255, 255, 255, 0.7);
}

.password-dialog :deep(.el-dialog__headerbtn .el-dialog__close:hover) {
  color: #fff;
}

.dialog-tip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(245, 158, 11, 0.02) 100%);
  border: 1px solid rgba(245, 158, 11, 0.15);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 16px;
}

.tip-icon {
  color: var(--accent-color);
  flex-shrink: 0;
}

/* Password Strength Bar */
.strength-bar {
  margin-top: 16px;
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--bg-color);
  border: 1px solid var(--border-light);
}

.strength-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.strength-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.strength-value {
  font-size: 13px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 20px;
  letter-spacing: 0.5px;
}

.strength-value.weak {
  color: var(--danger-color);
  background: rgba(239, 68, 68, 0.08);
}

.strength-value.medium {
  color: var(--accent-color);
  background: rgba(245, 158, 11, 0.08);
}

.strength-value.strong {
  color: var(--success-color);
  background: rgba(16, 185, 129, 0.08);
}

.strength-track {
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 12px;
}

.strength-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.4s;
}

.strength-fill.weak {
  background: linear-gradient(90deg, var(--danger-color), #f87171);
}

.strength-fill.medium {
  background: linear-gradient(90deg, var(--accent-color), #fbbf24);
}

.strength-fill.strong {
  background: linear-gradient(90deg, var(--success-color), #34d399);
}

.strength-tips {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px 12px;
}

.strength-tips li {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  padding-left: 18px;
  position: relative;
  transition: all var(--transition-fast);
}

.strength-tips li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  transition: all var(--transition-fast);
}

.strength-tips li.ok {
  color: var(--success-color);
  font-weight: 600;
}

.strength-tips li.ok::before {
  border-color: var(--success-color);
  background: var(--success-color);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.3);
}

.strength-tips li.ok::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 50%;
  transform: translateY(-50%) rotate(45deg);
  width: 4px;
  height: 6px;
  border-right: 2px solid #fff;
  border-bottom: 2px solid #fff;
}

.confirm-btn {
  width: 100%;
  height: 42px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

/* Mobile */
@media (max-width: 768px) {
  .login-wrapper {
    flex-direction: column;
    min-height: auto;
  }
  .login-brand {
    padding: 32px 24px;
    align-items: center;
    text-align: center;
  }
  .brand-desc {
    max-width: 100%;
  }
  .login-card {
    padding: 32px 24px;
  }
}
</style>
