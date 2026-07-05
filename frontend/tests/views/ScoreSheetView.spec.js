import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import ScoreSheetView from '@/views/score-sheet/ScoreSheetView.vue'

const mockGetToReviewList = vi.fn()
const mockSubmitManagerScore = vi.fn()
const mockGetManagerDraft = vi.fn()
const mockSaveManagerDraft = vi.fn()
const mockDeleteManagerDraft = vi.fn()

vi.mock('@/api/scores', () => ({
  getToReviewList: (...args) => mockGetToReviewList(...args),
  submitManagerScore: (...args) => mockSubmitManagerScore(...args),
  getManagerDraft: (...args) => mockGetManagerDraft(...args),
  saveManagerDraft: (...args) => mockSaveManagerDraft(...args),
  deleteManagerDraft: (...args) => mockDeleteManagerDraft(...args),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    user: { role: 'manager', name: '张经理' },
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
    ElMessageBox: {
      confirm: vi.fn().mockResolvedValue(true),
    },
  }
})

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
}))

describe('ScoreSheetView.vue', () => {
  const mockRecord = {
    record_id: 1,
    employee_name: '王员工',
    employee_no: 'EMP001',
    department_name: '研发部',
    position_name: '工程师',
    cycle_name: '2024 Q1',
    manager_due_date: '2024-04-15T23:59:59',
    status: 'pending_manager',
    self_scores: { performance: 85, ability: 80, attitude: 90 },
    kpi_snapshot: {
      items: [
        { name: '代码质量', weight: 40, target: '95%', self_score: 88 },
      ],
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockGetToReviewList.mockResolvedValue([mockRecord])
    mockGetManagerDraft.mockResolvedValue({ has_draft: false, draft: null })
  })

  it('renders employee info and score inputs', async () => {
    const wrapper = mount(ScoreSheetView)
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('王员工')
    expect(wrapper.text()).toContain('研发部')
    expect(wrapper.text()).toContain('工程师')

    const labels = wrapper.findAll('.dim-name')
    const labelTexts = labels.map(l => l.text())
    expect(labelTexts).toContain('工作业绩')
    expect(labelTexts).toContain('工作能力')
    expect(labelTexts).toContain('工作态度')
  })

  it('loads self-assessment reference scores', async () => {
    const wrapper = mount(ScoreSheetView)
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('员工自评参考')
    expect(wrapper.text()).toContain('85')
    expect(wrapper.text()).toContain('80')
    expect(wrapper.text()).toContain('90')
  })

  it('submits manager scores with comment', async () => {
    const wrapper = mount(ScoreSheetView)
    await flushPromises()
    await nextTick()

    wrapper.vm.scoreForm.dimensionScores.performance = 88
    wrapper.vm.scoreForm.dimensionScores.ability = 82
    wrapper.vm.scoreForm.dimensionScores.attitude = 85
    wrapper.vm.scoreForm.comment = '该员工表现优秀，完成了所有KPI指标，值得肯定。'
    await nextTick()

    await wrapper.vm.handleSubmit()
    await flushPromises()

    expect(mockSubmitManagerScore).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        performance: 88,
        ability: 82,
        attitude: 85,
        comment: '该员工表现优秀，完成了所有KPI指标，值得肯定。',
      })
    )
  })

  it('validates comment length (>=20 chars)', async () => {
    const wrapper = mount(ScoreSheetView)
    await flushPromises()
    await nextTick()

    wrapper.vm.scoreForm.dimensionScores.performance = 88
    wrapper.vm.scoreForm.dimensionScores.ability = 82
    wrapper.vm.scoreForm.dimensionScores.attitude = 85
    wrapper.vm.scoreForm.comment = '太短'
    await nextTick()

    expect(wrapper.vm.canSubmit).toBe(false)
  })

  it('shows alert when self/manager score diff > 20', async () => {
    const wrapper = mount(ScoreSheetView)
    await flushPromises()
    await nextTick()

    // Self score is 85, manager gives 10 -> diff 75 > 20
    wrapper.vm.scoreForm.dimensionScores.performance = 10
    wrapper.vm.scoreForm.dimensionScores.ability = 82
    wrapper.vm.scoreForm.dimensionScores.attitude = 85
    wrapper.vm.scoreForm.comment = '该员工表现一般，需要改进工作方法和效率。'
    await nextTick()

    await wrapper.vm.handleSubmit()
    await nextTick()

    expect(wrapper.vm.diffDialogVisible).toBe(true)
    expect(wrapper.vm.diffDimension).toBe('工作业绩')
    expect(wrapper.vm.diffScore).toBe(10)
    expect(wrapper.vm.diffSelfScore).toBe(85)
  })
})
