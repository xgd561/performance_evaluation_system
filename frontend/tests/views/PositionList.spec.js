import { vi, describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import PositionList from '@/views/positions/PositionList.vue'

const mockListPositions = vi.fn(() => Promise.resolve({
  items: [
    { id: 1, name: 'Java工程师', department_id: 1, department_name: '技术部', level: 'P5', employee_count: 3 }
  ],
  total: 1, page: 1, size: 10
}))
const mockListDepartments = vi.fn(() => Promise.resolve([
  { id: 1, name: '技术部', code: 'TECH' }
]))
const mockListEmployees = vi.fn(() => Promise.resolve({
  items: [
    { id: 1, employee_no: 'E001', name: '张三', position_id: 1, department_id: 1 }
  ],
  total: 1, page: 1, size: 10
}))
const mockDeletePosition = vi.fn(() => Promise.resolve())

vi.mock('@/api/departments', () => ({
  listPositions: (params) => mockListPositions(params),
  listDepartments: () => mockListDepartments(),
  createPosition: vi.fn(() => Promise.resolve({ id: 2, name: '新岗位' })),
  updatePosition: vi.fn(() => Promise.resolve({ id: 1, name: '更新岗位' })),
  deletePosition: (id) => mockDeletePosition(id),
}))

vi.mock('@/api/employees', () => ({
  listEmployees: (params) => mockListEmployees(params),
}))

describe('PositionList.vue — 岗位管理测试', () => {
  let wrapper

  beforeEach(async () => {
    mockListPositions.mockClear()
    mockListDepartments.mockClear()
    mockListEmployees.mockClear()
    mockDeletePosition.mockClear()
    wrapper = mount(PositionList, { attachTo: document.body })
    await flushPromises()
    await nextTick()
  })

  it('页面标题应为「岗位管理」', () => {
    expect(wrapper.text()).toContain('岗位管理')
  })

  it('表格应渲染岗位名称、所属部门、职级、人数、操作列', () => {
    const headers = wrapper.findAll('th').map(th => th.text())
    expect(headers).toContain('岗位名称')
    expect(headers).toContain('所属部门')
    expect(headers).toContain('职级')
    expect(headers).toContain('人数')
    expect(headers).toContain('操作')
  })

  it('点击「新增岗位」应打开弹窗并初始化表单', async () => {
    const btn = wrapper.findAll('button').find(b => b.text().includes('新增岗位'))
    expect(btn).toBeTruthy()
    await btn.trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('新增岗位')
  })

  it('部门筛选后应重新查询', async () => {
    const vm = wrapper.vm
    vm.queryForm.department_id = 1
    await nextTick()
    vm.handleSearch()
    await flushPromises()
    expect(mockListPositions).toHaveBeenCalled()
  })

  it('删除岗位时应调用 deletePosition', async () => {
    const deleteBtn = wrapper.findAll('button').find(b => b.text().includes('删除'))
    if (deleteBtn) {
      await deleteBtn.trigger('click')
      await flushPromises()
      expect(mockDeletePosition).toHaveBeenCalledTimes(1)
    }
  })
})
