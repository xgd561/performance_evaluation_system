import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import KpiAdjustmentApproval from '@/views/kpi-adjustment/KpiAdjustmentApproval.vue'

const mockGetPendingKpiAdjustments = vi.fn()
const mockApproveKpiAdjustment = vi.fn()
const mockRejectKpiAdjustment = vi.fn()

vi.mock('@/api/kpiAdjustment', () => ({
  getPendingKpiAdjustments: (...args) => mockGetPendingKpiAdjustments(...args),
  approveKpiAdjustment: (...args) => mockApproveKpiAdjustment(...args),
  rejectKpiAdjustment: (...args) => mockRejectKpiAdjustment(...args),
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

describe('KpiAdjustmentApproval.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetPendingKpiAdjustments.mockResolvedValue([
      {
        id: 1,
        record_id: 10,
        original_kpi: '[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
        adjusted_kpi: '{"kpi_id": 1, "new_target": "120万"}',
        reason: '市场变化',
        status: 'pending',
        created_at: '2026-06-30T08:00:00',
      },
    ])
    mockApproveKpiAdjustment.mockResolvedValue({ message: 'ok' })
    mockRejectKpiAdjustment.mockResolvedValue({ message: 'ok' })
  })

  it('renders title and pending table', async () => {
    const wrapper = mount(KpiAdjustmentApproval)
    await flushPromises()
    await nextTick()

    expect(wrapper.find('h2').text()).toBe('KPI 调整审批')
    expect(mockGetPendingKpiAdjustments).toHaveBeenCalled()
  })

  it('calls approve API when approve button is clicked', async () => {
    const wrapper = mount(KpiAdjustmentApproval)
    await flushPromises()
    await nextTick()

    wrapper.vm.handleApprove(1)
    await flushPromises()
    await nextTick()

    expect(mockApproveKpiAdjustment).toHaveBeenCalledWith(1)
  })
})
