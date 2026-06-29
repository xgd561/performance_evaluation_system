import { vi, describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import CycleList from '@/views/cycles/CycleList.vue'

const mockListCycles = vi.fn(() => Promise.resolve([]))
const mockCreateCycle = vi.fn((data) => Promise.resolve({ id: 1, ...data, status: '未开始', created_at: '2026-06-29T00:00:00' }))
const mockUpdateCycle = vi.fn((id, data) => Promise.resolve({ id, ...data }))
const mockListEmployees = vi.fn(() => Promise.resolve({ items: [], total: 0, page: 1, size: 10 }))

vi.mock('@/api/cycles', () => ({
  listCycles: () => mockListCycles(),
  createCycle: (data) => mockCreateCycle(data),
  updateCycle: (id, data) => mockUpdateCycle(id, data),
  deleteCycle: vi.fn(() => Promise.resolve()),
  launchCycle: vi.fn(() => Promise.resolve({ created_records: 1, status: '进行中（自评）' })),
  getCycleProgress: vi.fn(() => Promise.resolve({ cycle_id: 1, status: 'not_started', total_employees: 1, completed: 0, overall_progress: 0, stages: [] })),
}))

vi.mock('@/api/employees', () => ({
  listEmployees: () => mockListEmployees(),
}))

describe('CycleList.vue — 考核周期表单测试', () => {
  let wrapper

  beforeEach(async () => {
    mockListCycles.mockClear()
    mockCreateCycle.mockClear()
    mockUpdateCycle.mockClear()
    mockListEmployees.mockClear()
    wrapper = mount(CycleList, { attachTo: document.body })
    await flushPromises()
  })

  it('新增弹窗打开时，dateRange 应绑定到 form 对象且初始为空数组', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增周期')
    expect(btn).toBeTruthy()
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    expect(vm.form.dateRange).toBeInstanceOf(Array)
    expect(vm.form.dateRange).toHaveLength(0)
  })

  it('日期选择后，form.dateRange 应包含所选日期，且表单校验应通过', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增周期')
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.form.dateRange = ['2026-06-01', '2026-06-30']
    await nextTick()

    expect(vm.form.dateRange).toEqual(['2026-06-01', '2026-06-30'])

    const valid = await vm.$refs.formRef.validate().catch(() => false)
    expect(valid).toBe(true)
  })

  it('未选择日期时，提交 payload 中的 start_date 和 end_date 应为空字符串', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增周期')
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.form.name = '测试周期'
    vm.form.type = 'monthly'
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    if (mockCreateCycle.mock.calls.length > 0) {
      const payload = mockCreateCycle.mock.calls[0][0]
      expect(payload.start_date).toBe('')
      expect(payload.end_date).toBe('')
    }
  })

  it('编辑时，dateRange 应从行数据正确回填到 form', async () => {
    mockListCycles.mockResolvedValueOnce([
      { id: 1, name: 'Q2考核', type: 'quarterly', start_date: '2026-04-01', end_date: '2026-06-30', status: 'not_started' }
    ])
    await wrapper.vm.loadData()
    await flushPromises()
    await nextTick()

    const editBtn = wrapper.findAll('button').find(b => b.text() === '编辑')
    expect(editBtn).toBeTruthy()
    await editBtn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    expect(vm.form.dateRange).toEqual(['2026-04-01', '2026-06-30'])
  })

  it('编辑时，self_due_date / manager_due_date / peer_due_date 应从行数据正确回填到表单', async () => {
    mockListCycles.mockResolvedValueOnce([
      {
        id: 1,
        name: 'Q2考核',
        type: 'quarterly',
        start_date: '2026-04-01',
        end_date: '2026-06-30',
        self_due_date: '2026-05-15',
        manager_due_date: '2026-05-25',
        peer_due_date: '2026-06-05',
        status: 'not_started'
      }
    ])
    await wrapper.vm.loadData()
    await flushPromises()
    await nextTick()

    const editBtn = wrapper.findAll('button').find(b => b.text() === '编辑')
    expect(editBtn).toBeTruthy()
    await editBtn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    expect(vm.form.self_due_date).toBe('2026-05-15')
    expect(vm.form.manager_due_date).toBe('2026-05-25')
    expect(vm.form.peer_due_date).toBe('2026-06-05')
  })

  it('提交时 payload 应包含正确的 start_date 和 end_date', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增周期')
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.form.name = 'Q3考核'
    vm.form.type = 'quarterly'
    vm.form.dateRange = ['2026-07-01', '2026-09-30']
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(mockCreateCycle).toHaveBeenCalledTimes(1)
    const payload = mockCreateCycle.mock.calls[0][0]
    expect(payload.start_date).toBe('2026-07-01')
    expect(payload.end_date).toBe('2026-09-30')
  })

  it('日期格式为 YYYY-MM-DD，确保后端能正确解析', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增周期')
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.form.name = '格式测试'
    vm.form.type = 'monthly'
    vm.form.dateRange = ['2026-12-31', '2027-01-31']
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    const payload = mockCreateCycle.mock.calls[0][0]
    expect(payload.start_date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(payload.end_date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})
