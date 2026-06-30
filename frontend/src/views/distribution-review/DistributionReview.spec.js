import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import DistributionReview from '@/views/distribution-review/DistributionReview.vue'

const mockListCycles = vi.fn()
const mockGetDistributionAdjustments = vi.fn()
const mockGetDistributionOverrides = vi.fn()
const mockApproveDistributionOverride = vi.fn()
const mockRejectDistributionOverride = vi.fn()

vi.mock('@/api/cycles', () => ({
  listCycles: (...args) => mockListCycles(...args),
}))

vi.mock('@/api/distribution', () => ({
  getDistributionAdjustments: (...args) => mockGetDistributionAdjustments(...args),
  getDistributionOverrides: (...args) => mockGetDistributionOverrides(...args),
  approveDistributionOverride: (...args) => mockApproveDistributionOverride(...args),
  rejectDistributionOverride: (...args) => mockRejectDistributionOverride(...args),
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessageBox: {
      confirm: vi.fn(() => Promise.resolve()),
    },
    ElMessage: {
      success: vi.fn(),
      warning: vi.fn(),
      error: vi.fn(),
    },
  }
})

describe('DistributionReview.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListCycles.mockResolvedValue([
      { id: 1, name: '2026 Q1' },
      { id: 2, name: '2026 Q2' },
    ])
    mockGetDistributionAdjustments.mockResolvedValue({
      adjustments: [
        {
          record_id: 1,
          employee_id: 10,
          employee_name: '张三',
          employee_no: 'EMP001',
          total_score: '93',
          original_grade: 'A',
          adjusted_grade: 'B',
          is_override: false,
          override_reason: null,
        },
      ],
    })
    mockGetDistributionOverrides.mockResolvedValue([
      {
        record_id: 2,
        employee_id: 20,
        employee_name: '李四',
        employee_no: 'EMP002',
        total_score: '94',
        original_grade: 'A',
        adjusted_grade: 'B',
        override_reason: '该员工表现优异，应保留A等级',
      },
    ])
    mockApproveDistributionOverride.mockResolvedValue({ message: 'ok' })
    mockRejectDistributionOverride.mockResolvedValue({ message: 'ok' })
  })

  it('renders cycle selector and query button', async () => {
    const wrapper = mount(DistributionReview)
    await flushPromises()
    await nextTick()

    expect(wrapper.find('h2').text()).toBe('强制分布处理')
    expect(wrapper.find('.el-select').exists()).toBe(true)
  })

  it('loads adjustments and overrides after selecting cycle and clicking query', async () => {
    const wrapper = mount(DistributionReview)
    await flushPromises()
    await nextTick()

    wrapper.vm.queryForm.cycle_id = 1
    await nextTick()

    const btns = wrapper.findAll('button')
    const queryBtn = btns.find((b) => b.text().includes('查询'))
    expect(queryBtn).toBeTruthy()
    await queryBtn?.trigger('click')
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('李四')
    expect(mockGetDistributionAdjustments).toHaveBeenCalledWith(1)
    expect(mockGetDistributionOverrides).toHaveBeenCalled()
  })

  it('calls approve API when approve button is clicked', async () => {
    const wrapper = mount(DistributionReview)
    await flushPromises()
    await nextTick()

    wrapper.vm.queryForm.cycle_id = 1
    await nextTick()

    const btns = wrapper.findAll('button')
    const queryBtn = btns.find((b) => b.text().includes('查询'))
    await queryBtn?.trigger('click')
    await flushPromises()
    await nextTick()

    // Trigger handleApprove directly since ElMessageBox is mocked
    wrapper.vm.handleApprove(2)
    await flushPromises()
    await nextTick()

    expect(mockApproveDistributionOverride).toHaveBeenCalledWith(2)
  })
})
