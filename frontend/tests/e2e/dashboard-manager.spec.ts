import { test, expect } from '@playwright/test'

async function managerLogin(page: any) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('mgr001')
  await page.getByPlaceholder('密码').fill('Mgr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

/**
 * 经理仪表盘 E2E 测试
 */
test.describe('经理仪表盘', () => {
  test('应显示统计卡片', async ({ page }) => {
    await managerLogin(page)
    await expect(page.getByText('部门经理工作台')).toBeVisible()

    await expect(page.locator('.stat-label').filter({ hasText: '待评分' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待审批' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待面谈' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '下属总数' })).toBeVisible()
  })

  test('应显示最近考核周期表格', async ({ page }) => {
    await managerLogin(page)
    await expect(page.getByText('最近考核周期')).toBeVisible()
    await expect(page.locator('.custom-table')).toBeVisible()
  })

  test('快捷操作应显示经理常用操作', async ({ page }) => {
    await managerLogin(page)
    await expect(page.getByText('快捷操作')).toBeVisible()
    await expect(page.getByRole('button', { name: '批量评分' })).toBeVisible()
    await expect(page.getByRole('button', { name: '审批确认' })).toBeVisible()
    await expect(page.getByRole('button', { name: '绩效面谈' })).toBeVisible()
  })
})
