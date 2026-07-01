import { test, expect } from '@playwright/test'

/**
 * Manager（直属上级/部门负责人）端到端场景测试
 * 覆盖：经理仪表盘、评分表、审批工作台、绩效面谈
 */

async function managerLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('mgr001')
  await page.getByPlaceholder('密码').fill('Mgr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

test.describe('Manager 场景', () => {
  test('登录后仪表盘显示经理专属统计与快捷操作', async ({ page }) => {
    await managerLogin(page)

    await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()

    // 经理专属统计卡片
    await expect(page.locator('.stat-label').filter({ hasText: '下属人数' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待评分' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待审批' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待面谈' })).toBeVisible()

    // 快捷操作入口
    await expect(page.getByRole('button', { name: '批量评分' })).toBeVisible()
    await expect(page.getByRole('button', { name: '审批下属绩效' })).toBeVisible()
    await expect(page.getByRole('button', { name: '记录面谈' })).toBeVisible()
  })

  test('可进入评分表页面', async ({ page }) => {
    await managerLogin(page)

    await page.goto('/score-sheet')
    await expect(page).toHaveURL(/.*\/score-sheet/)

    // 断言评分页面包含维度列表或员工选择器（即使无数据，布局元素应存在）
    await expect(page.locator('.score-sheet-layout, .el-select, .dimension-list').first()).toBeVisible()
  })

  test('可进入审批工作台页面', async ({ page }) => {
    await managerLogin(page)

    await page.goto('/approval-workbench')
    await expect(page).toHaveURL(/.*\/approval-workbench/)
    await expect(page.getByRole('heading', { name: '审批工作台' })).toBeVisible()

    // 断言存在审批操作按钮或空状态提示
    const actionBtn = page.locator('button').filter({ hasText: '通过' }).first()
    const emptyTip = page.getByText('暂无').first()
    await expect(actionBtn.or(emptyTip)).toBeVisible()
  })

  test('可进入绩效面谈记录页面', async ({ page }) => {
    await managerLogin(page)

    await page.goto('/interviews')
    await expect(page).toHaveURL(/.*\/interviews/)
    await expect(page.getByRole('heading', { name: '绩效面谈' })).toBeVisible()
    // 页面存在表格或空状态提示（el-table 空数据时两者可能同时存在，取第一个可见元素）
    await expect(page.locator('table, .el-empty').first()).toBeVisible()
  })
})
