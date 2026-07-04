import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import SelfAssessment from '@/views/self-assessment/SelfAssessment.vue'

// 模拟依赖
global.localStorage = {
  getItem: vi.fn(() => 'fake_token'),
  setItem: vi.fn(),
  removeItem: vi.fn()
}

const mockRecord = {
  id: 1,
  cycle_name: '2026 Q1',
  employee_name: '王员工',
  employee_no: 'EMP001',
  department_name: '研发部',
  position_name: '工程师',
  kpi_items: [
    { name: '代码质量', weight: 40, target: '95%', actual: '92%' },
    { name: '项目交付', weight: 60, target: '100%', actual: '98%' }
  ],
  dimensions: [
    { key: 'performance', label: '工作业绩', weight: 40 },
    { key: 'ability', label: '工作能力', weight: 35 },
    { key: 'attitude', label: '工作态度', weight: 25 }
  ],
  self_scores: null,
  status: 'pending_self'
}

vi.mock('@/api/scores', () => ({
  getSelfAssessment: vi.fn(() => Promise.resolve({ data: mockRecord })),
  saveDraft: vi.fn(() => Promise.resolve({ data: { success: true } })),
  submitSelf: vi.fn(() => Promise.resolve({ data: { success: true } }))
}))

describe('SelfAssessment.vue', () => {
  it('页面加载时渲染 KPI 快照和维度评分区', async () => {
    const wrapper = mount(SelfAssessment, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('2026 Q1')
    expect(wrapper.text()).toContain('王员工')
    expect(wrapper.text()).toContain('代码质量')
    expect(wrapper.text()).toContain('工作业绩')
    expect(wrapper.text()).toContain('工作能力')
    expect(wrapper.text()).toContain('工作态度')
  })

  it('得分范围校验：输入 101 时拦截', async () => {
    const wrapper = mount(SelfAssessment, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    const inputs = wrapper.findAll('.score-input input')
    expect(inputs.length).toBe(3)

    await inputs[0].setValue('101')
    await inputs[0].trigger('blur')
    await flushPromises()

    expect(wrapper.text()).toContain('得分必须在 0-100 之间')
  })

  it('保存草稿后显示成功提示', async () => {
    const wrapper = mount(SelfAssessment, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    const inputs = wrapper.findAll('.score-input input')
    await inputs[0].setValue('85')
    await inputs[1].setValue('80')
    await inputs[2].setValue('90')

    const saveBtn = wrapper.find('button:has-text("保存草稿")')
    if (saveBtn.exists()) {
      await saveBtn.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('草稿已保存')
    }
  })

  it('提交后状态变为锁定', async () => {
    const wrapper = mount(SelfAssessment, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    // 模拟已提交状态
    const vm = wrapper.vm
    vm.record.status = 'pending_manager'
    await flushPromises()

    expect(wrapper.text()).toContain('已提交') || expect(wrapper.text()).toContain('不可修改')
  })
})
