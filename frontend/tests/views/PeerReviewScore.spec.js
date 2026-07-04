import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PeerReviewScore from '@/views/peer-review/PeerReviewScore.vue'

vi.mock('@/api/peers', () => ({
  getPeerReviewList: vi.fn(() => Promise.resolve({
    data: [
      {
        id: 1,
        record_id: 10,
        employee_name: '王员工',
        cycle_name: '2026 Q1',
        status: 'pending'
      }
    ]
  })),
  getPeerReviewDetail: vi.fn(() => Promise.resolve({
    data: {
      record_id: 10,
      employee_name: '王员工',
      self_scores: { performance: 85, ability: 80, attitude: 90 },
      manager_scores: { performance: 88, ability: 82, attitude: 85 },
      dimension: { key: 'ability', label: '工作能力', weight: 35 }
    }
  })),
  submitPeerScore: vi.fn(() => Promise.resolve({ data: { success: true } }))
}))

describe('PeerReviewScore.vue', () => {
  it('加载时显示被评分人信息和参考分数', async () => {
    const wrapper = mount(PeerReviewScore, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('王员工')
    expect(wrapper.text()).toContain('员工自评参考')
    expect(wrapper.text()).toContain('上级评分参考')
  })

  it('仅工作能力维度可输入，其他维度显示锁定', async () => {
    const wrapper = mount(PeerReviewScore, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    // 协作人仅评分工作能力维度
    expect(wrapper.text()).toContain('工作能力') || expect(wrapper.text()).toContain('协作人仅可评分')
    expect(wrapper.text()).toContain('锁定') || expect(wrapper.text()).toContain('不可修改')
  })

  it('提交后页面显示锁定状态', async () => {
    const wrapper = mount(PeerReviewScore, {
      global: { plugins: [createPinia()] }
    })
    await flushPromises()

    const vm = wrapper.vm
    vm.review.status = 'completed'
    await flushPromises()

    expect(wrapper.text()).toContain('已提交') || expect(wrapper.text()).toContain('不可修改')
  })
})
