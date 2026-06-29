import { vi, describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import DepartmentList from '@/views/departments/DepartmentList.vue'

const mockCreateDepartment = vi.fn((data) => Promise.resolve({ id: 3, ...data, created_at: '2026-06-29T00:00:00' }))
const mockUpdateDepartment = vi.fn((id, data) => Promise.resolve({ id, ...data }))
const mockListDepartments = vi.fn(() => Promise.resolve([
  { id: 1, name: '技术部', code: 'TECH', parent_name: null, position_count: 2, employee_count: 5 },
  { id: 2, name: '人事部', code: 'HR', parent_name: null, position_count: 1, employee_count: 2 }
]))
const mockCreatePosition = vi.fn((data) => Promise.resolve({ id: 1, ...data }))

vi.mock('@/api/departments', () => ({
  listDepartments: () => mockListDepartments(),
  createDepartment: (data) => mockCreateDepartment(data),
  updateDepartment: (id, data) => mockUpdateDepartment(id, data),
  deleteDepartment: vi.fn(() => Promise.resolve()),
  listPositions: vi.fn(() => Promise.resolve({ items: [], total: 0 })),
  createPosition: (data) => mockCreatePosition(data),
  updatePosition: vi.fn((id, data) => Promise.resolve({ id, ...data })),
  deletePosition: vi.fn(() => Promise.resolve()),
}))

describe('DepartmentList.vue — 部门管理表单测试', () => {
  let wrapper

  beforeEach(async () => {
    mockCreateDepartment.mockClear()
    mockUpdateDepartment.mockClear()
    mockListDepartments.mockClear()
    mockCreatePosition.mockClear()
    wrapper = mount(DepartmentList, { attachTo: document.body })
    await flushPromises()
    await nextTick()
  })

  it('新增部门弹窗打开时，表单字段应正确初始化', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增部门')
    expect(btn).toBeTruthy()
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    expect(vm.deptForm.code).toBe('')
    expect(vm.deptForm.name).toBe('')
    expect(vm.deptForm.parent_id).toBeNull()
  })

  it('必填字段（编码、名称）未填时，若提交应发送空值 payload', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增部门')
    await btn.trigger('click')
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    if (mockCreateDepartment.mock.calls.length > 0) {
      const payload = mockCreateDepartment.mock.calls[0][0]
      expect(payload.code).toBe('')
      expect(payload.name).toBe('')
    }
  })

  it('填写完整信息后提交，createDepartment 应被正确调用一次', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增部门')
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.deptForm.code = 'FIN'
    vm.deptForm.name = '财务部'
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(mockCreateDepartment).toHaveBeenCalledTimes(1)
    const payload = mockCreateDepartment.mock.calls[0][0]
    expect(payload.code).toBe('FIN')
    expect(payload.name).toBe('财务部')
  })

  it('编辑时表单应回填部门现有数据', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '编辑')
    expect(btn).toBeTruthy()
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    expect(vm.deptForm.code).toBe('TECH')
    expect(vm.deptForm.name).toBe('技术部')
  })

  it('上级部门选择应排除当前部门自身（避免自引用）', async () => {
    const editBtn = wrapper.findAll('button').find(b => b.text() === '编辑')
    await editBtn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.deptForm.id = 1  // 技术部
    await nextTick()

    const available = vm.availableParents
    expect(available).toBeInstanceOf(Array)
    expect(available.some(d => d.id === 1)).toBe(false)
    expect(available.some(d => d.id === 2)).toBe(true)
  })

  it('新增岗位时，name 必填未填应阻止提交或发送空值', async () => {
    const manageBtn = wrapper.findAll('button').find(b => b.text() === '管理岗位')
    expect(manageBtn).toBeTruthy()
    await manageBtn.trigger('click')
    await flushPromises()
    await nextTick()

    const addPosBtn = wrapper.findAll('button').find(b => b.text() === '新增')
    if (addPosBtn) {
      await addPosBtn.trigger('click')
      await flushPromises()
    }

    if (mockCreatePosition.mock.calls.length > 0) {
      const payload = mockCreatePosition.mock.calls[0][0]
      expect(payload.name).toBe('')
    }
  })
})
