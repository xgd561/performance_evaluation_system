import { test, expect } from '@playwright/test'
import { adminLogin, hrLogin, expectToast } from './helpers/admin-helper'

/**
 * E2E: 报表导出页 (ReportExport)
 * 覆盖：表单元素、导出按钮状态、进度条、历史记录表格
 */

test.describe('报表导出页', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
    await page.goto('/reports')
  })

  test('页面标题可见', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '报表导出' })).toBeVisible()
  })

  test('考核周期下拉存在', async ({ page }) => {
    const cycleSelect = page.locator('.el-form-item').filter({ hasText: '考核周期' }).locator('.el-select').first()
    await expect(cycleSelect).toBeVisible()
  })

  test('部门多选下拉存在', async ({ page }) => {
    const deptSelect = page.locator('.el-form-item').filter({ hasText: '部门' }).locator('.el-select').first()
    await expect(deptSelect).toBeVisible()
  })

  test('导出格式单选按钮存在', async ({ page }) => {
    await expect(page.locator('.el-radio-button').filter({ hasText: 'Excel' })).toBeVisible()
    await expect(page.locator('.el-radio-button').filter({ hasText: 'PDF' })).toBeVisible()
  })

  test('未选择周期时导出按钮禁用', async ({ page }) => {
    const exportBtn = page.getByRole('button', { name: '导出' })
    await expect(exportBtn).toBeDisabled()
  })

  test('选择周期后导出按钮启用', async ({ page }) => {
    const cycleSelect = page.locator('.el-form-item').filter({ hasText: '考核周期' }).locator('.el-select').first()
    await cycleSelect.click()
    await page.locator('.el-select-dropdown').last().waitFor({ state: 'visible' })
    await page.locator('.el-select-dropdown').last().locator('.el-select-dropdown__item').first().click()

    const exportBtn = page.getByRole('button', { name: '导出' })
    await expect(exportBtn).toBeEnabled()
  })

  test('点击导出后显示进度条', async ({ page }) => {
    const cycleSelect = page.locator('.el-form-item').filter({ hasText: '考核周期' }).locator('.el-select').first()
    await cycleSelect.click()
    await page.locator('.el-select-dropdown').last().waitFor({ state: 'visible' })
    await page.locator('.el-select-dropdown').last().locator('.el-select-dropdown__item').first().click()

    await page.getByRole('button', { name: '导出' }).click()
    await expect(page.locator('.el-progress')).toBeVisible()
  })

  test('历史导出记录表格存在', async ({ page }) => {
    await expect(page.locator('.el-card').filter({ hasText: '历史导出记录' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '文件名' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '格式' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '导出时间' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '状态' })).toBeVisible()
  })
})

test.describe('报表导出页权限', () => {
  test('HR 可访问报表导出页', async ({ page }) => {
    await hrLogin(page)
    await page.goto('/reports')
    await expect(page.getByRole('heading', { name: '报表导出' })).toBeVisible()
  })
})
