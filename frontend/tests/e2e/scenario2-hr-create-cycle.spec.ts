import { test, expect } from '@playwright/test'

/**
 * E2E 场景 2：HR 创建并启动考核周期
 * 覆盖：登录（张燕子）→ 新增周期 → 选择研发部和产品部员工 → 设置截止时间 → 保存 → 启动考核
 * → 验证仪表盘显示待自评状态 → 验证员工（王志强）收到待自评通知
 */

async function hrLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('hr001')
  await page.getByPlaceholder('密码').fill('Hr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

async function getToken(page, username, password) {
  const res = await page.request.post('/api/v1/auth/login', {
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

    // 设置考核时间（5 号到 25 号，确保不早于今天）
    const dateFormItem = dialog.locator('.el-form-item').filter({ hasText: '考核时间' })
    await dateFormItem.click()
    await page.waitForTimeout(300)
    await page.getByRole('gridcell', { name: '5' }).first().click()
    await page.getByRole('gridcell', { name: '25' }).last().click()
    await page.waitForTimeout(300)

    // 设置截止时间
    await dialog.locator('.el-form-item').filter({ hasText: '自评截止' }).locator('input').first().fill('2026-07-15')
    await dialog.locator('.el-form-item').filter({ hasText: '上级评截止' }).locator('input').first().fill('2026-07-25')
    await dialog.locator('.el-form-item').filter({ hasText: '协作评截止' }).locator('input').first().fill('2026-07-30')
    await page.waitForTimeout(200)

    await dialog.getByRole('button', { name: '确定' }).click()
    await expect(page.getByText('创建成功')).toBeVisible()

    // 刷新页面确认周期已保存
    await page.reload()
    await page.waitForTimeout(500)
    const row = page.locator('table tbody tr').filter({ hasText: cycleName })
    await expect(row).toBeVisible()

    // 通过 API 获取员工列表（研发部和产品部）
    const adminToken = await getToken(page, 'admin', 'admin123')
    const emps = await page.request.get('/api/v1/employees?page=1&size=100', {
      headers: { Authorization: `Bearer ${adminToken}` }
    }).then(r => r.json()).then(j => j.items || [])

    // 筛选研发部和产品部的员工（王志强 EMP001 在研发部）
    const targetEmps = emps.filter(e => e.department_name === '研发部' || e.department_name === '产品部')
    const empIds = targetEmps.slice(0, 2).map(e => e.id)

    // 启动考核
    const cycleRow = page.locator('table tbody tr').filter({ hasText: cycleName })
    await cycleRow.locator('button').filter({ hasText: '启动' }).click()
    await page.waitForTimeout(3000)

    const launchDialog = page.locator('.el-dialog').filter({ hasText: '发起考核' })
    await expect(launchDialog).toBeVisible({ timeout: 10000 })
    await expect(launchDialog.locator('.el-transfer')).toBeVisible()

    // 选择员工
    if (empIds.length > 0) {
      const transferItems = await launchDialog.locator('.el-transfer-panel').first().locator('.el-transfer-panel__item').all()
      for (const item of transferItems) {
        const label = await item.textContent()
        if (label && (label.includes('王志强') || label.includes('陈志强') || label.includes('赵晓峰'))) {
          await item.click()
          await page.waitForTimeout(200)
        }
      }
      await launchDialog.locator('.el-transfer__button').last().click()
      await page.waitForTimeout(200)
    }

    await launchDialog.getByRole('button', { name: '确定发起' }).click()
    await expect(page.getByText('发起成功')).toBeVisible()

    // 验证状态变为自评中
    await page.reload()
    await page.waitForTimeout(500)
    const updatedRow = page.locator('table tbody tr').filter({ hasText: cycleName })
    await expect(updatedRow.locator('td').nth(8)).toContainText('自评中')

    // 验证仪表盘显示待自评状态
    await page.goto('/dashboard')
    await page.waitForTimeout(500)
    await expect(page.getByText('自评中').first()).toBeVisible()
    await expect(page.getByText(cycleName).first()).toBeVisible()

    // 验证员工（王志强）收到待自评通知
    const empToken = await getToken(page, 'emp001', 'Emp001@123')
    const notifs = await page.request.get('/api/v1/notifications?page=1&size=10', {
      headers: { Authorization: `Bearer ${empToken}` }
    }).then(r => r.json()).then(j => Array.isArray(j) ? j : (j.items || []))
    const hasCycleNotif = notifs.some(n => n.content.includes('自评'))
    expect(hasCycleNotif).toBe(true)
  })
})
