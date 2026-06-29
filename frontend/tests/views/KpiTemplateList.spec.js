import { vi, describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import KpiTemplateList from '@/views/kpi-templates/KpiTemplateList.vue'

const mockListKpiTemplates = vi.fn(() => Promise.resolve([]))
const mockCreateKpiTemplate = vi.fn((data) => Promise.resolve({ id: 1, ...data }))
const mockUpdateKpiTemplate = vi.fn((id, data) => Promise.resolve({ id, ...data }))
const mockDeleteKpiTemplate = vi.fn(() => Promise.resolve())
const mockListPositions = vi.fn(() => Promise.resolve({ items: [], total: 0 }))

vi.mock('@/api/kpi-templates', () => ({
  listKpiTemplates: () => mockListKpiTemplates(),
  createKpiTemplate: (data) => mockCreateKpiTemplate(data),
  updateKpiTemplate: (id, data) => mockUpdateKpiTemplate(id, data),
  deleteKpiTemplate: (id) => mockDeleteKpiTemplate(id),
}))

vi.mock('@/api/departments', () => ({
  listPositions: () => mockListPositions(),
}))

describe('KpiTemplateList.vue — KPI模板列表与表单测试', () => {
  let wrapper

  beforeEach(async () => {
    mockListKpiTemplates.mockClear()
    mockCreateKpiTemplate.mockClear()
    mockUpdateKpiTemplate.mockClear()
    mockDeleteKpiTemplate.mockClear()
    mockListPositions.mockClear()
    wrapper = mount(KpiTemplateList, { attachTo: document.body })
    await flushPromises()
  })

  it('列表应渲染 position_name 字段', async () => {
    mockListKpiTemplates.mockResolvedValueOnce([
      {
        id: 1,
        position_id: 1,
        position_name: '产品经理',
        name: '月度营收达成率',
        weight: 50,
        target_value: '100万',
        description: 'test',
        is_active: true,
        created_at: '2026-06-29T00:00:00',
      },
    ])
    await wrapper.vm.loadData()
    await flushPromises()
    await nextTick()

    const html = wrapper.html()
    expect(html).toContain('产品经理')
    expect(html).toContain('月度营收达成率')
  })

  it('新增模板时，应调用 createKpiTemplate 并传入单条 payload', async () => {
    mockListPositions.mockResolvedValueOnce({
      items: [{ id: 1, name: '测试岗' }],
      total: 1,
    })
    await wrapper.vm.loadPositions()
    await flushPromises()

    const btn = wrapper.findAll('button').find(b => b.text() === '新增模板')
    expect(btn).toBeTruthy()
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.form.position_id = 1
    vm.form.name = '测试指标'
    vm.form.weight = 60
    vm.form.target_value = '100%'
    vm.form.description = 'desc'
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(mockCreateKpiTemplate).toHaveBeenCalledTimes(1)
    const payload = mockCreateKpiTemplate.mock.calls[0][0]
    expect(payload).toMatchObject({
      position_id: 1,
      name: '测试指标',
      weight: 60,
      target_value: '100%',
      description: 'desc',
    })
  })

  it('编辑模板时，应调用 updateKpiTemplate 并传入单条 payload', async () => {
    mockListKpiTemplates.mockResolvedValueOnce([
      {
        id: 1,
        position_id: 1,
        position_name: '测试岗',
        name: '原指标',
        weight: 50,
        target_value: '100',
        description: 'old',
        is_active: true,
      },
    ])
    await wrapper.vm.loadData()
    await flushPromises()
    await nextTick()

    const editBtn = wrapper.findAll('button').find(b => b.text() === '编辑')
    expect(editBtn).toBeTruthy()
    await editBtn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.form.name = '新指标'
    vm.form.weight = 70
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(mockUpdateKpiTemplate).toHaveBeenCalledTimes(1)
    expect(mockUpdateKpiTemplate.mock.calls[0][0]).toBe(1)
    const payload = mockUpdateKpiTemplate.mock.calls[0][1]
    expect(payload).toMatchObject({
      name: '新指标',
      weight: 70,
    })
  })
})
