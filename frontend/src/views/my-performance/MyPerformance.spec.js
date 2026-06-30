import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import MyPerformance from '@/views/my-performance/MyPerformance.vue'

const mockGetMyAssessment = vi.fn()
const mockGetEmployeeTrend = vi.fn()
const mockGetAssessmentDetail = vi.fn()
const mockDownloadRecordPdf = vi.fn()

vi.mock('@/api/scores', () => ({
  getMyAssessment: (...args) => mockGetMyAssessment(...args),
  getAssessmentDetail: (...args) => mockGetAssessmentDetail(...args),
  downloadRecordPdf: (...args) => mockDownloadRecordPdf(...args),
}))

vi.mock('@/api/reports', () => ({
  getEmployeeTrend: (...args) => mockGetEmployeeTrend(...args),
}))

vi.mock('echarts', () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    dispose: vi.fn(),
  })),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    user: { employee_id: 1, role: 'employee' },
    token: 'token',
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
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

const PageContainerStub = {
  name: 'PageContainer',
  props: ['title'],
  template: '<div class="page-container"><h2>{{ title }}</h2><slot /></div>',
}

describe('MyPerformance.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetMyAssessment.mockResolvedValue({
      items: [
        {
          record_id: 1,
          cycle_id: 10,
          cycle_name: '2026 Q1',
          total_score: '85.0',
          grade: 'B',
          status: 'published',
          self_scores: { performance: 80, ability: 85, attitude: 90 },
          manager_scores: { performance: 82, ability: 83, attitude: 88 },
          peer_scores: { ability: 84 },
          weighted_performance: '82.5',
          weighted_ability: '83.5',
          weighted_attitude: '88.0',
          manager_comment: '表现良好',
        },
      ],
      total: 1,
    })
    mockGetEmployeeTrend.mockResolvedValue({
      items: [
        {
          cycle_name: '2026 Q1',
          total_score: 85,
          weighted_performance: 82.5,
          weighted_ability: 83.5,
          weighted_attitude: 88,
        },
      ],
    })
    mockGetAssessmentDetail.mockResolvedValue({
      record_id: 1,
      cycle_name: '2026 Q1',
      status: 'published',
      total_score: '85.0',
      grade: 'B',
      self_scores: { performance: 80, ability: 85, attitude: 90 },
      manager_scores: { performance: 82, ability: 83, attitude: 88 },
      peer_scores: { ability: 84 },
      weighted_performance: '82.5',
      weighted_ability: '83.5',
      weighted_attitude: '88.0',
      manager_comment: '表现良好，继续努力',
      kpi_details: [
        { kpi_name: '销售额完成率', weight: '50', target_value: '100万', self_score: '80', manager_score: '82' },
      ],
      appeal: null,
      interview: null,
    })
    mockDownloadRecordPdf.mockResolvedValue(new Blob(['pdf'], { type: 'application/pdf' }))
  })

  it('renders title and loads records on mount', async () => {
    const wrapper = mount(MyPerformance, {
      global: { stubs: { PageContainer: PageContainerStub } },
    })
    await flushPromises()
    await nextTick()

    expect(mockGetMyAssessment).toHaveBeenCalled()
    expect(wrapper.find('h2').text()).toBe('我的绩效')
    expect(wrapper.vm.records.length).toBe(1)
  })

  it('opens detail drawer and loads detail when viewDetail is clicked', async () => {
    const wrapper = mount(MyPerformance, {
      global: { stubs: { PageContainer: PageContainerStub } },
    })
    await flushPromises()
    await nextTick()

    wrapper.vm.viewDetail({ record_id: 1 })
    await flushPromises()
    await nextTick()

    expect(mockGetAssessmentDetail).toHaveBeenCalledWith(1)
    expect(wrapper.vm.detailDrawerVisible).toBe(true)
    expect(wrapper.vm.detailRecord).not.toBeNull()
    expect(wrapper.vm.detailRecord.cycle_name).toBe('2026 Q1')
    expect(wrapper.vm.detailRecord.kpi_details.length).toBe(1)
  })

  it('shows dimension compare data correctly', async () => {
    const wrapper = mount(MyPerformance, {
      global: { stubs: { PageContainer: PageContainerStub } },
    })
    await flushPromises()
    await nextTick()

    wrapper.vm.viewDetail({ record_id: 1 })
    await flushPromises()
    await nextTick()

    const compareData = wrapper.vm.dimensionCompareData
    expect(compareData.length).toBe(3)
    expect(compareData[0].dimension).toBe('业绩')
    expect(compareData[0].self).toBe(80)
    expect(compareData[0].manager).toBe(82)
    expect(compareData[0].weighted).toBe('82.5')
  })

  it('shows appeal and interview when present', async () => {
    mockGetAssessmentDetail.mockResolvedValue({
      record_id: 1,
      cycle_name: '2026 Q1',
      status: 'published',
      total_score: '85.0',
      grade: 'B',
      self_scores: {},
      manager_scores: {},
      peer_scores: {},
      kpi_details: [],
      appeal: {
        id: 1,
        reason: '对评分有异议',
        status: 'pending',
        review_result: null,
        reviewer_name: null,
      },
      interview: {
        id: 1,
        interviewer_name: '李经理',
        interview_time: '2026-06-30T10:00:00',
        location: '会议室A',
        content: '绩效面谈',
        improvement_plan: '提升技术能力',
      },
    })

    const wrapper = mount(MyPerformance, {
      global: { stubs: { PageContainer: PageContainerStub } },
    })
    await flushPromises()
    await nextTick()

    wrapper.vm.viewDetail({ record_id: 1 })
    await flushPromises()
    await nextTick()

    expect(wrapper.vm.detailRecord.appeal).not.toBeNull()
    expect(wrapper.vm.detailRecord.appeal.reason).toBe('对评分有异议')
    expect(wrapper.vm.detailRecord.interview).not.toBeNull()
    expect(wrapper.vm.detailRecord.interview.content).toBe('绩效面谈')
  })

  it('calls download PDF API when download button clicked', async () => {
    const wrapper = mount(MyPerformance, {
      global: { stubs: { PageContainer: PageContainerStub } },
    })
    await flushPromises()
    await nextTick()

    wrapper.vm.viewDetail({ record_id: 1 })
    await flushPromises()
    await nextTick()

    await wrapper.vm.downloadPdf()
    expect(mockDownloadRecordPdf).toHaveBeenCalledWith(1)
  })
})
