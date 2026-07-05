import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 岗位管理页面 (PositionList.vue)
 * P2-04 验收标准：表格正确渲染；按部门筛选正确过滤；删除有员工的岗位时提示
 */

test.describe('岗位管理页面', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
    await page.goto('/positions')
  })

  test('页面标题和筛选表单可见', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '岗位管理' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '所属部门' })).toBeVisible()
    await expect(page.getByRole('button', { name: '查询' })).toBeVisible()
    await expect(page.getByRole('button', { name: '重置' })).toBeVisible()
  })

  test('新增岗位按钮存在', async ({ page }) => {
    await expect(page.getByRole('button', { name: '新增岗位' })).toBeVisible()
  })

  test('表格列头正确渲染', async ({ page }) => {
    // 等待表格列头渲染
    await page.waitForSelector('.el-table__header th')
    await expect(page.locator('.el-table__header th').filter({ hasText: '岗位名称' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '所属部门' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '职级' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '人数' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '操作' })).toBeVisible()
  })

  test('点击新增岗位弹出表单且可填写', async ({ page }) => {
    await page.getByRole('button', { name: '新增岗位' }).click()
    await expect(page.locator('.el-dialog__title').filter({ hasText: '新增岗位' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '岗位名称' }).locator('input').first()).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '所属部门' }).locator('.el-select').first()).toBeVisible()
  })

  test('部门筛选下拉可交互', async ({ page }) => {
    const select = page.locator('.el-form-item').filter({ hasText: '所属部门' }).locator('.el-select').first()
    await select.click()
    await page.locator('.el-select-dropdown').last().waitFor({ state: 'visible' })
    // 断言下拉出现（至少包含选项或空）
    await expect(page.locator('.el-select-dropdown').last()).toBeVisible()
  })
})
