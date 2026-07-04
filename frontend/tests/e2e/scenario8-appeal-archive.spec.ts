import { test, expect } from '@playwright/test'

/**
 * E2E 场景 8：申诉与归档
 * 覆盖：完成考核 → 发布 → 员工申诉 → HR 通过 → 归档
 */

async function hrLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('hr001')
  await page.getByPlaceholder('密码').fill('Hr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

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

async function getScoreSummaryViaApi(page, token, cycleId) {
  const res = await page.request.get(`/api/scores/summary/${cycleId}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

async function publishCycleViaApi(page, token, cycleId) {
  const res = await page.request.post(`/api/assessment-cycles/${cycleId}/publish`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

async function advanceToInterviewViaApi(page, token, cycleId) {
  const res = await page.request.post(`/api/assessment-cycles/${cycleId}/advance-to-interview`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

test.describe('场景 8 — 申诉与归档', () => {
  test('员工申诉后 HR 通过并归档周期', async ({ page }) => {
    test.setTimeout(120000)
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `场景8-${Date.now()}`)
    const emps = await page.request.get('/api/employees?page=1&size=100', {
      headers: { Authorization: `Bearer ${adminToken}` }
    }).then(r => r.json()).then(j => j.items || [])
    const emp = emps.find(e => e.employee_no === 'WANG001')
    if (!emp) throw new Error('WANG001 not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [emp.id])

    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === emp.id)
    if (!record) throw new Error('Record not found')
    const recordId = record.record_id

    // 员工自评
    const empToken = await getToken(page, 'emp001', 'Emp001@123')
    await page.request.post(`/api/scores/self/${recordId}`, {
      headers: { Authorization: `Bearer ${empToken}`, 'Content-Type': 'application/json' },
      data: JSON.stringify({ performance: 85, ability: 80, attitude: 90 })
    })

    // 经理评分
    const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
    await page.request.post(`/api/scores/manager/${recordId}`, {
      headers: { Authorization: `Bearer ${mgrToken}`, 'Content-Type': 'application/json' },
      data: JSON.stringify({ performance: 88, ability: 82, attitude: 85, comment: 'This is a test comment with more than 20 characters required.' })
    })

    // 汇总 + 发布
    await page.request.post(`/api/scores/calculate/${cycle.id}`, {
      headers: { Authorization: `Bearer ${hrToken}` }
    })
    await advanceToInterviewViaApi(page, adminToken, cycle.id)
    await publishCycleViaApi(page, hrToken, cycle.id)

    // 员工发起申诉
    await employeeLogin(page)
    await page.goto('/appeal')
    await page.waitForLoadState('networkidle')
    await expect(page.getByText('可申诉的考核记录')).toBeVisible()
    await expect(page.getByText(cycle.name)).toBeVisible()
    await page.getByRole('button', { name: '发起申诉' }).first().click()
    await page.locator('.el-select').click()
    await page.getByRole('option', { name: '对评分结果有异议' }).click()
    const appealReason = `对本次考核评分结果有异议，认为评分偏低。${Date.now()}`
    await page.locator('textarea').fill(appealReason)
    await page.getByRole('button', { name: '提交申诉' }).click()
    await expect(page.getByText('申诉提交成功')).toBeVisible()

    // HR 通过申诉
    await hrLogin(page)
    await page.goto('/appeals')
    await expect(page).toHaveURL(/.*\/appeals/)
    const row = page.locator('table tbody tr').filter({ hasText: '对评分结果有异议' }).first()
    await expect(row).toBeVisible()
    await row.getByRole('button', { name: '通过' }).first().click()
    const reviewDialog = page.locator('.el-dialog').filter({ hasText: '通过申诉' })
    await expect(reviewDialog).toBeVisible()
    await reviewDialog.locator('textarea').fill('经复核，申诉理由成立，维持原结果。')
    await reviewDialog.getByRole('button', { name: 'OK' }).click()
    await expect(page.getByText('已通过申诉')).toBeVisible()

    // 归档周期
    await page.goto('/cycles')
    await expect(page).toHaveURL(/.*\/cycles/)
    const cycleRow = page.locator('table tbody tr').filter({ hasText: cycle.name })
    await cycleRow.locator('button').filter({ hasText: '归档' }).click()
    await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
    await expect(page.getByText('归档成功')).toBeVisible()

    await page.reload()
    await page.waitForTimeout(500)
    const updatedRow = page.locator('table tbody tr').filter({ hasText: cycle.name })
    await expect(updatedRow.locator('td').nth(7)).toContainText('已归档')
  })
})
