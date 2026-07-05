
import { test, expect } from '@playwright/test'
import { employeeLogin, hrLogin } from './helpers/approval-helper'

/**
 * E2E: 申诉管理 (AppealView + AppealList + AppealDetail)
 * 覆盖：员工发起申诉、HR 列表/详情/处理（维持/调整）
 */

test.describe('员工申诉发起页', () => {
  test.beforeEach(async ({ page }) => {
    await employeeLogin(page)
  })

  test('申诉页面显示可申诉记录列表', async ({ page }) => {
    await page.goto('/appeal')
    await expect(page.getByRole('heading', { name: '申诉' })).toBeVisible()
    await expect(page.getByText('可申诉的考核记录')).toBeVisible()
  })

  test('发起申诉表单验证（理由少于20字）', async ({ page }) => {
    await page.goto('/appeal')
    await page.getByRole('button', { name: '发起申诉' }).first().click()
    await page.getByPlaceholder('请详细说明申诉原因（不少于20字）').fill('太短')
    await page.getByRole('button', { name: '提交申诉' }).click()
    await expect(page.getByText('详细说明不少于20字')).toBeVisible()
  })
})

test.describe('HR 申诉管理', () => {
  test.beforeEach(async ({ page }) => {
    await hrLogin(page)
  })

  test('申诉列表页展示申诉人、理由、状态', async ({ page }) => {
    await page.goto('/appeals')
    await expect(page.getByRole('heading', { name: '申诉管理' })).toBeVisible()
    await expect(page.getByText('申诉人')).toBeVisible()
    await expect(page.getByText('申诉理由')).toBeVisible()
    await expect(page.getByText('状态')).toBeVisible()
  })

  test('申诉详情页展示评分原始数据和处理区', async ({ page }) => {
    await page.goto('/appeals')
    // 点击第一个"查看"按钮
    await page.getByRole('button', { name: '查看' }).first().click()
    await page.waitForURL('**/appeal-detail**')
    await expect(page.getByRole('heading', { name: '申诉处理' })).toBeVisible()
    await expect(page.getByText('申诉信息')).toBeVisible()
    await expect(page.getByText('评分原始数据')).toBeVisible()
  })

  test('处理详情页可选择维持或调整', async ({ page }) => {
    await page.goto('/appeals')
    // 点击第一个"处理"按钮
    const resolveBtn = page.getByRole('button', { name: '处理' }).first()
    if (await resolveBtn.isVisible().catch(() => false)) {
      await resolveBtn.click()
      await page.waitForURL('**/appeal-detail**')
      await expect(page.getByText('复核处理')).toBeVisible()
      await expect(page.getByText('维持原结果')).toBeVisible()
      await expect(page.getByText('调整等级')).toBeVisible()
    }
  })
})
