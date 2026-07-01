import { Page } from '@playwright/test'

/**
 * Admin 登录辅助函数
 */
export async function adminLogin(page: Page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('admin')
  await page.getByPlaceholder('密码').fill('admin123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

/**
 * 生成唯一的测试标识（用于工号、名称等，避免冲突）
 */
export function uniqueId() {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1000)}`
}

/**
 * 辅助：选择 Element Plus 的 el-select 下拉选项
 * @param page Page 对象
 * @param label select 前的表单标签文本
 * @param optionText 要选择的选项文本
 */
export async function selectOptionByLabel(page: Page, label: string, optionText: string) {
  // 找到包含 label 的 form-item，点击其中的 select
  const select = page.locator('.el-form-item').filter({ hasText: label }).locator('.el-select').first()
  await select.click()
  // 等待下拉菜单出现
  await page.locator('.el-select-dropdown').last().waitFor({ state: 'visible' })
  // 选择选项
  await page.locator('.el-select-dropdown').last().getByText(optionText).click()
}

/**
 * 辅助：等待 Element Plus 的 Message 提示出现并断言内容
 * @param page Page 对象
 * @param text 提示文本（部分匹配）
 */
export async function expectToast(page: Page, text: string) {
  const toast = page.locator('.el-message').filter({ hasText: text }).first()
  await expect(toast).toBeVisible({ timeout: 5000 })
}

import { expect } from '@playwright/test'
