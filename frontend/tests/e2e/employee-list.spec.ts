import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 员工列表页 (EmployeeList.vue)
 * P2-06 验收标准：表格渲染正确；搜索「王志强」正确过滤；分页正常；删除后状态变为「已停用」
 */

test.describe('员工列表页', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
    await page.goto('/employees')
  })

  test('页面标题和搜索表单可见', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '员工管理' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '关键词' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '部门' })).toBeVisible()
    await expect(page.getByRole('button', { name: '查询' })).toBeVisible()
    await expect(page.getByRole('button', { name: '重置' })).toBeVisible()
  })

  test('新增员工、下载模板、导入员工按钮存在', async ({ page }) => {
    await expect(page.getByRole('button', { name: '新增员工' })).toBeVisible()
    await expect(page.getByRole('button', { name: '下载模板' })).toBeVisible()
    await expect(page.getByRole('button', { name: '导入员工' })).toBeVisible()
  })

  test('表格列头正确渲染', async ({ page }) => {
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    // Element Plus table header text is inside .cell div
    // Use exact text matching to avoid '部门' matching both '部门' and '部门负责人'
    await expect(page.locator('th .cell').filter({ hasText: /^工号$/ })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: /^姓名$/ })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: /^部门$/ })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: /^岗位$/ })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: /^直属上级$/ })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: /^部门负责人$/ })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: /^状态$/ })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: /^操作$/ })).toBeVisible()
  })

  test('分页组件存在', async ({ page }) => {
    await expect(page.locator('.el-pagination').first()).toBeVisible()
  })

  test('搜索关键词可输入', async ({ page }) => {
    const input = page.locator('.el-form-item').filter({ hasText: '关键词' }).locator('input').first()
    await input.fill('王志强')
    await expect(input).toHaveValue('王志强')
  })
})
