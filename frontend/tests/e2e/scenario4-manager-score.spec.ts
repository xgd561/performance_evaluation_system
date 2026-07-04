import { test, expect } from '@playwright/test'

/**
 * E2E 场景 4：上级评分 + 协作评分
 * 覆盖：经理登录 → 评分列表 → 评分详情 → 填写评分 → 分配协作人 → 提交
 * → 协作人登录 → 协作评分 → 提交 → 验证状态变为 pending_summary
 */

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

async function assignPeerReviewerViaApi(page, token, cycleId, employeeId, peerId) {
  const res = await page.request.post('/api/peer-reviewers', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ cycle_id: cycleId, employee_id: employeeId, peer_id: peerId })
  })
  return await res.json()
}

async function submitSelfScoreViaApi(page, token, recordId, scores) {
  const res = await page.request.post(`/api/scores/self/${recordId}`, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify(scores)
  })
  return await res.json()
}

async function getScoreSummaryViaApi(page, token, cycleId) {
  const res = await page.request.get(`/api/scores/summary/${cycleId}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

test.describe('场景 4 — 上级评分 + 协作评分', () => {
  test('经理评分后协作人完成评分', async ({ page }) => {
    test.setTimeout(120000)
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `场景4-${Date.now()}`)
    const emps = await page.request.get('/api/employees?page=1&size=100', {
      headers: { Authorization: `Bearer ${adminToken}` }
    }).then(r => r.json()).then(j => j.items || [])
    const emp = emps.find(e => e.employee_no === 'WANG001')
    const mgr = emps.find(e => e.employee_no === 'MGR001')
    const peer = emps.find(e => e.employee_no === 'PEER001')
    if (!emp || !mgr || !peer) throw new Error('Required employees not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [emp.id])
    await assignPeerReviewerViaApi(page, hrToken, cycle.id, emp.id, peer.id)

    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === emp.id)
    if (!record) throw new Error('Record not found')
    const recordId = record.record_id

    // 员工先自评
    const empToken = await getToken(page, 'emp001', 'Emp001@123')
    await submitSelfScoreViaApi(page, empToken, recordId, { performance: 85, ability: 80, attitude: 90 })

    // 经理评分
    await managerLogin(page)
    await page.goto(`/score-sheet?recordId=${recordId}`)
    await page.waitForLoadState('networkidle')

    await expect(page.locator('.employee-name')).toHaveText('王员工')

    const perfInput = page.locator('.dimension-item').filter({ hasText: '工作业绩' }).locator('.score-input input')
    await perfInput.fill('85')
    const abilityInput = page.locator('.dimension-item').filter({ hasText: '工作能力' }).locator('.score-input input')
    await abilityInput.fill('88')
    const attitudeInput = page.locator('.dimension-item').filter({ hasText: '工作态度' }).locator('.score-input input')
    await attitudeInput.fill('90')

    await page.locator('.comment-section').waitFor({ state: 'visible', timeout: 5000 })
    await page.getByPlaceholder('请填写综合评语（不少于20字）').fill('该员工在本考核周期表现良好，工作积极主动，能够按时完成任务，团队协作能力强。')

    await page.getByRole('button', { name: '提交评分' }).click()
    await expect(page.getByText('评分提交成功')).toBeVisible()

    // 协作人评分
    await peerLogin(page)
    await page.goto('/peer-review')
    await page.waitForLoadState('networkidle')

    await expect(page.getByText(cycle.name)).toBeVisible()
    await page.locator('.review-card').filter({ hasText: cycle.name }).getByRole('button', { name: '开始评分' }).click()
    await page.waitForURL(/.*\/peer-review\/.+/)
    await expect(page.getByRole('heading', { name: /协作评分/ })).toBeVisible()

    await page.locator('.score-input input').fill('86')
    await page.getByRole('button', { name: '提交评分' }).click()
    await expect(page.getByText('评分提交成功')).toBeVisible()

    // 验证状态变为 pending_summary
    const summary2 = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record2 = summary2.find(r => r.employee_id === emp.id)
    expect(record2.status).toBe('pending_summary')
  })
})
