import { test, expect } from '@playwright/test'

async function hrLogin(page: any) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('hr001')
  await page.getByPlaceholder('密码').fill('Hr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

/**
 * HR 仪表盘 E2E 测试
 * 覆盖：统计卡片、最近考核周期表格、进度条、导航
 */
test.describe('HR 仪表盘', () => {
  test('应显示 5 张统计卡片', async ({ page }) => {
    await hrLogin(page)
    await expect(page.getByText('HR 专员工作台')).toBeVisible()

    const statCards = page.locator('.stat-card')
    await expect(statCards).toHaveCount(5)

    await expect(page.locator('.stat-label').filter({ hasText: '当前周期' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待汇总' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待审批' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待处理申诉' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '强制分布超标' })).toBeVisible()
  })

  test('应显示最近考核周期表格', async ({ page }) => {
    await hrLogin(page)
    await expect(page.getByText('最近考核周期')).toBeVisible()
    await expect(page.locator('table')).toBeVisible()
  })

  test('统计卡片应可点击导航', async ({ page }) => {
    await hrLogin(page)
    await page.locator('.stat-card').filter({ hasText: '待汇总' }).click()
    await page.waitForURL('**/summary')
  })

  test('快捷操作区应显示 HR 常用操作', async ({ page }) => {
    await hrLogin(page)
    await expect(page.getByText('快捷操作')).toBeVisible()
    await expect(page.getByRole('button', { name: '创建考核周期' })).toBeVisible()
    await expect(page.getByRole('button', { name: '汇总处理' })).toBeVisible()
    await expect(page.getByRole('button', { name: '审批工作台' })).toBeVisible()
    await expect(page.getByRole('button', { name: '报表导出' })).toBeVisible()
  })
})
