import { vi, describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import CycleEdit from '@/views/cycles/CycleEdit.vue'

const mockCreateCycle = vi.fn((data) => Promise.resolve({ id: 1, ...data }))
const mockUpdateCycle = vi.fn((id, data) => Promise.resolve({ id, ...data }))

vi.mock('@/api/cycles', () => ({
  createCycle: (data) => mockCreateCycle(data),
  updateCycle: (id, data) => mockUpdateCycle(id, data),
}))

describe('CycleEdit.vue — 考核周期编辑表单测试', () => {
  let wrapper
  let pushMock
  let messageSuccess
  let messageError

  beforeEach(() => {
    mockCreateCycle.mockClear()
    mockUpdateCycle.mockClear()
    pushMock = vi.fn()
    messageSuccess = vi.fn()
    messageError = vi.fn()
  })

  function mountComponent(routeQuery = {}) {
    wrapper = mount(CycleEdit, {
      global: {
        mocks: {
          $route: { query: routeQuery },
          $router: { push: pushMock },
          $message: { success: messageSuccess, error: messageError },
        },
      },
      attachTo: document.body,
    })
    return wrapper
  }

  it('新增模式下应渲染默认表单值', async () => {
    mountComponent({})
    await flushPromises()
    expect(wrapper.vm.isEdit).toBe(false)
    expect(wrapper.vm.form.name).toBe('')
    expect(wrapper.vm.form.type).toBe('quarterly')
    expect(wrapper.vm.form.is_active).toBe(true)
    expect(wrapper.vm.form.start_date).toBe('')
    expect(wrapper.vm.form.end_date).toBe('')
    expect(wrapper.vm.form.self_deadline).toBe('')
    expect(wrapper.vm.form.manager_deadline).toBe('')
  })

  it('编辑模式下应从 query 回填数据', async () => {
    mountComponent({
      id: '1',
      name: 'Q2考核',
      type: 'annual',
      start_date: '2026-04-01',
      end_date: '2026-06-30',
      self_deadline: '2026-05-15',
      manager_deadline: '2026-05-25',
      is_active: 'true',
    })
    await flushPromises()
    expect(wrapper.vm.isEdit).toBe(true)
    expect(wrapper.vm.form.name).toBe('Q2考核')
    expect(wrapper.vm.form.type).toBe('annual')
    expect(wrapper.vm.form.start_date).toBe('2026-04-01')
    expect(wrapper.vm.form.end_date).toBe('2026-06-30')
    expect(wrapper.vm.form.self_deadline).toBe('2026-05-15')
    expect(wrapper.vm.form.manager_deadline).toBe('2026-05-25')
    expect(wrapper.vm.form.is_active).toBe(true)
  })

  it('编辑模式下 is_active=false 应正确解析', async () => {
    mountComponent({
      id: '1',
      name: '停用周期',
      type: 'monthly',
      is_active: 'false',
    })
    await flushPromises()
    expect(wrapper.vm.form.is_active).toBe(false)
  })

  it('提交新增时应调用 createCycle 并格式化日期', async () => {
    mountComponent({})
    await flushPromises()

    const vm = wrapper.vm
    vm.form.name = '测试周期'
    vm.form.type = 'monthly'
    vm.form.start_date = '2026-07-01'
    vm.form.end_date = '2026-07-31'
    vm.form.self_deadline = '2026-07-15'
    vm.form.manager_deadline = '2026-07-20'
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '保存')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(mockCreateCycle).toHaveBeenCalledTimes(1)
    const payload = mockCreateCycle.mock.calls[0][0]
    expect(payload.name).toBe('测试周期')
    expect(payload.type).toBe('monthly')
    expect(payload.start_date).toBe('2026-07-01')
    expect(payload.end_date).toBe('2026-07-31')
    expect(payload.self_deadline).toBe('2026-07-15')
    expect(payload.manager_deadline).toBe('2026-07-20')
    expect(payload.is_active).toBe(true)
    expect(messageSuccess).toHaveBeenCalledWith('创建成功')
    expect(pushMock).toHaveBeenCalledWith({ name: 'Cycles' })
  })

  it('提交编辑时应调用 updateCycle 并传递 id', async () => {
    mountComponent({
      id: '2',
      name: '旧名称',
      type: 'quarterly',
      start_date: '2026-01-01',
      end_date: '2026-03-31',
      self_deadline: '2026-02-15',
      manager_deadline: '2026-02-20',
      is_active: 'true',
    })
    await flushPromises()

    const vm = wrapper.vm
    vm.form.name = '新名称'
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '保存')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(mockUpdateCycle).toHaveBeenCalledTimes(1)
    const [id, payload] = mockUpdateCycle.mock.calls[0]
    expect(id).toBe('2')
    expect(payload.name).toBe('新名称')
    expect(payload.type).toBe('quarterly')
    expect(messageSuccess).toHaveBeenCalledWith('更新成功')
    expect(pushMock).toHaveBeenCalledWith({ name: 'Cycles' })
  })

  it('取消按钮应返回列表页', async () => {
    mountComponent({})
    await flushPromises()

    const cancelBtn = wrapper.findAll('button').find(b => b.text() === '取消')
    await cancelBtn.trigger('click')
    await flushPromises()

    expect(pushMock).toHaveBeenCalledWith({ name: 'Cycles' })
  })

  it('Date 对象应被格式化为 YYYY-MM-DD', async () => {
    mountComponent({})
    await flushPromises()

    const vm = wrapper.vm
    vm.form.name = '格式测试'
    vm.form.type = 'monthly'
    vm.form.start_date = new Date('2026-12-31')
    vm.form.end_date = new Date('2027-01-31')
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '保存')
    await submitBtn.trigger('click')
    await flushPromises()

    const payload = mockCreateCycle.mock.calls[0][0]
    expect(payload.start_date).toBe('2026-12-31')
    expect(payload.end_date).toBe('2027-01-31')
  })

  it('表单校验不通过时应阻止提交', async () => {
    mountComponent({})
    await flushPromises()

    // Mock form validation to fail
    const validateSpy = vi.spyOn(wrapper.vm.$refs.formRef, 'validate').mockRejectedValue(new Error('invalid'))

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '保存')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(mockCreateCycle).not.toHaveBeenCalled()
    validateSpy.mockRestore()
  })

  it('保存失败时应显示错误提示', async () => {
    mockCreateCycle.mockRejectedValueOnce({ response: { data: { message: '网络错误' } } })
    mountComponent({})
    await flushPromises()

    const vm = wrapper.vm
    vm.form.name = '测试周期'
    vm.form.type = 'monthly'
    vm.form.start_date = '2026-07-01'
    vm.form.end_date = '2026-07-31'
    vm.form.self_deadline = '2026-07-15'
    vm.form.manager_deadline = '2026-07-20'
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '保存')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(messageError).toHaveBeenCalledWith('网络错误')
  })
})
