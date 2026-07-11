import { test, expect } from '@playwright/test'

async function employeeLogin(page: any) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('emp001')
  await page.getByPlaceholder('密码').fill('Emp001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

/**
 * 员工仪表盘 E2E 测试
 */
test.describe('员工仪表盘', () => {
  test('应显示统计卡片', async ({ page }) => {
    await employeeLogin(page)
    await expect(page.getByText('我的绩效首页')).toBeVisible()

    await expect(page.locator('.stat-label').filter({ hasText: '当前状态' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待自评' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '历史考核' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '申诉记录' })).toBeVisible()
  })

  test('应显示最近考核周期表格', async ({ page }) => {
    await employeeLogin(page)
    await expect(page.getByText('最近考核周期')).toBeVisible()
    await expect(page.locator('.custom-table')).toBeVisible()
  })

  test('快捷操作应显示员工常用操作', async ({ page }) => {
    await employeeLogin(page)
    await expect(page.getByText('快捷操作')).toBeVisible()
    await expect(page.getByRole('button', { name: '进入自评' })).toBeVisible()
    await expect(page.getByRole('button', { name: '查看历史' })).toBeVisible()
    await expect(page.getByRole('button', { name: '发起申诉' })).toBeVisible()
  })
})
