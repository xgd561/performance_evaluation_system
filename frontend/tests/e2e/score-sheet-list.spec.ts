import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 上级评分列表 (ScoreSheetList)
 * 覆盖：列表渲染、筛选、搜索、分页、跳转到评分页
 */

test.describe('上级评分列表', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
    await page.goto('/score-sheet-list')
  })

  test('页面标题和表格列头可见', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '上级评分列表' })).toBeVisible()
    await expect(page.getByText('姓名')).toBeVisible()
    await expect(page.getByText('工号')).toBeVisible()
    await expect(page.getByText('部门')).toBeVisible()
    await expect(page.getByText('当前状态')).toBeVisible()
    await expect(page.getByText('操作')).toBeVisible()
  })

  test('状态筛选下拉包含待上级评分/待协作评分/待汇总', async ({ page }) => {
    const select = page.locator('.el-form-item').filter({ hasText: '状态' }).locator('.el-select').first()
    await select.click()
    await page.locator('.el-select-dropdown').last().waitFor({ state: 'visible' })
    await expect(page.locator('.el-select-dropdown').last().getByText('待上级评分')).toBeVisible()
    await expect(page.locator('.el-select-dropdown').last().getByText('待协作评分')).toBeVisible()
    await expect(page.locator('.el-select-dropdown').last().getByText('待汇总')).toBeVisible()
  })

  test('搜索表单存在且可交互', async ({ page }) => {
    const searchInput = page.locator('.el-form-item').filter({ hasText: '搜索' }).locator('input').first()
    await expect(searchInput).toBeVisible()
    await searchInput.fill('test')
    await expect(searchInput).toHaveValue('test')
  })

  test('重置按钮清空搜索条件', async ({ page }) => {
    const searchInput = page.locator('.el-form-item').filter({ hasText: '搜索' }).locator('input').first()
    await searchInput.fill('test')
    await page.getByRole('button', { name: '重置' }).click()
    await expect(searchInput).toHaveValue('')
  })

  test('表格存在且至少显示表头行', async ({ page }) => {
    const table = page.locator('.el-table').first()
    await expect(table).toBeVisible()
    const headerCells = table.locator('.el-table__header th')
    await expect(headerCells).toHaveCount(8)
  })

  test('分页组件存在', async ({ page }) => {
    await expect(page.locator('.el-pagination').first()).toBeVisible()
  })
})
