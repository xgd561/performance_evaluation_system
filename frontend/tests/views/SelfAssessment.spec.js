import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import SelfAssessment from '@/views/self-assessment/SelfAssessment.vue'

const mockGetMyAssessment = vi.fn()
const mockGetSelfAssessmentData = vi.fn()
const mockSubmitSelfScore = vi.fn()
const mockCreateScoreDraft = vi.fn()

vi.mock('@/api/scores', () => ({
  getMyAssessment: (...args) => mockGetMyAssessment(...args),
  getSelfAssessmentData: (...args) => mockGetSelfAssessmentData(...args),
  submitSelfScore: (...args) => mockSubmitSelfScore(...args),
  createScoreDraft: (...args) => mockCreateScoreDraft(...args),
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
    ElMessageBox: {
      confirm: vi.fn().mockResolvedValue(true),
    },
  }
})

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

describe('SelfAssessment.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetMyAssessment.mockResolvedValue({
      items: [
        {
          record_id: 1,
          status: 'pending_self',
          cycle_name: '2024 Q1',
          self_due_date: '2024-03-31T23:59:59',
          self_scores: {},
        },
      ],
    })
    mockGetSelfAssessmentData.mockResolvedValue({
      dimension_weights: { performance: 60, ability: 20, attitude: 20 },
      reviewer_weights: { self: 30, manager: 60, peer: 10 },
      kpi_items: [],
      self_scores: {},
      draft: null,
    })
  })

  it('renders score inputs for performance, ability, attitude', async () => {
    const wrapper = mount(SelfAssessment)
    await flushPromises()
    await nextTick()

    const labels = wrapper.findAll('.dim-name')
    const labelTexts = labels.map(l => l.text())
    expect(labelTexts).toContain('工作业绩')
    expect(labelTexts).toContain('工作能力')
    expect(labelTexts).toContain('工作态度')

    const inputs = wrapper.findAll('.el-input-number')
    expect(inputs.length).toBeGreaterThanOrEqual(3)
  })

  it('loads existing draft scores on mount', async () => {
    mockGetSelfAssessmentData.mockResolvedValue({
      dimension_weights: { performance: 60, ability: 20, attitude: 20 },
      reviewer_weights: { self: 30, manager: 60, peer: 10 },
      kpi_items: [],
      self_scores: {},
      draft: {
        performance: 85,
        ability: 78,
        attitude: 90,
      },
    })

    const wrapper = mount(SelfAssessment)
    await flushPromises()
    await nextTick()

    expect(wrapper.vm.scoreForm.dimensionScores.performance).toBe(85)
    expect(wrapper.vm.scoreForm.dimensionScores.ability).toBe(78)
    expect(wrapper.vm.scoreForm.dimensionScores.attitude).toBe(90)
  })

  it('validates score range (0-100)', async () => {
    const wrapper = mount(SelfAssessment)
    await flushPromises()
    await nextTick()

    wrapper.vm.handleDimensionScoreChange('performance', 105)
    await nextTick()
    expect(wrapper.vm.dimensionErrors.performance).toBe('分数需在 0-100 之间')

    wrapper.vm.handleDimensionScoreChange('performance', -5)
    await nextTick()
    expect(wrapper.vm.dimensionErrors.performance).toBe('分数需在 0-100 之间')

    wrapper.vm.handleDimensionScoreChange('performance', 50)
    await nextTick()
    expect(wrapper.vm.dimensionErrors.performance).toBe('')
  })

  it('submits self-assessment successfully', async () => {
    const wrapper = mount(SelfAssessment)
    await flushPromises()
    await nextTick()

    wrapper.vm.scoreForm.dimensionScores.performance = 80
    wrapper.vm.scoreForm.dimensionScores.ability = 75
    wrapper.vm.scoreForm.dimensionScores.attitude = 85
    await nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(mockSubmitSelfScore).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        performance: 80,
        ability: 75,
        attitude: 85,
        kpi_scores: [],
      })
    )
  })

  it('shows error when scores are missing', async () => {
    const wrapper = mount(SelfAssessment)
    await flushPromises()
    await nextTick()

    // Leave performance null
    wrapper.vm.scoreForm.dimensionScores.ability = 75
    wrapper.vm.scoreForm.dimensionScores.attitude = 85
    await nextTick()

    await wrapper.vm.handleSubmit()
    await nextTick()

    expect(mockSubmitSelfScore).not.toHaveBeenCalled()
    expect(wrapper.vm.dimensionErrors.performance).toBe('请填写 0-100 之间的分数')
  })
})
