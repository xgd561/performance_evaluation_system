import { test, expect } from '@playwright/test'

/**
 * Peer（跨部门协作人）端到端场景测试
 * 覆盖：协作人仪表盘、协作评分待办列表
 */

async function peerLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('peer001')
  await page.getByPlaceholder('密码').fill('Peer001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

test.describe('Peer 场景', () => {
  test('登录后仪表盘显示协作人专属统计与快捷操作', async ({ page }) => {
    await peerLogin(page)

    await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()

    // 协作人专属统计卡片
    await expect(page.locator('.stat-label').filter({ hasText: '待协作评分' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '已完成评分' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '总协作评分' })).toBeVisible()

    // 快捷操作入口
    await expect(page.getByRole('button', { name: '进入协作评分' })).toBeVisible()
  })

  test('可进入协作评分待办页面', async ({ page }) => {
    await peerLogin(page)

    await page.goto('/peer-review')
    await expect(page).toHaveURL(/.*\/peer-review/)
    // 断言页面存在评分卡片或空状态提示
    const reviewCard = page.locator('.review-card').first()
    const emptyTip = page.locator('.el-empty').first()
    await expect(reviewCard.or(emptyTip)).toBeVisible()
  })
})
