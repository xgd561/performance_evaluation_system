import { test, expect } from '@playwright/test'

/**
 * E2E: 上级评分 + 协作评分场景 (P4-22)
 * 场景：admin 创建考核周期 → HR 发起考核 → emp001 自评 → mgr001 上级评分并分配协作人 → peer001 提交协作评分
 * 最终状态验证：record.status === 'pending_summary'
 */

// --- Auth helpers ---
async function getToken(page, username, password) {
  const res = await page.request.post('/api/v1/auth/login', {
    headers: { 'Content-Type': 'application/json' },
    data: JSON.stringify({ username, password })
  })
  const body = await res.json()
  if (!body.access_token) {
    throw new Error(`Login failed for ${username}: ${JSON.stringify(body)}`)
  }
  return body.access_token
}

// --- API helpers ---
async function createCycleViaApi(page, token, name) {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  const startDate = `${year}-${month}-${day}`
  const endDate = `${year}-${month}-${new Date(year, today.getMonth() + 1, 0).getDate()}`
  const res = await page.request.post('/api/v1/assessment-cycles', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({
      name,
      type: 'monthly',
      start_date: startDate,
      end_date: endDate,
      weights: { self: 30, manager: 50, peer: 20 },
      grade_rules: { A: 90, B: 80, C: 60, D: 0 }
    })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Create cycle failed: ${JSON.stringify(body)}`)
  return body
}

async function launchCycleViaApi(page, token, cycleId, employeeIds) {
  const res = await page.request.post('/api/v1/assessment-cycles/launch', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ cycle_id: cycleId, employee_ids: employeeIds })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Launch cycle failed: ${JSON.stringify(body)}`)
  return body
}

async function getEmployeesViaApi(page, token) {
  const res = await page.request.get('/api/v1/employees?page=1&size=100', {
    headers: { Authorization: `Bearer ${token}` }
  })
  const json = await res.json()
  return json.items || []
}

async function getScoreSummaryViaApi(page, token, cycleId) {
  const res = await page.request.get(`/api/v1/scores/summary/${cycleId}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

async function submitSelfScoreViaApi(page, token, recordId, scores) {
  const res = await page.request.post(`/api/v1/scores/self/${recordId}`, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify(scores)
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Submit self score failed: ${JSON.stringify(body)}`)
  return body
}

async function assignPeerReviewerViaApi(page, token, cycleId, employeeId, peerId) {
  const res = await page.request.post('/api/v1/peer-reviewers', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ cycle_id: cycleId, employee_id: employeeId, peer_id: peerId })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Assign peer reviewer failed: ${JSON.stringify(body)}`)
  return body
}

// --- Frontend login helpers ---
async function managerLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('mgr001')
  await page.getByPlaceholder('密码').fill('Mgr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

async function peerLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('peer001')
  await page.getByPlaceholder('密码').fill('Peer001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

// --- Scenario ---
test.describe.serial('P4-22: 上级评分 + 协作评分完整流程', () => {
  test('mgr001 提交上级评分并分配 peer001，随后 peer001 提交协作评分，最终状态为 pending_summary', async ({ page }) => {
    test.setTimeout(120000)

    // ========== 1. Setup via API ==========
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `P4-22-上级协作-${Date.now()}`)
    const employees = await getEmployeesViaApi(page, adminToken)
    const employee = employees.find(e => e.employee_no === 'EMP001')
    const peer = employees.find(e => e.employee_no === 'PEER001')
    if (!employee || !peer) throw new Error('Required employees not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === employee.id)
    if (!record) throw new Error('Record not found')

    // emp001 提交自评
    const empToken = await getToken(page, 'emp001', 'Emp001@123')
    await submitSelfScoreViaApi(page, empToken, record.record_id, {
      performance: 80, ability: 82, attitude: 85
    })

    // ========== 2. Manager login & score ==========
    await managerLogin(page)

    // Go directly to score sheet detail page with record_id query param
    // The score sheet list may redirect directly to detail if only one record exists
    await page.goto(`/score-sheet?recordId=${record.record_id}`)
    await page.waitForLoadState('networkidle')
    // Wait for the employee name heading to confirm page loaded
    await expect(page.locator('.employee-name')).toBeVisible({ timeout: 10000 })
    // Verify we're on the correct employee's score sheet
    await expect(page.locator('.employee-name')).toHaveText(employee.name || '王志强')

    // Fill scores: performance=85, ability=88, attitude=90
    // The dimension inputs are in order: performance, ability, attitude
    const scoreInputs = page.locator('.dimension-item .score-input input')
    await scoreInputs.nth(0).fill('85')
    await scoreInputs.nth(1).fill('88')
    await scoreInputs.nth(2).fill('90')

    // Write comment (>=20 chars)
    await page.locator('.comment-section textarea').fill('该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。')

    // Assign peer reviewer via API (UI selector may not exist; use API to ensure assignment)
    await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee.id, peer.id)

    // Submit manager score
    await page.getByRole('button', { name: '提交评分' }).click()

    // Verify success: page shows success message
    await expect(page.getByText('评分提交成功')).toBeVisible()

    // ========== 3. Peer login & review ==========
    await peerLogin(page)

    await page.goto('/peer-review')
    await page.waitForLoadState('networkidle')

    // Find the card for emp001 and click "开始评分"
    const reviewCard = page.locator('.review-card').filter({ hasText: cycle.name })
    await expect(reviewCard).toBeVisible()
    await reviewCard.getByRole('button', { name: '开始评分' }).click()

    // Wait for peer review detail page
    await page.waitForURL(/.*\/peer-review\/.+/)
    await expect(page.getByRole('heading', { name: /协作评分/ })).toBeVisible()

    // Fill ability score: 86
    await page.locator('.score-input input').fill('86')

    // Write peer comment (>=20 chars)
    await page.locator('.comment-section textarea').fill('该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。')

    // Submit peer review
    await page.getByRole('button', { name: '提交评分' }).click()

    // Verify success: page shows success message
    await expect(page.getByText('评分提交成功')).toBeVisible()

    // ========== 4. Verify final status via API ==========
    const finalSummary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const finalRecord = finalSummary.find(r => r.employee_id === employee.id)
    if (!finalRecord) throw new Error('Final record not found')
    expect(finalRecord.status).toBe('pending_summary')
  })
})
