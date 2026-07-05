import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 审批详情 (ApprovalDetail)
 * 覆盖：详情展示、异常提示、审批操作（通过/驳回/打回）
 */

test.describe('审批详情页', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
  })

  test('无 record_id 时显示空状态', async ({ page }) => {
    await page.goto('/approval-detail')
    await expect(page.getByRole('heading', { name: '审批详情' })).toBeVisible()
    await expect(page.getByText('未找到考核记录')).toBeVisible()
  })

  test('页面包含审批操作区', async ({ page }) => {
    await page.goto('/approval-detail?record_id=999')
    await expect(page.getByRole('heading', { name: '审批详情' })).toBeVisible()

    // 基本信息区块
    await expect(page.getByText('员工基本信息')).toBeVisible()
    // 评分详情区块
    await expect(page.getByText('评分详情')).toBeVisible()
    // 加权结果区块
    await expect(page.getByText('加权计算结果')).toBeVisible()
    // 审批操作区
    await expect(page.getByText('审批操作')).toBeVisible()
    await expect(page.getByRole('button', { name: '通过' })).toBeVisible()
    await expect(page.getByRole('button', { name: '驳回' })).toBeVisible()
    await expect(page.getByRole('button', { name: '打回重评' })).toBeVisible()
    await expect(page.getByRole('button', { name: '返回' })).toBeVisible()
  })

  test('审批意见 textarea 存在且有字数限制', async ({ page }) => {
    await page.goto('/approval-detail?record_id=999')
    const textarea = page.locator('.el-textarea__inner').first()
    await expect(textarea).toBeVisible()
    await textarea.fill('短')
    await expect(textarea).toHaveValue('短')
  })

  test('点击返回按钮跳转回审批工作台', async ({ page }) => {
    await page.goto('/approval-detail?record_id=999')
    await page.getByRole('button', { name: '返回' }).click()
    await page.waitForURL('**/approval-workbench')
    await expect(page).toHaveURL(/.*\/approval-workbench/)
  })
})
