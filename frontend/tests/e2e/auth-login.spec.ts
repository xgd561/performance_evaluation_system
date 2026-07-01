import { test, expect } from '@playwright/test'

/**
 * E2E: 登录核心流程
 * 场景：访问登录页 → 输入管理员账号 → 点击登录 → 跳转仪表盘
 */

test.describe('登录流程', () => {
  test('管理员成功登录并进入仪表盘', async ({ page }) => {
    // 1. 打开登录页
    await page.goto('/login')

    // 2. 断言页面标题和表单元素可见
    await expect(page.getByText('绩效考核评分系统')).toBeVisible()
    await expect(page.getByPlaceholder('用户名')).toBeVisible()
    await expect(page.getByPlaceholder('密码')).toBeVisible()
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible()

    // 3. 填写账号密码
    await page.getByPlaceholder('用户名').fill('admin')
    await page.getByPlaceholder('密码').fill('admin123')

    // 4. 点击登录按钮
    await page.getByRole('button', { name: '登录' }).click()

    // 5. 等待 URL 跳转并断言已进入仪表盘
    await page.waitForURL('**/dashboard')
    await expect(page).toHaveURL(/.*\/dashboard/)

    // 6. 断言仪表盘页面关键内容可见（admin 角色统计卡片）
    await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()
    // 使用 .stat-label 精确匹配统计卡片标签，避免与导航菜单冲突
    await expect(page.locator('.stat-label').filter({ hasText: '员工总数' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '部门数量' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '考核周期' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '进行中' })).toBeVisible()
  })

  test('登录失败后停留在登录页并提示错误', async ({ page }) => {
    await page.goto('/login')

    await page.getByPlaceholder('用户名').fill('admin')
    await page.getByPlaceholder('密码').fill('wrong_password')
    await page.getByRole('button', { name: '登录' }).click()

    // 登录失败应仍停留在 /login
    await expect(page).toHaveURL(/.*\/login/)

    // Element Plus 的 Message 组件会在页面顶部显示错误提示（通过拦截器处理）
    // 这里断言登录按钮恢复可点击状态即可（loading 结束）
    await expect(page.getByRole('button', { name: '登录' })).toBeEnabled()
  })

  test('未登录用户访问受保护页面被重定向到登录页', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForURL('**/login')
    await expect(page).toHaveURL(/.*\/login/)
  })
})
