import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import ConfigView from '@/views/config/ConfigView.vue'

const mockGetGradeRules = vi.fn()
const mockUpdateGradeRules = vi.fn()
const mockGetDimensionWeights = vi.fn()
const mockUpdateDimensionWeights = vi.fn()
const mockGetReviewerWeights = vi.fn()
const mockUpdateReviewerWeights = vi.fn()
const mockGetSmallDeptExemption = vi.fn()
const mockUpdateSmallDeptExemption = vi.fn()

vi.mock('@/api/config', () => ({
  getGradeRules: (...args) => mockGetGradeRules(...args),
  updateGradeRules: (...args) => mockUpdateGradeRules(...args),
  getDimensionWeights: (...args) => mockGetDimensionWeights(...args),
  updateDimensionWeights: (...args) => mockUpdateDimensionWeights(...args),
  getReviewerWeights: (...args) => mockGetReviewerWeights(...args),
  updateReviewerWeights: (...args) => mockUpdateReviewerWeights(...args),
  getSmallDeptExemption: (...args) => mockGetSmallDeptExemption(...args),
  updateSmallDeptExemption: (...args) => mockUpdateSmallDeptExemption(...args),
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

describe('ConfigView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetGradeRules.mockResolvedValue({
      A: { min: 90, max: 100 },
      B: { min: 80, max: 89.9 },
      C: { min: 60, max: 79.9 },
      D: { min: 0, max: 59.9 },
    })
    mockGetDimensionWeights.mockResolvedValue({ performance: 60, ability: 20, attitude: 20 })
    mockGetReviewerWeights.mockResolvedValue({ self: 30, manager: 60, peer: 10 })
    mockGetSmallDeptExemption.mockResolvedValue({ enabled: true, threshold: 5 })
  })

  it('renders dimension weights tab with correct labels', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()
    await nextTick()

    // Switch to dimension weights tab
    const tabs = wrapper.findAll('.el-tabs__item')
    const weightsTab = tabs.find(t => t.text().includes('维度权重'))
    expect(weightsTab).toBeTruthy()
    await weightsTab.trigger('click')
    await nextTick()

    const labels = wrapper.findAll('.el-form-item__label')
    const labelTexts = labels.map(l => l.text())
    expect(labelTexts).toContain('工作业绩权重')
    expect(labelTexts).toContain('工作能力权重')
    expect(labelTexts).toContain('工作态度权重')

    // Should NOT contain reviewer labels
    expect(labelTexts).not.toContain('自评权重')
    expect(labelTexts).not.toContain('上级评权重')
    expect(labelTexts).not.toContain('协作评权重')
  })

  it('renders reviewer weights tab with correct labels', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()
    await nextTick()

    const tabs = wrapper.findAll('.el-tabs__item')
    const reviewerTab = tabs.find(t => t.text().includes('评价人权重'))
    expect(reviewerTab).toBeTruthy()
    await reviewerTab.trigger('click')
    await nextTick()

    const labels = wrapper.findAll('.el-form-item__label')
    const labelTexts = labels.map(l => l.text())
    expect(labelTexts).toContain('自评')
    expect(labelTexts).toContain('上级')
    expect(labelTexts).toContain('协作')
  })

  it('calculates dimension weight total correctly', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()
    await nextTick()

    // Default dimension weights: 60 + 20 + 20 = 100
    expect(wrapper.vm.weightTotal).toBe(100)

    // Change performance to 50
    wrapper.vm.dimensionWeights.performance = 50
    await nextTick()
    expect(wrapper.vm.weightTotal).toBe(90)
  })

  it('blocks saving dimension weights when total is not 100', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()
    await nextTick()

    wrapper.vm.dimensionWeights.performance = 50
    await nextTick()
    expect(wrapper.vm.weightTotal).toBe(90)

    await wrapper.vm.saveDimensionWeights()
    expect(mockUpdateDimensionWeights).not.toHaveBeenCalled()
  })

  it('saves dimension weights successfully when total is 100', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()
    await nextTick()

    wrapper.vm.dimensionWeights.performance = 50
    wrapper.vm.dimensionWeights.ability = 30
    wrapper.vm.dimensionWeights.attitude = 20
    await nextTick()
    expect(wrapper.vm.weightTotal).toBe(100)

    await wrapper.vm.saveDimensionWeights()
    expect(mockUpdateDimensionWeights).toHaveBeenCalledWith(
      expect.objectContaining({ performance: 50, ability: 30, attitude: 20 })
    )
  })
})
