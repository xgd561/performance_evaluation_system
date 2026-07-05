import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import SummaryDashboard from '@/views/summary/SummaryDashboard.vue'

const mockGetScoreSummary = vi.fn()
const mockCalculateScores = vi.fn()
const mockGetDistribution = vi.fn()
const mockListCycles = vi.fn()
const mockListDepartments = vi.fn()

vi.mock('@/api/scores', () => ({
  getScoreSummary: (...args) => mockGetScoreSummary(...args),
  calculateScores: (...args) => mockCalculateScores(...args),
}))

vi.mock('@/api/reports', () => ({
  getDistribution: (...args) => mockGetDistribution(...args),
}))

vi.mock('@/api/cycles', () => ({
  listCycles: (...args) => mockListCycles(...args),
}))

vi.mock('@/api/departments', () => ({
  listDepartments: (...args) => mockListDepartments(...args),
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

vi.mock('vue-echarts', () => ({
  default: {
    name: 'VChart',
    template: '<div class="mock-vchart" :data-option="JSON.stringify($attrs.option)"></div>',
    props: ['option', 'autoresize'],
  },
}))

describe('SummaryDashboard.vue', () => {
  const mockSummaryData = [
    {
      employee_no: 'EMP001',
      employee_name: '张三',
      department_name: '研发部',
      position_name: '工程师',
      total_score: 95,
      grade: 'A',
      original_grade: null,
      weighted_performance: 90,
      weighted_ability: 85,
      weighted_attitude: 88,
      status: 'pending_approval',
    },
    {
      employee_no: 'EMP002',
      employee_name: '李四',
      department_name: '销售部',
      position_name: '销售经理',
      total_score: 55,
      grade: 'D',
      original_grade: null,
      weighted_performance: 50,
      weighted_ability: 60,
      weighted_attitude: 55,
      status: 'pending_distribution_review',
    },
    {
      employee_no: 'EMP003',
      employee_name: '王五',
      department_name: '市场部',
      position_name: '市场专员',
      total_score: 99.5,
      grade: 'A',
      original_grade: 'B',
      weighted_performance: 98,
      weighted_ability: 100,
      weighted_attitude: 99,
      status: 'published',
    },
  ]

  const mockDistribution = {
    total_records: 3,
    overall_distribution: {
      A: 2,
      B: 0,
      C: 0,
      D: 1,
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockListCycles.mockResolvedValue([{ id: 1, name: '2024 Q1' }])
    mockListDepartments.mockResolvedValue([{ id: 1, name: '研发部' }])
    mockGetScoreSummary.mockResolvedValue(mockSummaryData)
    mockGetDistribution.mockResolvedValue(mockDistribution)
  })

  it('renders the table with summary data', async () => {
    const wrapper = mount(SummaryDashboard)
    await flushPromises()
    await nextTick()

    // Trigger search to load data
    wrapper.vm.queryForm.cycle_id = 1
    await wrapper.vm.handleSearch()
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('李四')
    expect(wrapper.text()).toContain('王五')
    expect(wrapper.text()).toContain('研发部')
    expect(wrapper.text()).toContain('销售部')
  })

  it('shows danger tag for abnormal scores (<60 or >98)', async () => {
    const wrapper = mount(SummaryDashboard)
    await flushPromises()
    await nextTick()

    wrapper.vm.queryForm.cycle_id = 1
    await wrapper.vm.handleSearch()
    await flushPromises()
    await nextTick()

    const tags = wrapper.findAll('.el-tag')
    const tagTypes = tags.map(t => t.classes())

    // Find tags that contain abnormal scores
    const dangerTags = tags.filter(t => {
      const text = t.text()
      const score = parseFloat(text)
      return !isNaN(score) && (score < 60 || score > 98)
    })

    expect(dangerTags.length).toBeGreaterThan(0)
    dangerTags.forEach(tag => {
      expect(tag.classes()).toContain('el-tag--danger')
    })
  })

  it('shows force adjustment icon when original_grade differs from grade', async () => {
    const wrapper = mount(SummaryDashboard)
    await flushPromises()
    await nextTick()

    wrapper.vm.queryForm.cycle_id = 1
    await wrapper.vm.handleSearch()
    await flushPromises()
    await nextTick()

    // Check that the WarningFilled icon is rendered for the adjusted grade row
    const icons = wrapper.findAll('.force-adjust-icon')
    expect(icons.length).toBe(1)

    // Verify tooltip content via the tooltip component
    const tooltip = wrapper.findAllComponents({ name: 'ElTooltip' })
      .find(t => t.props('content')?.includes('强制分布调整'))
    expect(tooltip).toBeTruthy()
    expect(tooltip.props('content')).toBe('强制分布调整: 原等级 B → 调整后 A')
  })

  it('renders pie chart when distribution data is present', async () => {
    const wrapper = mount(SummaryDashboard)
    await flushPromises()
    await nextTick()

    wrapper.vm.queryForm.cycle_id = 1
    await wrapper.vm.handleSearch()
    await flushPromises()
    await nextTick()

    const chartCard = wrapper.findAll('.el-card').find(card => card.text().includes('等级分布图'))
    expect(chartCard).toBeTruthy()

    const vChart = wrapper.findComponent({ name: 'VChart' })
    expect(vChart.exists()).toBe(true)
  })

  it('does not render pie chart when distribution is empty', async () => {
    mockGetDistribution.mockResolvedValue({
      total_records: 0,
      overall_distribution: {},
    })

    const wrapper = mount(SummaryDashboard)
    await flushPromises()
    await nextTick()

    wrapper.vm.queryForm.cycle_id = 1
    await wrapper.vm.handleSearch()
    await flushPromises()
    await nextTick()

    const chartCard = wrapper.findAll('.el-card').find(card => card.text().includes('等级分布图'))
    expect(chartCard).toBeFalsy()
  })

  it('correctly maps pending_distribution_review status to 待分布审核', async () => {
    const wrapper = mount(SummaryDashboard)
    await flushPromises()
    await nextTick()

    wrapper.vm.queryForm.cycle_id = 1
    await wrapper.vm.handleSearch()
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('待分布审核')
  })

  it('calls handleCalculate API and refreshes data', async () => {
    const wrapper = mount(SummaryDashboard)
    await flushPromises()
    await nextTick()

    wrapper.vm.queryForm.cycle_id = 1
    await wrapper.vm.handleCalculate()
    await flushPromises()
    await nextTick()

    expect(mockCalculateScores).toHaveBeenCalledWith(1)
    // handleSearch is called inside handleCalculate, so total calls = 1 (initial mount) + 1 (after calculate)
    expect(mockGetScoreSummary).toHaveBeenCalledTimes(1)
    expect(mockGetDistribution).toHaveBeenCalledTimes(1)
  })
})
