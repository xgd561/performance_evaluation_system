import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import PeerReviewScore from '@/views/peer-review/PeerReviewScore.vue'

const mockGetPeerReviewList = vi.fn()
const mockSubmitPeerReviewTask = vi.fn()

vi.mock('@/api/scores', () => ({
  getPeerReviewList: (...args) => mockGetPeerReviewList(...args),
  submitPeerReviewTask: (...args) => mockSubmitPeerReviewTask(...args),
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
      warning: vi.fn(),
    },
  }
})

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { taskId: '42' } }),
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

describe('PeerReviewScore.vue', () => {
  const mockItem = {
    task_id: 42,
    employee_name: '李协作',
    department_name: '产品部',
    position_name: '产品经理',
    cycle_name: '2024 Q1',
    peer_due_date: '2024-04-20T23:59:59',
    status: 'pending',
    self_scores: { performance: 85, ability: 80, attitude: 90 },
    manager_scores: { performance: 88, ability: 82, attitude: 85 },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockGetPeerReviewList.mockResolvedValue({ items: [mockItem] })
  })

  it('renders ability score input and comment textarea', async () => {
    const wrapper = mount(PeerReviewScore)
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('协作评分')
    expect(wrapper.text()).toContain('工作能力')

    const inputs = wrapper.findAll('.el-input-number')
    expect(inputs.length).toBeGreaterThanOrEqual(1)

    const textareas = wrapper.findAll('.el-textarea')
    expect(textareas.length).toBeGreaterThanOrEqual(1)
  })

  it('loads self_scores and manager_scores as reference', async () => {
    const wrapper = mount(PeerReviewScore)
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('员工自评参考')
    expect(wrapper.text()).toContain('上级评分参考')
    expect(wrapper.text()).toContain('85')
    expect(wrapper.text()).toContain('88')
  })

  it('submits peer review successfully', async () => {
    const wrapper = mount(PeerReviewScore)
    await flushPromises()
    await nextTick()

    wrapper.vm.scoreForm.ability = 84
    wrapper.vm.scoreForm.comment = '该同事沟通能力强，项目推进顺利，协作态度积极主动。'
    await nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(mockSubmitPeerReviewTask).toHaveBeenCalledWith(
      '42',
      expect.objectContaining({
        ability: 84,
        comment: '该同事沟通能力强，项目推进顺利，协作态度积极主动。',
      })
    )
  })

  it('locks page when status is completed (isLocked)', async () => {
    mockGetPeerReviewList.mockResolvedValue({
      items: [
        {
          ...mockItem,
          status: 'completed',
          ability_score: 84,
          comment: '该同事沟通能力强，项目推进顺利。',
        },
      ],
    })

    const wrapper = mount(PeerReviewScore)
    await flushPromises()
    await nextTick()

    expect(wrapper.vm.isLocked).toBe(true)
  })

  it('shows "评分已提交" tag when locked', async () => {
    mockGetPeerReviewList.mockResolvedValue({
      items: [
        {
          ...mockItem,
          status: 'completed',
          ability_score: 84,
          comment: '该同事沟通能力强，项目推进顺利。',
        },
      ],
    })

    const wrapper = mount(PeerReviewScore)
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('评分已提交')
  })

  it('validates comment length (>=20 chars)', async () => {
    const wrapper = mount(PeerReviewScore)
    await flushPromises()
    await nextTick()

    wrapper.vm.scoreForm.ability = 84
    wrapper.vm.scoreForm.comment = '太短'
    await nextTick()

    expect(wrapper.vm.canSubmit).toBe(false)

    await wrapper.vm.handleSubmit()
    await nextTick()

    expect(wrapper.vm.commentError).toBe('协作评语不少于20字')
    expect(mockSubmitPeerReviewTask).not.toHaveBeenCalled()
  })
})
