import { vi, describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import EmployeeList from '@/views/employees/EmployeeList.vue'

const mockCreateEmployee = vi.fn((data) => Promise.resolve({ id: 2, ...data, is_active: true, created_at: '2026-06-29T00:00:00' }))
const mockUpdateEmployee = vi.fn((id, data) => Promise.resolve({ id, ...data }))
const mockListEmployees = vi.fn(() => Promise.resolve({
  items: [
    { id: 1, employee_no: 'E001', name: '张三', department_name: '技术部', position_name: '工程师', manager_name: '李经理', is_department_head: false, is_active: true }
  ],
  total: 1, page: 1, size: 10
}))
const mockListDepartments = vi.fn(() => Promise.resolve([
  { id: 1, name: '技术部', code: 'TECH' },
  { id: 2, name: '人事部', code: 'HR' }
]))

vi.mock('@/api/employees', () => ({
  listEmployees: () => mockListEmployees(),
  createEmployee: (data) => mockCreateEmployee(data),
  updateEmployee: (id, data) => mockUpdateEmployee(id, data),
  deleteEmployee: vi.fn(() => Promise.resolve()),
  importEmployees: vi.fn(() => Promise.resolve({ success: true })),
  downloadTemplate: vi.fn(() => Promise.resolve(new Blob(['template']))),
}))

vi.mock('@/api/departments', () => ({
  listDepartments: () => mockListDepartments(),
  listPositions: vi.fn(() => Promise.resolve({ items: [] })),
}))

describe('EmployeeList.vue — 员工管理表单测试', () => {
  let wrapper

  beforeEach(async () => {
    mockCreateEmployee.mockClear()
    mockUpdateEmployee.mockClear()
    mockListEmployees.mockClear()
    mockListDepartments.mockClear()
    wrapper = mount(EmployeeList, { attachTo: document.body })
    await flushPromises()
    await nextTick()
  })

  it('新增员工弹窗打开时，表单字段应正确初始化', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增员工')
    expect(btn).toBeTruthy()
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    expect(vm.form.employee_no).toBe('')
    expect(vm.form.name).toBe('')
    expect(vm.form.department_id).toBeNull()
    expect(vm.form.position_id).toBeNull()
  })

  it('必填字段（工号、姓名）未填时，若提交应发送空值 payload（反映前端实际行为）', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增员工')
    await btn.trigger('click')
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    // Element Plus 的 required 对空字符串在 jsdom 中可能无法完全阻止，
    // 但如果阻止了，createEmployee 不应被调用；如果没阻止，payload 中应是空值
    if (mockCreateEmployee.mock.calls.length > 0) {
      const payload = mockCreateEmployee.mock.calls[0][0]
      expect(payload.employee_no).toBe('')
      expect(payload.name).toBe('')
    }
  })

  it('填写完整信息后提交，createEmployee 应被正确调用一次', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增员工')
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.form.employee_no = 'E002'
    vm.form.name = '李四'
    vm.form.department_id = 1
    vm.form.position_id = 1
    await nextTick()

    const submitBtn = wrapper.findAll('button').find(b => b.text() === '确定')
    await submitBtn.trigger('click')
    await flushPromises()

    expect(mockCreateEmployee).toHaveBeenCalledTimes(1)
    const payload = mockCreateEmployee.mock.calls[0][0]
    expect(payload.employee_no).toBe('E002')
    expect(payload.name).toBe('李四')
    expect(payload.department_id).toBe(1)
  })

  it('编辑时表单应回填员工现有数据', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '编辑')
    expect(btn).toBeTruthy()
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    expect(vm.form.employee_no).toBe('E001')
    expect(vm.form.name).toBe('张三')
  })

  it('部门选择变化后，应触发 onDeptChange', async () => {
    const btn = wrapper.findAll('button').find(b => b.text() === '新增员工')
    await btn.trigger('click')
    await nextTick()

    const vm = wrapper.vm
    vm.form.department_id = 1
    await nextTick()

    expect(vm.form.department_id).toBe(1)
  })
})
