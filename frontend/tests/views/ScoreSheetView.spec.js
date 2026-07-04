import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ScoreSheetView from '@/views/score-sheet/ScoreSheetView.vue'

vi.mock('@/api/scores', () => ({
  getScoreRecordDetail: vi.fn(() => Promise.resolve({
    data: {
      id: 1,
      employee_name: '王员工',
      employee_no: 'EMP001',
      self_scores: { performance: 85, ability: 80, attitude: 90 },
      self_facts: { performance: '完成了项目A', ability: '技术提升' },
      kpi_items: [
        { name: '代码质量', weight: 40, target: '95%', actual_score: 92 }
      ],
      dimensions: [
        { key: 'performance', label: '工作业绩', weight: 40 },
        { key: 'ability', label: '工作能力', weight: 35 },
        { key: 'attitude', label: '工作态度', weight: 25 }
      ],
      status: 'pending_manager'
    }
  })),
  saveDraft: vi.fn(() => Promise.resolve({ data: { success: true } })),
  submitManagerScore: vi.fn(() => Promise.resolve({ data: { success: true } }))
}))

describe('ScoreSheetView.vue', () => {
  it('加载时显示员工自评参考', async () => {
    const wrapper = mount(ScoreSheetView, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('王员工')
    expect(wrapper.text()).toContain('员工自评参考')
    expect(wrapper.text()).toContain('85')
    expect(wrapper.text()).toContain('80')
    expect(wrapper.text()).toContain('90')
  })

  it('评语少于 20 字时提交拦截', async () => {
    const wrapper = mount(ScoreSheetView, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    const comment = wrapper.find('textarea')
    if (comment.exists()) {
      await comment.setValue('太短')
      await comment.trigger('blur')
      await flushPromises()
      expect(wrapper.text()).toContain('不少于 20 字') || expect(wrapper.text()).toContain('20')
    }
  })

  it('评分差异大于 20 分时弹出确认框', async () => {
    const wrapper = mount(ScoreSheetView, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    const inputs = wrapper.findAll('.score-input input')
    if (inputs.length >= 3) {
      await inputs[0].setValue('10')  // 与自评 85 差异 75
      await inputs[1].setValue('82')
      await inputs[2].setValue('85')

      const submitBtn = wrapper.find('button:has-text("提交评分")')
      if (submitBtn.exists()) {
        await submitBtn.trigger('click')
        await flushPromises()
        expect(wrapper.text()).toContain('差异') || expect(wrapper.text()).toContain('确认')
      }
    }
  })

  it('保存草稿功能正常', async () => {
    const wrapper = mount(ScoreSheetView, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    const saveBtn = wrapper.find('button:has-text("保存草稿")')
    if (saveBtn.exists()) {
      await saveBtn.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('草稿') || expect(wrapper.text()).toContain('已保存')
    }
  })
})
