import { test, expect } from '@playwright/test'

/**
 * E2E 场景 2：HR 创建并启动考核周期
 * 覆盖：登录 → 新增周期 → 选择部门 → 设置时间 → 保存 → 启动 → 验证进度
 */

async function hrLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('hr001')
  await page.getByPlaceholder('密码').fill('Hr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

async function getToken(page, username, password) {
  const res = await page.request.post('/api/auth/login', {
    headers: { 'Content-Type': 'application/json' },
    data: JSON.stringify({ username, password })
  })
  const body = await res.json()
  if (!body.access_token) throw new Error(`Login failed for ${username}`)
  return body.access_token
}

test.describe('场景 2 — HR 创建并启动考核周期', () => {
  test('HR 创建周期、设置部门、保存并启动', async ({ page }) => {
    test.setTimeout(60000)
    await hrLogin(page)
    await page.goto('/cycles')
    await page.waitForTimeout(500)

    // 新增周期
    await page.getByRole('button', { name: '新增周期' }).click()
    await page.waitForTimeout(800)
    const dialog = page.locator('.el-dialog').filter({ hasText: '新增周期' })
    await expect(dialog).toBeVisible()

    const cycleName = `场景2-周期-${Date.now()}`
    await dialog.locator('.el-form-item').filter({ hasText: '名称' }).locator('input').first().fill(cycleName)

    await dialog.locator('.el-form-item').filter({ hasText: '类型' }).locator('.el-select').first().click()
    await page.waitForTimeout(300)
    await page.getByRole('option', { name: '月度' }).click()

    const dateFormItem = dialog.locator('.el-form-item').filter({ hasText: '考核时间' })
    await dateFormItem.click()
    await page.waitForTimeout(300)
    await page.getByRole('gridcell', { name: '1' }).first().click()
    await page.getByRole('gridcell', { name: '31' }).last().click()
    await page.waitForTimeout(300)

    await dialog.getByRole('button', { name: '确定' }).click()
    await expect(page.getByText('创建成功')).toBeVisible()

    // 刷新页面确认周期已保存
    await page.reload()
    await page.waitForTimeout(500)
    const row = page.locator('table tbody tr').filter({ hasText: cycleName })
    await expect(row).toBeVisible()

    // 启动考核（需要 API 前置获取员工）
    const adminToken = await getToken(page, 'admin', 'admin123')
    const emps = await page.request.get('/api/employees?page=1&size=100', {
      headers: { Authorization: `Bearer ${adminToken}` }
    }).then(r => r.json()).then(j => j.items || [])
    const empIds = emps.slice(0, 2).map(e => e.id)

    const cycleRow = page.locator('table tbody tr').filter({ hasText: cycleName })
    await cycleRow.locator('button').filter({ hasText: '发起' }).click()
    await page.waitForTimeout(3000)

    const launchDialog = page.locator('.el-dialog').filter({ hasText: '发起考核' })
    await expect(launchDialog).toBeVisible({ timeout: 10000 })
    await expect(launchDialog.locator('.el-transfer')).toBeVisible()

    // 选择员工
    if (empIds.length > 0) {
      await launchDialog.locator('.el-transfer-panel').first().locator('.el-transfer-panel__item').first().click()
      await page.waitForTimeout(200)
      await launchDialog.locator('.el-transfer__button').last().click()
      await page.waitForTimeout(200)
    }

    await launchDialog.getByRole('button', { name: '确定发起' }).click()
    await expect(page.getByText('发起成功')).toBeVisible()

    // 验证状态变为自评中
    await page.reload()
    await page.waitForTimeout(500)
    const updatedRow = page.locator('table tbody tr').filter({ hasText: cycleName })
    await expect(updatedRow.locator('td').nth(7)).toContainText('自评中')
  })
})
