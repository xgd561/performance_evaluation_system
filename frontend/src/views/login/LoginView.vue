<template>
  <div class="login-container">
    <div class="login-sheet">
      <span class="tape tape-tl" aria-hidden="true"></span>
      <span class="tape tape-tr" aria-hidden="true"></span>

      <header class="sheet-head">
        <h1 class="brand-title">绩效考核评分系统</h1>
        <p class="brand-sub">员工登录</p>
        <div class="head-rule" aria-hidden="true"></div>
      </header>

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

      <p class="first-login-note">首次登录需先修改初始密码</p>

      <div class="seal" aria-hidden="true">
        <span class="seal-text">绩效<br />考核</span>
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
import { User, Lock, ArrowRight, InfoFilled } from '@element-plus/icons-vue'
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
/* ------------------------------------------------------------------
   Lo-Fi anchor: 纸质考核表贴在公告栏上
   Surfaces: #EDE4CF / #E8E0C0 (paper-yellow, not cream)
   Type: Times/SimSun display + Helvetica body + Courier form
   Texture: halftone dots, riso misregistration, tape
------------------------------------------------------------------ */

.login-container {
  --ink: #241e12;
  --ink-soft: #4a4030;
  --ink-muted: #6b5d40;
  --paper: #ede4cf;
  --paper-deep: #e8e0c0;
  --stamp: #b0312a;

  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  background-color: var(--paper);
  background-image:
    radial-gradient(rgba(36, 30, 18, 0.09) 1px, transparent 1.5px),
    radial-gradient(rgba(36, 30, 18, 0.05) 1px, transparent 1.5px);
  background-size: 18px 18px, 18px 18px;
  background-position: 0 0, 9px 9px;
  font-family: 'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ---------- 纸质登录表 ---------- */

.login-sheet {
  position: relative;
  width: 100%;
  max-width: 400px;
  background: var(--paper-deep);
  border: 1px solid rgba(36, 30, 18, 0.55);
  padding: 48px 38px 40px;
  transform: rotate(-2deg);
  box-shadow: 0 12px 26px rgba(60, 48, 20, 0.28);
}

/* 胶带 */
.tape {
  position: absolute;
  top: -13px;
  width: 96px;
  height: 26px;
  background: linear-gradient(100deg, rgba(255, 252, 230, 0.78), rgba(244, 236, 198, 0.62));
  border-left: 1px dashed rgba(60, 48, 20, 0.28);
  border-right: 1px dashed rgba(60, 48, 20, 0.28);
  box-shadow: 0 1px 3px rgba(60, 48, 20, 0.22);
  pointer-events: none;
}

.tape-tl {
  left: 26px;
  transform: rotate(-5deg);
}

.tape-tr {
  right: 26px;
  transform: rotate(4deg);
}

/* ---------- 表头 ---------- */

.sheet-head {
  margin-bottom: 28px;
}

.brand-title {
  margin: 0 0 8px;
  font-family: 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: 3px;
  line-height: 1.25;
  color: var(--ink);
  /* Risograph 套准错位 */
  text-shadow: 2px 0 rgba(255, 0, 110, 0.32), -2px 0 rgba(0, 255, 204, 0.32);
}

.brand-sub {
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  letter-spacing: 5px;
  color: var(--ink-muted);
}

/* 表格双线 */
.head-rule {
  margin-top: 16px;
  border-top: 2px solid var(--ink);
  border-bottom: 1px solid var(--ink);
  height: 3px;
}

/* ---------- 表单 ---------- */

.login-form :deep(.el-input__wrapper) {
  background: var(--paper);
  border: 1px solid rgba(36, 30, 18, 0.6);
  border-radius: 0;
  box-shadow: none;
  padding: 2px 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: var(--ink);
  box-shadow: none;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--ink);
  box-shadow: 2px 2px 0 rgba(36, 30, 18, 0.25);
}

.login-form :deep(.el-input__inner) {
  height: 42px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  color: var(--ink);
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #8a7b5c;
  letter-spacing: 2px;
}

.login-form :deep(.el-input__prefix) {
  color: var(--ink-muted);
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.remember-checkbox :deep(.el-checkbox__label) {
  font-size: 13px;
  color: var(--ink-soft);
}

.remember-checkbox :deep(.el-checkbox__inner) {
  border-radius: 0;
  background: var(--paper);
  border-color: rgba(36, 30, 18, 0.6);
}

.remember-checkbox :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--ink);
  border-color: var(--ink);
}

/* ---------- 登录按钮 ---------- */

.login-btn {
  width: 100%;
  height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--ink);
  color: var(--paper);
  border: 1px solid var(--ink);
  border-radius: 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 6px;
  transform: rotate(1deg);
  box-shadow: 3px 3px 0 rgba(36, 30, 18, 0.3);
  transition: transform 0.12s, box-shadow 0.12s;
}

.login-btn:hover {
  background: var(--ink);
  color: var(--paper);
  border-color: var(--ink);
  transform: rotate(1deg) translate(1px, 1px);
  box-shadow: 2px 2px 0 rgba(36, 30, 18, 0.3);
}

