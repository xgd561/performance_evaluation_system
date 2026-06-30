import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import KpiAdjustmentRequest from '@/views/kpi-adjustment/KpiAdjustmentRequest.vue'

const mockGetToReviewList = vi.fn()
const mockRequestKpiAdjustment = vi.fn()

vi.mock('@/api/scores', () => ({
  getToReviewList: (...args) => mockGetToReviewList(...args),
}))

vi.mock('@/api/kpiAdjustment', () => ({
  requestKpiAdjustment: (...args) => mockRequestKpiAdjustment(...args),
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

describe('KpiAdjustmentRequest.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetToReviewList.mockResolvedValue([
      {
        record_id: 1,
        employee_id: 10,
        employee_name: '张三',
        employee_no: 'EMP001',
        cycle_name: '2026 Q1',
        kpi_snapshot: [
          { id: 1, name: '销售额完成率', weight: '50', target_value: '100万' },
          { id: 2, name: '客户满意度', weight: '30', target_value: '90分' },
        ],
      },
    ])
    mockRequestKpiAdjustment.mockResolvedValue({ message: 'ok' })
  })

  it('renders title and record selector', async () => {
    const wrapper = mount(KpiAdjustmentRequest)
    await flushPromises()
    await nextTick()

    expect(wrapper.find('h2').text()).toBe('KPI 动态调整申请')
    expect(wrapper.find('.el-select').exists()).toBe(true)
  })

  it('loads to-review list on mount', async () => {
    const wrapper = mount(KpiAdjustmentRequest)
    await flushPromises()
    await nextTick()

    expect(mockGetToReviewList).toHaveBeenCalled()
    expect(wrapper.vm.toReviewList.length).toBe(1)
    expect(wrapper.vm.toReviewList[0].employee_name).toBe('张三')
  })

  it('shows KPI table after selecting record and submits adjustment', async () => {
    const wrapper = mount(KpiAdjustmentRequest)
    await flushPromises()
    await nextTick()

    // Select record
    wrapper.vm.selectedRecordId = 1
    await nextTick()

    expect(wrapper.vm.kpiItems.length).toBe(2)
    expect(wrapper.vm.kpiItems[0].name).toBe('销售额完成率')
    expect(wrapper.vm.kpiItems[0].target).toBe('100万')

    // Fill form
    wrapper.vm.adjustForm.kpi_id = 1
    wrapper.vm.adjustForm.new_target = '120万'
    wrapper.vm.adjustForm.reason = '市场变化'
    await nextTick()

    // Trigger submit directly
    wrapper.vm.handleSubmit()
    await flushPromises()
    await nextTick()

    expect(mockRequestKpiAdjustment).toHaveBeenCalledWith(1, {
      kpi_id: 1,
      new_target: '120万',
      reason: '市场变化',
    })
  })
})
