import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import LoginView from '@/views/login/LoginView.vue'
import { useAuthStore } from '@/stores/auth'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  User: { name: 'User' },
  Lock: { name: 'Lock' },
}))

// Mock auth store
vi.mock('@/stores/auth', async () => {
  const actual = await vi.importActual('@/stores/auth')
  return {
    ...actual,
    useAuthStore: vi.fn(),
  }
})

async function mountLoginView(authStoreOverrides = {}) {
  const defaultAuthStore = {
    token: '',
    userInfo: null,
    login: vi.fn().mockResolvedValue({ user: { is_first_login: false } }),
    logout: vi.fn(),
    changePassword: vi.fn().mockResolvedValue({}),
    ...authStoreOverrides,
  }
  useAuthStore.mockReturnValue(defaultAuthStore)

  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/dashboard', name: 'Dashboard', component: { template: '<div>Dashboard</div>' } }],
  })

  const wrapper = mount(LoginView, {
    global: {
      plugins: [createPinia(), ElementPlus, router],
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('P0-19 LoginView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('应渲染登录表单标题和输入框', async () => {
    const { wrapper } = await mountLoginView()
    expect(wrapper.find('.title').text()).toBe('绩效考核评分系统')
    expect(wrapper.find('input[placeholder="用户名"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder="密码"]').exists()).toBe(true)
    expect(wrapper.find('.login-btn').text()).toBe('登录')
  })

  it('点击登录按钮应调用 authStore.login', async () => {
    const loginMock = vi.fn().mockResolvedValue({ user: { is_first_login: false } })
    const { wrapper } = await mountLoginView({ login: loginMock })

    await wrapper.find('input[placeholder="用户名"]').setValue('admin')
    await wrapper.find('input[placeholder="密码"]').setValue('admin123')
    await wrapper.find('.login-btn').trigger('click')
    await flushPromises()

    expect(loginMock).toHaveBeenCalledWith({
      username: 'admin',
      password: 'admin123',
      remember_me: false,
    })
  })

  it('首次登录应弹出修改密码弹窗', async () => {
    const loginMock = vi.fn().mockResolvedValue({
      user: { is_first_login: true },
    })
    const { wrapper } = await mountLoginView({ login: loginMock })

    await wrapper.find('input[placeholder="用户名"]').setValue('emp001')
    await wrapper.find('input[placeholder="密码"]').setValue('Emp001@123')
    await wrapper.find('.login-btn').trigger('click')
    await flushPromises()

    expect(loginMock).toHaveBeenCalled()
    // Dialog should be visible
    expect(wrapper.find('.el-dialog').isVisible()).toBe(true)
    expect(wrapper.text()).toContain('首次登录')
  })

  it('修改密码弹窗中应验证密码强度', async () => {
    const loginMock = vi.fn().mockResolvedValue({
      user: { is_first_login: true },
    })
    const { wrapper } = await mountLoginView({ login: loginMock })

    await wrapper.find('input[placeholder="用户名"]').setValue('emp001')
    await wrapper.find('input[placeholder="密码"]').setValue('Emp001@123')
    await wrapper.find('.login-btn').trigger('click')
    await flushPromises()

    // 输入弱密码（使用 wrapper.findAll 以正确触发表单模型更新）
    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[1].setValue('123')
    await inputs[2].setValue('123')
    await flushPromises()

    // 触发确认按钮以触发表单校验
    await wrapper.find('.el-dialog__footer button').trigger('click')
    await flushPromises()

    // 校验失败后弹窗应保持打开（说明表单校验拦截了提交）
    expect(wrapper.find('.el-dialog').exists()).toBe(true)
  })

  it('修改密码成功后应调用 logout 并清空表单', async () => {
    const changePasswordMock = vi.fn().mockResolvedValue({})
    const logoutMock = vi.fn()
    const loginMock = vi.fn().mockResolvedValue({
      user: { is_first_login: true },
    })
    const { wrapper } = await mountLoginView({
      login: loginMock,
      changePassword: changePasswordMock,
      logout: logoutMock,
    })

    await wrapper.find('input[placeholder="用户名"]').setValue('emp001')
    await wrapper.find('input[placeholder="密码"]').setValue('Emp001@123')
    await wrapper.find('.login-btn').trigger('click')
    await flushPromises()

    // 输入合法密码
    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[1].setValue('NewPass1!')
    await inputs[2].setValue('NewPass1!')
    await flushPromises()

    // 点击确认修改
    const confirmBtn = wrapper.find('.el-dialog__footer .el-button')
    await confirmBtn.trigger('click')
    await flushPromises()

    expect(changePasswordMock).toHaveBeenCalledWith({
      old_password: 'Emp001@123',
      new_password: 'NewPass1!',
    })
    expect(logoutMock).toHaveBeenCalled()
  })

  it('登录成功后非首次登录应跳转仪表盘', async () => {
    const loginMock = vi.fn().mockResolvedValue({ user: { is_first_login: false } })
    const { wrapper, router } = await mountLoginView({ login: loginMock })

    const pushSpy = vi.spyOn(router, 'push')

    await wrapper.find('input[placeholder="用户名"]').setValue('admin')
    await wrapper.find('input[placeholder="密码"]').setValue('admin123')
    await wrapper.find('.login-btn').trigger('click')
    await flushPromises()

    expect(loginMock).toHaveBeenCalled()
    expect(pushSpy).toHaveBeenCalledWith('/dashboard')
  })

  it('登录表单应支持回车键提交', async () => {
    const loginMock = vi.fn().mockResolvedValue({ user: { is_first_login: false } })
    const { wrapper } = await mountLoginView({ login: loginMock })

    await wrapper.find('input[placeholder="用户名"]').setValue('admin')
    await wrapper.find('input[placeholder="密码"]').setValue('admin123')
    await wrapper.find('form').trigger('keyup.enter')
    await flushPromises()

    expect(loginMock).toHaveBeenCalled()
  })
})
