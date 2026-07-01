import { test, expect } from '@playwright/test'

/**
 * Employee（普通员工）端到端场景测试
 * 覆盖：员工仪表盘、自评、我的绩效
 */

async function employeeLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('emp001')
  await page.getByPlaceholder('密码').fill('Emp001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

test.describe('Employee 场景', () => {
  test('登录后仪表盘显示员工专属统计与快捷操作', async ({ page }) => {
    await employeeLogin(page)

    await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()

    // 员工专属统计卡片
    await expect(page.locator('.stat-label').filter({ hasText: '考核记录' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待自评' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '当前考核' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '当前状态' })).toBeVisible()

    // 快捷操作入口
    await expect(page.getByRole('button', { name: '进入自评' })).toBeVisible()
    await expect(page.getByRole('button', { name: '查看历史绩效' })).toBeVisible()
    await expect(page.getByRole('button', { name: '发起申诉' })).toBeVisible()
  })

  test('可进入自评页面', async ({ page }) => {
    await employeeLogin(page)

    await page.goto('/self-assessment')
    await expect(page).toHaveURL(/.*\/self-assessment/)
    await expect(page.getByRole('heading', { name: '自评' })).toBeVisible()
    await expect(page.getByRole('button', { name: '提交自评' })).toBeVisible()
  })

  test('可进入我的绩效页面', async ({ page }) => {
    await employeeLogin(page)

    await page.goto('/my-performance')
    await expect(page).toHaveURL(/.*\/my-performance/)
    // 页面核心内容：加载状态、状态卡片或历史记录表格至少其一可见
    await expect(page.locator('.status-card, .el-empty, .loading-wrap, table').first()).toBeVisible()
  })

  test('未登录访问员工页面被重定向到登录页', async ({ page }) => {
    await page.goto('/self-assessment')
    await page.waitForURL('**/login')
    await expect(page).toHaveURL(/.*\/login/)
  })
})