.login-btn:active {
  transform: rotate(1deg) translate(3px, 3px);
  box-shadow: none;
}

.btn-icon {
  transition: none;
}

/* ---------- 首次登录提示 ---------- */

.first-login-note {
  display: inline-block;
  margin: 16px 0 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  letter-spacing: 1px;
  color: var(--ink-muted);
  transform: rotate(2deg);
}

/* ---------- 红章 ---------- */

.seal {
  position: absolute;
  right: -22px;
  bottom: 58px;
  width: 86px;
  height: 86px;
  border-radius: 50%;
  border: 3px double var(--stamp);
  display: flex;
  align-items: center;
  justify-content: center;
  transform: rotate(-14deg);
  opacity: 0.82;
  mix-blend-mode: multiply;
  pointer-events: none;
}

.seal-text {
  font-family: 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 3px;
  line-height: 1.15;
  text-align: center;
  color: var(--stamp);
}

/* ---------- 修改密码弹窗 ---------- */

.password-dialog :deep(.el-dialog) {
  background: var(--paper);
  border: 1px solid rgba(36, 30, 18, 0.55);
  border-radius: 0;
  transform: rotate(-2deg);
  box-shadow: 0 14px 30px rgba(60, 48, 20, 0.32);
}

.password-dialog :deep(.el-dialog__header) {
  background: transparent;
  border-bottom: 2px solid var(--ink);
  padding: 18px 22px 12px;
  margin-right: 0;
}

.password-dialog :deep(.el-dialog__title) {
  font-family: 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--ink);
}

.password-dialog :deep(.el-dialog__body) {
  color: var(--ink-soft);
  font-family: 'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.password-dialog :deep(.el-form-item__label) {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  color: var(--ink-soft);
}

.password-dialog :deep(.el-input__wrapper) {
  background: var(--paper-deep);
  border: 1px solid rgba(36, 30, 18, 0.6);
  border-radius: 0;
  box-shadow: none;
}

.password-dialog :deep(.el-input__wrapper.is-focus) {
  border-color: var(--ink);
  box-shadow: 2px 2px 0 rgba(36, 30, 18, 0.25);
}

.dialog-tip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--paper-deep);
  border: 1px solid rgba(36, 30, 18, 0.5);
  border-left: 4px solid var(--stamp);
  border-radius: 0;
  color: var(--ink-soft);
  font-size: 13px;
  margin-bottom: 16px;
}

.tip-icon {
  color: var(--stamp);
  flex-shrink: 0;
}

/* ---------- 密码强度 ---------- */

.strength-bar {
  margin-top: 16px;
  padding: 14px 16px;
  background: var(--paper-deep);
  border: 1px dashed rgba(36, 30, 18, 0.5);
  border-radius: 0;
}

.strength-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.strength-label {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  letter-spacing: 2px;
  color: var(--ink-muted);
}

.strength-value {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 0;
  letter-spacing: 1px;
}

.strength-value.weak {
  color: var(--stamp);
  background: rgba(176, 49, 42, 0.12);
}

.strength-value.medium {
  color: #8a6a1b;
  background: rgba(184, 134, 11, 0.14);
}

.strength-value.strong {
  color: #3e6b34;
  background: rgba(62, 107, 52, 0.12);
}

.strength-track {
  height: 6px;
  background: rgba(36, 30, 18, 0.15);
  border-radius: 0;
  overflow: hidden;
  margin-bottom: 12px;
}

.strength-fill {
  height: 100%;
  border-radius: 0;
  transition: width 0.3s;
}

.strength-fill.weak {
  background: var(--stamp);
}

.strength-fill.medium {
  background: #b8860b;
}

.strength-fill.strong {
  background: #3e6b34;
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
  color: var(--ink-muted);
  padding-left: 18px;
  position: relative;
}

.strength-tips li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid rgba(36, 30, 18, 0.4);
}

.strength-tips li.ok {
  color: #3e6b34;
  font-weight: 600;
}

.strength-tips li.ok::before {
  border-color: #3e6b34;
  background: #3e6b34;
}

.strength-tips li.ok::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 50%;
  transform: translateY(-50%) rotate(45deg);
  width: 4px;
  height: 6px;
  border-right: 2px solid var(--paper);
  border-bottom: 2px solid var(--paper);
}

.confirm-btn {
  width: 100%;
  height: 42px;
  background: var(--ink);
  color: var(--paper);
  border: 1px solid var(--ink);
  border-radius: 0;
  font-family: 'Courier New', Courier, monospace;
  font-weight: 700;
  letter-spacing: 4px;
}

.confirm-btn:hover {
  background: #3a3222;
  color: var(--paper);
  border-color: #3a3222;
}

/* ---------- Mobile ---------- */

@media (max-width: 480px) {
  .login-sheet {
    padding: 40px 26px 34px;
    transform: rotate(-1deg);
  }
  .brand-title {
    font-size: 25px;
  }
  .seal {
    width: 70px;
    height: 70px;
    right: -12px;
    bottom: 52px;
  }
  .seal-text {
    font-size: 14px;
  }
}
</style>
