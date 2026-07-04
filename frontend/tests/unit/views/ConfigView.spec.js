import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { ElMessage } from 'element-plus'

// Mock API module
vi.mock('@/api/config', () => ({
  getGradeRules: vi.fn(() => Promise.resolve({
    A: { min: 90, max: 100, ratio_limit: 0.2 },
    B: { min: 80, max: 89.9, ratio_limit: 0.5 },
    C: { min: 60, max: 79.9, ratio_limit: 0.25 },
    D: { min: 0, max: 59.9, ratio_limit: 0.05 },
  })),
  getDimensionWeights: vi.fn(() => Promise.resolve({ performance: 60, ability: 20, attitude: 20 })),
  getReviewerWeights: vi.fn(() => Promise.resolve({
    performance: { self: 30, manager: 70, peer: 0 },
    ability: { self: 20, manager: 60, peer: 20 },
    attitude: { self: 10, manager: 50, peer: 40 },
  })),
  getSmallDeptExemption: vi.fn(() => Promise.resolve({ enabled: true, threshold: 5 })),
  getPeerReviewEnabled: vi.fn(() => Promise.resolve({ enabled: true })),
  updateGradeRules: vi.fn(() => Promise.resolve({ code: 200 })),
  updateDimensionWeights: vi.fn(() => Promise.resolve({ code: 200 })),
  updateReviewerWeights: vi.fn(() => Promise.resolve({ code: 200 })),
  updateSmallDeptExemption: vi.fn(() => Promise.resolve({ code: 200 })),
  updatePeerReviewEnabled: vi.fn(() => Promise.resolve({ code: 200 })),
}))

import {
  updateGradeRules,
  updateDimensionWeights,
} from '@/api/config'

import ConfigView from '@/views/config/ConfigView.vue'

describe('ConfigView.vue', () => {
  beforeEach(() => {
    vi.spyOn(ElMessage, 'success').mockImplementation(() => {})
    vi.spyOn(ElMessage, 'warning').mockImplementation(() => {})
    vi.spyOn(ElMessage, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders 5 tabs correctly on page load', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()

    const tabs = wrapper.findAll('.el-tabs__item')
    expect(tabs.length).toBe(5)

    const labels = tabs.map(t => t.text())
    expect(labels).toContain('等级规则')
    expect(labels).toContain('维度权重')
    expect(labels).toContain('评价人权重')
    expect(labels).toContain('小部门豁免')
    expect(labels).toContain('协作评分开关')
  })

  it('triggers API call when save button is clicked in grade rules tab', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()

    const panes = wrapper.findAll('.el-tab-pane')
    const gradesPane = panes.find(p => p.text().includes('比例上限合计'))
    const saveBtn = gradesPane.find('.el-button--primary')

    expect(saveBtn.exists()).toBe(true)
    await saveBtn.trigger('click')
    await flushPromises()

    expect(updateGradeRules).toHaveBeenCalled()
  })

  it('disables save button when dimension weight total is not 100%', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()

    // Switch to dimension weights tab
    const tabs = wrapper.findAll('.el-tabs__item')
    const weightsTab = tabs.find(t => t.text().includes('维度权重'))
    await weightsTab.trigger('click')
    await nextTick()

    // Change performance weight to 50, total becomes 90
    wrapper.vm.dimensionWeights.performance = 50
    await nextTick()

    const panes = wrapper.findAll('.el-tab-pane')
    const weightsPane = panes.find(p => p.text().includes('工作业绩权重'))
    const saveBtn = weightsPane.find('.el-button--primary')

    expect(saveBtn.classes()).toContain('is-disabled')
  })

  it('enables save button when dimension weight total equals 100%', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()

    const tabs = wrapper.findAll('.el-tabs__item')
    const weightsTab = tabs.find(t => t.text().includes('维度权重'))
    await weightsTab.trigger('click')
    await nextTick()

    // Default values are 60+20+20=100
    const panes = wrapper.findAll('.el-tab-pane')
    const weightsPane = panes.find(p => p.text().includes('工作业绩权重'))
    const saveBtn = weightsPane.find('.el-button--primary')

    expect(saveBtn.classes()).not.toContain('is-disabled')
  })

  it('shows warning when saving grade rules with invalid ranges', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()

    // Modify grade rules to create overlap
    wrapper.vm.gradeRules.A.min = 80
    wrapper.vm.gradeRules.A.max = 100
    await nextTick()

    const panes = wrapper.findAll('.el-tab-pane')
    const gradesPane = panes.find(p => p.text().includes('比例上限合计'))
    const saveBtn = gradesPane.find('.el-button--primary')

    await saveBtn.trigger('click')
    await flushPromises()

    expect(ElMessage.warning).toHaveBeenCalled()
  })
})
