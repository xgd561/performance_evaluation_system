import { test, expect } from '@playwright/test'

/**
 * E2E 场景 3：员工自评
 * 覆盖：登录 → 我的绩效 → 去自评 → 填写三维度 → 保存草稿 → 提交 → 验证状态
 */

async function employeeLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('emp001')
  await page.getByPlaceholder('密码').fill('Emp001@123')
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

async function createCycleViaApi(page, token, name) {
  const res = await page.request.post('/api/assessment-cycles', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ name, type: 'monthly', start_date: '2025-01-01', end_date: '2025-01-31', weights: { self: 30, manager: 50, peer: 20 }, grade_rules: { A: 90, B: 80, C: 60, D: 0 } })
  })
  return await res.json()
}

async function launchCycleViaApi(page, token, cycleId, employeeIds) {
  const res = await page.request.post('/api/assessment-cycles/launch', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ cycle_id: cycleId, employee_ids: employeeIds })
  })
  return await res.json()
}

test.describe('场景 3 — 员工自评', () => {
  test('员工填写自评并提交', async ({ page }) => {
    test.setTimeout(60000)
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `场景3-${Date.now()}`)
    const emps = await page.request.get('/api/employees?page=1&size=100', {
      headers: { Authorization: `Bearer ${adminToken}` }
    }).then(r => r.json()).then(j => j.items || [])
    const emp = emps.find(e => e.employee_no === 'WANG001')
    if (!emp) throw new Error('WANG001 not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [emp.id])

    await employeeLogin(page)
    await page.goto('/self-assessment')
    await page.waitForLoadState('networkidle')

    await expect(page.getByText('截止日期')).toBeVisible()

    const inputs = page.locator('.dimension-item .score-input input')
    await expect(inputs).toHaveCount(3)
    await inputs.nth(0).fill('82')
    await inputs.nth(1).fill('84')
    await inputs.nth(2).fill('88')

    // 保存草稿
    const saveBtn = page.getByRole('button', { name: '保存草稿' })
    if (await saveBtn.isVisible().catch(() => false)) {
      await saveBtn.click()
      await expect(page.getByText('草稿已保存')).toBeVisible()
    }

    // 提交自评
    await page.getByRole('button', { name: '提交自评' }).click()
    await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
    await expect(page.getByText('自评提交成功')).toBeVisible()

    // 验证状态变为待上级评
    await expect(page).toHaveURL(/.*\/my-performance/)
    await expect(page.getByText('待上级评').first()).toBeVisible()
  })
})
