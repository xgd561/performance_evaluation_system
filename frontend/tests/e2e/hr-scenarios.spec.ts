import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'

/**
 * HR（绩效专员）端到端场景测试
 * 覆盖：仪表盘、考核周期、申诉处理、汇总计算、强制分布、员工导入、报表导出
 */

// --- Auth helpers ---
async function getToken(page, username, password) {
  const res = await page.request.post('/api/auth/login', {
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
  const res = await page.request.post('/api/assessment-cycles', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({
      name,
      type: 'monthly',
      start_date: '2025-01-01',
      end_date: '2025-01-31',
      weights: { self: 30, manager: 50, peer: 20 },
      grade_rules: { A: 90, B: 80, C: 60, D: 0 }
    })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Create cycle failed: ${JSON.stringify(body)}`)
  return body
}

async function createCycleWithRatioLimitsViaApi(page, token, name) {
  const res = await page.request.post('/api/assessment-cycles', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({
      name,
      type: 'monthly',
      start_date: '2025-01-01',
      end_date: '2025-01-31',
      weights: { self: 30, manager: 50, peer: 20 },
      grade_rules: {
        A: { min: 90, max: 100, ratio_limit: 0.0 },
        B: { min: 80, max: 89.9, ratio_limit: 1.0 },
        C: { min: 60, max: 79.9, ratio_limit: 1.0 },
        D: { min: 0, max: 59.9, ratio_limit: 1.0 }
      },
      small_dept_exemption: false
    })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Create cycle failed: ${JSON.stringify(body)}`)
  return body
}

async function launchCycleViaApi(page, token, cycleId, employeeIds) {
  const res = await page.request.post('/api/assessment-cycles/launch', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ cycle_id: cycleId, employee_ids: employeeIds })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Launch cycle failed: ${JSON.stringify(body)}`)
  return body
}

async function getEmployeesViaApi(page, token) {
  const res = await page.request.get('/api/employees?page=1&size=100', {
    headers: { Authorization: `Bearer ${token}` }
  })
  const json = await res.json()
  return json.items || []
}

async function getScoreSummaryViaApi(page, token, cycleId) {
  const res = await page.request.get(`/api/scores/summary/${cycleId}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

async function submitSelfScoreViaApi(page, token, recordId, scores) {
  const res = await page.request.post(`/api/scores/self/${recordId}`, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify(scores)
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Submit self score failed: ${JSON.stringify(body)}`)
  return body
}

async function submitManagerScoreViaApi(page, token, recordId, scores) {
  const res = await page.request.post(`/api/scores/manager/${recordId}`, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ ...scores, comment: 'This is a test comment with more than 20 characters required.' })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Submit manager score failed: ${JSON.stringify(body)}`)
  return body
}

async function submitPeerScoreViaApi(page, token, recordId, ability) {
  const res = await page.request.post(`/api/scores/peer/${recordId}`, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ ability })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Submit peer score failed: ${JSON.stringify(body)}`)
  return body
}

async function assignPeerReviewerViaApi(page, token, cycleId, employeeId, peerId) {
  const res = await page.request.post('/api/peer-reviewers', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ cycle_id: cycleId, employee_id: employeeId, peer_id: peerId })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Assign peer reviewer failed: ${JSON.stringify(body)}`)
  return body
}

async function calculateScoresViaApi(page, token, cycleId) {
  const res = await page.request.post(`/api/scores/calculate/${cycleId}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Calculate scores failed: ${JSON.stringify(body)}`)
  return body
}

async function advanceToInterviewViaApi(page, token, cycleId) {
  const res = await page.request.post(`/api/assessment-cycles/${cycleId}/advance-to-interview`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Advance to interview failed: ${JSON.stringify(body)}`)
  return body
}

async function submitInterviewViaApi(page, token, recordId) {
  const res = await page.request.post(`/api/assessment-records/${recordId}/interview`, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({
      interview_time: new Date(Date.now() - 3600_000).toISOString(),
      location: '会议室',
      content: '本次面谈已就本期绩效结果与下期改进方向达成一致，员工认可评分结果并确认后续行动计划。'
    })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Submit interview failed: ${JSON.stringify(body)}`)
  return body
}

async function createAppealViaApi(page, token, recordId, reason) {
  const res = await page.request.post('/api/appeals', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ record_id: recordId, reason, detail: 'Test detail for appeal.' })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Create appeal failed: ${JSON.stringify(body)}`)
  return body
}

async function requestDistributionOverrideViaApi(page, token, recordId, reason) {
  const res = await page.request.post(`/api/approvals/${recordId}/distribution-override?reason=${encodeURIComponent(reason)}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Request distribution override failed: ${JSON.stringify(body)}`)
  return body
}

// --- Frontend login helpers ---
async function hrLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('hr001')
  await page.getByPlaceholder('密码').fill('Hr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

// --- Existing simple tests ---
test.describe('HR 场景', () => {
  test('登录后仪表盘显示全局统计', async ({ page }) => {
    await hrLogin(page)

    await expect(page.getByRole('heading', { name: 'HR 专员工作台' })).toBeVisible()

    await expect(page.locator('.stat-label').filter({ hasText: '当前周期' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待汇总' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待审批' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待处理申诉' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '强制分布超标' })).toBeVisible()

    await expect(page.getByText('批量评分')).not.toBeVisible()
    await expect(page.getByText('进入自评')).not.toBeVisible()
    await expect(page.getByText('进入协作评分')).not.toBeVisible()
  })

  test('可进入考核周期管理页面', async ({ page }) => {
    await hrLogin(page)

    await page.goto('/cycles')
    await expect(page).toHaveURL(/.*\/cycles/)
    await expect(page.locator('table').first().or(page.getByText('暂无'))).toBeVisible()
  })

  test('可进入强制分布处理页面', async ({ page }) => {
    await hrLogin(page)

    await page.goto('/distribution-review')
    await expect(page).toHaveURL(/.*\/distribution-review/)
    await expect(page.getByRole('heading', { name: '强制分布处理' })).toBeVisible()

    // 查询表单（周期选择器）应可见
    await expect(page.locator('.search-form').first()).toBeVisible()
  })

  test('可进入报表导出页面', async ({ page }) => {
    await hrLogin(page)

    await page.goto('/reports')
    await expect(page).toHaveURL(/.*\/reports/)
    await expect(page.getByRole('heading', { name: '报表导出' })).toBeVisible()
    await expect(page.locator('.search-form').first()).toBeVisible()
  })

  test('可进入操作日志审计页面', async ({ page }) => {
    await hrLogin(page)

    await page.goto('/audit-logs')
    await expect(page).toHaveURL(/.*\/audit-logs/)
    await expect(page.locator('table').first().or(page.getByText('暂无'))).toBeVisible()
  })

  test('查看申诉列表', async ({ page }) => {
    await hrLogin(page)
    await page.goto('/appeals')
    await expect(page).toHaveURL(/.*\/appeals/)
    await expect(page.getByRole('heading', { name: '申诉管理' })).toBeVisible()
    await expect(page.locator('.search-form').first()).toBeVisible()
    await expect(page.locator('table').first().or(page.getByText('暂无'))).toBeVisible()
  })

  test('查看绩效汇总', async ({ page }) => {
    await hrLogin(page)
    await page.goto('/summary')
    await expect(page).toHaveURL(/.*\/summary/)
    await expect(page.getByRole('heading', { name: '绩效汇总' })).toBeVisible()
    await expect(page.locator('.search-form').first()).toBeVisible()
  })

  // --- Data-dependent core tests ---
  test.describe.serial('HR 核心操作流', () => {
    test('发起考核', async ({ page }) => {
      page.on('console', msg => {
        if (msg.type() === 'error') console.log('PAGE ERROR:', msg.text())
      })
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `HR-发起考核-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)

      await hrLogin(page)
      await page.goto('/cycles')
      await expect(page).toHaveURL(/.*\/cycles/)

      // Find the cycle and click 发起
      const row = page.locator('table tbody tr').filter({ hasText: cycle.name })
      await expect(row).toBeVisible()
      await row.locator('button').filter({ hasText: '发起' }).click()
      await page.waitForTimeout(3000)

      // Launch dialog
      const launchDialog = page.locator('.el-dialog').filter({ hasText: '发起考核' })
      await expect(launchDialog).toBeVisible({ timeout: 10000 })
      await expect(launchDialog.locator('.el-transfer')).toBeVisible()

      // Select first employee in transfer
      await launchDialog.locator('.el-transfer-panel').first().locator('.el-transfer-panel__item').first().click()
      await page.waitForTimeout(200)
      await launchDialog.locator('.el-transfer__button').last().click()
      await page.waitForTimeout(200)

      // Click 确定发起
      await launchDialog.getByRole('button', { name: '确定发起' }).click()

      // Assert success
      await expect(page.getByText('发起成功')).toBeVisible()

      // Assert status changed to 自评中
      await page.reload()
      await page.waitForTimeout(500)
      const updatedRow = page.locator('table tbody tr').filter({ hasText: cycle.name })
      await expect(updatedRow.locator('td').nth(7)).toContainText('自评中')
    })

    test('触发汇总计算', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `HR-汇总-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      const mgr = employees.find(e => e.employee_no === 'MGR001')
      const peer = employees.find(e => e.employee_no === 'PEER001')
      if (!employee4 || !mgr || !peer) throw new Error('Required employees not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')

      // Launch cycle with employee 4 (HR职责)
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      // Get assessment record
      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Assessment record not found')

      // Submit self score as employee
      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      await submitSelfScoreViaApi(page, empToken, record.record_id, {
        performance: 85, ability: 80, attitude: 90
      })

      // Submit manager score as mgr001
      const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
      await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
        performance: 88, ability: 82, attitude: 85
      })

      // Assign peer reviewer and submit peer score (HR职责)
      await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee4.id, peer.id)
      const peerToken = await getToken(page, 'peer001', 'Peer001@123')
      await submitPeerScoreViaApi(page, peerToken, record.record_id, 78)

      // Now HR calculates via frontend
      await hrLogin(page)
      await page.goto('/summary')
      await expect(page).toHaveURL(/.*\/summary/)

      // Select cycle
      await page.locator('.el-select').first().click()
      await page.getByRole('option', { name: cycle.name }).click()

      // Click 触发汇总计算
      await page.getByRole('button', { name: '触发汇总计算' }).click()

      // Confirm dialog
      await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()

      // Assert success
      await expect(page.getByText('汇总计算完成')).toBeVisible()

      // Assert table shows calculated data with status 汇总中
      await expect(page.locator('table tbody tr').first()).toBeVisible()
      const row = page.locator('table tbody tr').first()
      await expect(row.locator('td').nth(9)).toContainText('汇总中') // status
    })

    test('通过申诉', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `HR-申诉通过-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      if (!employee4) throw new Error('Employee 4 not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')

      // Launch cycle with employee 4 (HR职责)
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      // Get the assessment record
      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Assessment record not found')

      // Create appeal as employee (员工职责)
      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      const appeal = await createAppealViaApi(page, empToken, record.record_id, '申诉通过测试理由')

      // Now HR reviews it
      await hrLogin(page)
      await page.goto('/appeals')
      await expect(page).toHaveURL(/.*\/appeals/)

      // Find the appeal and click 通过
      const row = page.locator('table tbody tr').filter({ hasText: '申诉通过测试理由' })
      await row.getByRole('button', { name: '通过' }).first().click()

      // Review dialog
      const reviewDialog = page.locator('.el-dialog').filter({ hasText: '通过申诉' })
      await expect(reviewDialog).toBeVisible()
      await reviewDialog.locator('textarea').fill('经复核，申诉理由成立，维持原结果。')
      await reviewDialog.getByRole('button', { name: '确定' }).click()

      // Assert success
      await expect(page.getByText('已通过申诉')).toBeVisible()
      await page.waitForTimeout(500)

      // Assert status changed to 已通过
      const updatedRow = page.locator('table tbody tr').filter({ hasText: '申诉通过测试理由' })
      await expect(updatedRow.locator('td').nth(4)).toContainText('已通过')
    })

    test('驳回申诉', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `HR-申诉驳回-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      if (!employee4) throw new Error('Employee 4 not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')

      // Launch cycle with employee 4 (HR职责)
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      // Get the assessment record
      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Assessment record not found')

      // Create appeal as employee (员工职责)
      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      await createAppealViaApi(page, empToken, record.record_id, '申诉驳回测试理由')

      // Now HR reviews it
      await hrLogin(page)
      await page.goto('/appeals')
      await expect(page).toHaveURL(/.*\/appeals/)

      // Find the appeal and click 驳回
      const row = page.locator('table tbody tr').filter({ hasText: '申诉驳回测试理由' })
      await row.getByRole('button', { name: '驳回' }).first().click()

      // Review dialog
      const reviewDialog = page.locator('.el-dialog').filter({ hasText: '驳回申诉' })
      await expect(reviewDialog).toBeVisible()
      await reviewDialog.locator('textarea').fill('经复核，申诉理由不成立，维持原结果。')
      await reviewDialog.getByRole('button', { name: '确定' }).click()

      // Assert success
      await expect(page.getByText('已驳回申诉')).toBeVisible()
      await page.waitForTimeout(500)

      // Assert status changed to 已驳回
      const updatedRow = page.locator('table tbody tr').filter({ hasText: '申诉驳回测试理由' })
      await expect(updatedRow.locator('td').nth(4)).toContainText('已驳回')
    })

    test('批量特批通过', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      // Create cycle with A ratio_limit = 0.0 to force downgrade
      const cycle = await createCycleWithRatioLimitsViaApi(page, adminToken, `HR-特批通过-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      const mgr = employees.find(e => e.employee_no === 'MGR001')
      const peer = employees.find(e => e.employee_no === 'PEER001')
      if (!employee4 || !mgr || !peer) throw new Error('Required employees not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')

      // Launch cycle with employee 4 (HR职责)
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      // Get assessment record
      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Assessment record not found')

      // Submit high scores to get A grade
      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      await submitSelfScoreViaApi(page, empToken, record.record_id, {
        performance: 95, ability: 95, attitude: 95
      })

      const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
      await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
        performance: 95, ability: 95, attitude: 95
      })

      // Assign peer reviewer (HR职责)
      await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee4.id, peer.id)
      const peerToken = await getToken(page, 'peer001', 'Peer001@123')
      await submitPeerScoreViaApi(page, peerToken, record.record_id, 95)

      // Calculate scores — this will downgrade A to B because A cap = 0 (HR职责)
      await calculateScoresViaApi(page, hrToken, cycle.id)

      // Debug: check record after calculation
      const postCalcSummary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const postCalcRecord = postCalcSummary.find(r => r.employee_id === employee4.id)
      console.log('[DEBUG] post-calc record:', JSON.stringify(postCalcRecord))

      // Request distribution override as manager
      const overrideReason = `员工表现优异，应获得A等级-${Date.now()}`
      await requestDistributionOverrideViaApi(page, mgrToken, record.record_id, overrideReason)

      // HR approves via frontend
      await hrLogin(page)
      await page.goto('/distribution-review')
      await expect(page).toHaveURL(/.*\/distribution-review/)

      // Select any cycle and click 查询 to load overrides
      await page.locator('.el-select').first().click()
      await page.getByRole('option').first().click()
      await page.getByRole('button', { name: '查询' }).click()
      await page.waitForTimeout(500)

      // Find the override candidate and click 特批（限定在"特批候选人"表格内）
      const overrideTable = page.locator('.el-card').filter({ hasText: '特批候选人' }).locator('table tbody')
      const overrideRow = overrideTable.locator('tr').filter({ hasText: String(record.record_id) }).first()
      await expect(overrideRow).toBeVisible()
      await overrideRow.locator('button:has-text("特批")').first().click()

      // Confirm message box
      await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()

      // Assert success
      await expect(page.getByText('特批已通过')).toBeVisible()
    })

    test('批量特批驳回', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleWithRatioLimitsViaApi(page, adminToken, `HR-特批驳回-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      const mgr = employees.find(e => e.employee_no === 'MGR001')
      const peer = employees.find(e => e.employee_no === 'PEER001')
      if (!employee4 || !mgr || !peer) throw new Error('Required employees not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')

      // Launch cycle with employee 4 (HR职责)
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      // Get assessment record
      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Assessment record not found')

      // Submit high scores
      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      await submitSelfScoreViaApi(page, empToken, record.record_id, {
        performance: 95, ability: 95, attitude: 95
      })

      const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
      await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
        performance: 95, ability: 95, attitude: 95
      })

      // Assign peer reviewer (HR职责)
      await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee4.id, peer.id)
      const peerToken = await getToken(page, 'peer001', 'Peer001@123')
      await submitPeerScoreViaApi(page, peerToken, record.record_id, 95)

      // Calculate scores (HR职责)
      await calculateScoresViaApi(page, hrToken, cycle.id)

      // Request distribution override as manager
      const overrideReason = `特批驳回测试原因-${Date.now()}`
      await requestDistributionOverrideViaApi(page, mgrToken, record.record_id, overrideReason)

      // HR rejects via frontend
      await hrLogin(page)
      await page.goto('/distribution-review')
      await expect(page).toHaveURL(/.*\/distribution-review/)

      // Select any cycle and click 查询
      await page.locator('.el-select').first().click()
      await page.getByRole('option').first().click()
      await page.getByRole('button', { name: '查询' }).click()
      await page.waitForTimeout(500)

      // Find the override candidate and click 驳回（限定在"特批候选人"表格内）
      const overrideTable = page.locator('.el-card').filter({ hasText: '特批候选人' }).locator('table tbody')
      const overrideRow = overrideTable.locator('tr').filter({ hasText: String(record.record_id) }).first()
      await expect(overrideRow).toBeVisible()
      await overrideRow.locator('button:has-text("驳回")').first().click()

      // Confirm message box
      await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()

      // Assert success
      await expect(page.getByText('已驳回')).toBeVisible()
    })

    test('Excel批量导入员工', async ({ page }) => {
      const hrToken = await getToken(page, 'hr001', 'Hr001@123')

      // Download sample template from backend (HR职责，员工管理HR可访问)
      const templateRes = await page.request.get('/api/employees/template?type=sample', {
        headers: { Authorization: `Bearer ${hrToken}` }
      })
      const buffer = await templateRes.body()
      const tmpPath = path.join(os.tmpdir(), `test_import_${Date.now()}.xlsx`)
      fs.writeFileSync(tmpPath, buffer)

      await hrLogin(page)
      await page.goto('/employees')
      await expect(page).toHaveURL(/.*\/employees/)

      // Click import button
      await page.getByRole('button', { name: '导入员工' }).click()

      // Import dialog
      const importDialog = page.locator('.el-dialog').filter({ hasText: '导入员工' })
      await expect(importDialog).toBeVisible()

      // Upload file using file chooser
      const [fileChooser] = await Promise.all([
        page.waitForEvent('filechooser'),
        importDialog.getByRole('button', { name: '选择Excel文件' }).first().click(),
      ])
      await fileChooser.setFiles(tmpPath)
      await page.waitForTimeout(300)

      // Click 导入
      await importDialog.getByRole('button', { name: '导入' }).click()

      // Assert success message
      await expect(page.getByText('导入成功')).toBeVisible()

      // Cleanup temp file
      try { fs.unlinkSync(tmpPath) } catch (_) { /* ignore */ }
    })
  })

  test.describe.serial('HR P1 覆盖度补充', () => {
    test('考核周期 CRUD', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `P1-CRUD-${Date.now()}`)

      await hrLogin(page)
      await page.goto('/cycles')

      // 1. 编辑周期
      const row = page.locator('table tbody tr').filter({ hasText: cycle.name })
      await row.getByRole('button', { name: '编辑' }).click()
      const editDialog = page.locator('.el-dialog').filter({ hasText: '编辑周期' })
      await expect(editDialog).toBeVisible()
      const newName = `${cycle.name}-edited`
      await editDialog.locator('input').first().fill(newName)
      await editDialog.getByRole('button', { name: '确定' }).click()
      await expect(page.getByText('更新成功')).toBeVisible()
      await expect(page.locator('table tbody tr').filter({ hasText: newName })).toBeVisible()

      // 2. 删除周期
      const editedRow = page.locator('table tbody tr').filter({ hasText: newName })
      await editedRow.getByRole('button', { name: '删除' }).click()
      await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
      await expect(page.getByText('删除成功')).toBeVisible()
      await expect(page.locator('table tbody tr').filter({ hasText: newName })).toHaveCount(0)
    })

    test('考核进度查看', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `P1-进度-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      if (!employee4) throw new Error('Employee 4 not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      await hrLogin(page)
      await page.goto('/cycles')

      const row = page.locator('table tbody tr').filter({ hasText: cycle.name })
      await row.getByRole('button', { name: '进度' }).click()

      const progressDialog = page.locator('.el-dialog').filter({ hasText: '考核进度' })
      await expect(progressDialog).toBeVisible({ timeout: 10000 })
      await expect(progressDialog.locator('.el-progress')).toBeVisible()
      await expect(progressDialog.locator('.el-timeline')).toBeVisible()
      await expect(progressDialog.locator('text=总员工')).toBeVisible()
    })

    test('申诉详情与筛选', async ({ page }) => {
      test.setTimeout(45000)
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `P1-申诉筛选-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      if (!employee4) throw new Error('Employee 4 not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Record not found')

      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      const ts = Date.now()
      await createAppealViaApi(page, empToken, record.record_id, `详情测试申诉1-${ts}`)
      await createAppealViaApi(page, empToken, record.record_id, `详情测试申诉2-${ts}`)

      await hrLogin(page)
      await page.goto('/appeals')

      // 1. 查看详情
      const row1 = page.locator('table tbody tr').filter({ hasText: `详情测试申诉1-${ts}` }).first()
      await row1.getByRole('button', { name: '查看' }).click()

      const detailDialog = page.locator('.el-dialog').filter({ hasText: '申诉详情' })
      await expect(detailDialog).toBeVisible()
      await expect(detailDialog.locator('text=申诉人')).toBeVisible()
      await expect(detailDialog.locator('text=申诉理由')).toBeVisible()
      await expect(detailDialog.locator('text=考核总分')).toBeVisible()
      await expect(detailDialog.locator('text=考核等级')).toBeVisible()

      // 关闭详情
      await detailDialog.locator('.el-dialog__headerbtn').click()
      await expect(detailDialog).not.toBeVisible()

      // 2. 筛选待处理（默认就是全部，但显式查询）
      await page.locator('.search-form').locator('.el-select').first().click()
      await page.getByRole('option', { name: '待处理' }).click()
      await page.getByRole('button', { name: '查询' }).click()
      await page.waitForTimeout(300)
      await expect(page.locator('table tbody tr').filter({ hasText: `详情测试申诉1-${ts}` })).toBeVisible()
      await expect(page.locator('table tbody tr').filter({ hasText: `详情测试申诉2-${ts}` })).toBeVisible()

      // 3. 通过其中一个，然后筛选已通过
      await row1.getByRole('button', { name: '通过' }).click()
      const reviewDialog = page.locator('.el-dialog').filter({ hasText: '通过申诉' })
      await reviewDialog.locator('textarea').fill('测试通过')
      await reviewDialog.getByRole('button', { name: '确定' }).click()
      await expect(page.getByText('已通过申诉')).toBeVisible()
      await page.waitForTimeout(500)
      await page.goto('/appeals')
      await page.waitForLoadState('networkidle')

      // 筛选已通过
      await page.locator('.search-form').locator('.el-select').first().click()
      await page.getByRole('option', { name: '已通过' }).click()
      await page.getByRole('button', { name: '查询' }).click()
      await page.waitForTimeout(300)
      await expect(page.locator('table tbody tr').filter({ hasText: `详情测试申诉1-${ts}` })).toBeVisible()
      await expect(page.locator('table tbody tr').filter({ hasText: `详情测试申诉2-${ts}` })).not.toBeVisible()
    })

    test('发布考核结果', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `P1-发布-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      const mgr = employees.find(e => e.employee_no === 'MGR001')
      const peer = employees.find(e => e.employee_no === 'PEER001')
      if (!employee4 || !mgr || !peer) throw new Error('Required employees not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Record not found')

      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      await submitSelfScoreViaApi(page, empToken, record.record_id, {
        performance: 85, ability: 80, attitude: 90
      })

      const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
      await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
        performance: 88, ability: 82, attitude: 85
      })

      await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee4.id, peer.id)
      const peerToken = await getToken(page, 'peer001', 'Peer001@123')
      await submitPeerScoreViaApi(page, peerToken, record.record_id, 78)

      await calculateScoresViaApi(page, hrToken, cycle.id)
      await advanceToInterviewViaApi(page, hrToken, cycle.id)
      await submitInterviewViaApi(page, hrToken, record.record_id)

      await hrLogin(page)
      await page.goto('/cycles')

      const row = page.locator('table tbody tr').filter({ hasText: cycle.name })
      await row.getByRole('button', { name: '发布结果' }).click()
      await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
      await expect(page.getByText('发布成功')).toBeVisible()

      await page.reload()
      await page.waitForTimeout(500)
      const updatedRow = page.locator('table tbody tr').filter({ hasText: cycle.name })
      await expect(updatedRow.locator('td').nth(7)).toContainText('已发布')
    })

    test('智能调整预览', async ({ page }) => {
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleWithRatioLimitsViaApi(page, adminToken, `P1-智能调整-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      const mgr = employees.find(e => e.employee_no === 'MGR001')
      const peer = employees.find(e => e.employee_no === 'PEER001')
      if (!employee4 || !mgr || !peer) throw new Error('Required employees not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Record not found')

      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      await submitSelfScoreViaApi(page, empToken, record.record_id, {
        performance: 95, ability: 95, attitude: 95
      })

      const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
      await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
        performance: 95, ability: 95, attitude: 95
      })

      await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee4.id, peer.id)
      const peerToken = await getToken(page, 'peer001', 'Peer001@123')
      await submitPeerScoreViaApi(page, peerToken, record.record_id, 95)

      await calculateScoresViaApi(page, hrToken, cycle.id)

      await hrLogin(page)
      await page.goto('/distribution-review')
      await expect(page).toHaveURL(/.*\/distribution-review/)

      await page.locator('.el-select').first().click()
      await page.getByRole('option', { name: cycle.name }).click()
      await page.getByRole('button', { name: '查询' }).click()
      await page.waitForTimeout(500)

      const adjustmentCard = page.locator('.el-card').filter({ hasText: '智能调整预览' })
      await expect(adjustmentCard).toBeVisible()

      const adjustmentTable = adjustmentCard.locator('table').last()
      await expect(adjustmentTable).toBeVisible()

      const adjRow = adjustmentTable.locator('tbody tr').filter({ hasText: String(record.record_id) })
      await expect(adjRow).toBeVisible()
      await expect(adjRow.locator('td').nth(4)).toContainText('A')
      await expect(adjRow.locator('td').nth(5)).toContainText('B')
    })

    test('新增考核周期', async ({ page }) => {
      test.setTimeout(60000)
      await hrLogin(page)
      await page.goto('/cycles')
      await page.waitForTimeout(500)

      await page.getByRole('button', { name: '新增周期' }).click()
      await page.waitForTimeout(800)
      const dialog = page.locator('.el-dialog').filter({ hasText: '新增周期' })
      await expect(dialog).toBeVisible()

      const cycleName = `HR-P1-周期-${Date.now()}`
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

      await page.reload()
      await page.waitForTimeout(500)
      await expect(page.locator('table tbody tr').filter({ hasText: cycleName })).toBeVisible()
    })

    test('查看等级分布', async ({ page }) => {
      test.setTimeout(60000)
      const adminToken = await getToken(page, 'admin', 'admin123')
      const cycle = await createCycleViaApi(page, adminToken, `P1-分布-${Date.now()}`)
      const employees = await getEmployeesViaApi(page, adminToken)
      const employee4 = employees.find(e => e.employee_no === 'WANG001')
      const mgr = employees.find(e => e.employee_no === 'MGR001')
      const peer = employees.find(e => e.employee_no === 'PEER001')
      if (!employee4 || !mgr || !peer) throw new Error('Required employees not found')

      const hrToken = await getToken(page, 'hr001', 'Hr001@123')
      await launchCycleViaApi(page, hrToken, cycle.id, [employee4.id])

      const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
      const record = summary.find(r => r.employee_id === employee4.id)
      if (!record) throw new Error('Record not found')

      const empToken = await getToken(page, 'emp001', 'Emp001@123')
      await submitSelfScoreViaApi(page, empToken, record.record_id, {
        performance: 85, ability: 80, attitude: 90
      })

      const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
      await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
        performance: 88, ability: 82, attitude: 85
      })

      await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee4.id, peer.id)
      const peerToken = await getToken(page, 'peer001', 'Peer001@123')
      await submitPeerScoreViaApi(page, peerToken, record.record_id, 78)

      await calculateScoresViaApi(page, hrToken, cycle.id)

      await hrLogin(page)
      await page.goto('/summary')
      await expect(page).toHaveURL(/.*\/summary/)

      await page.locator('.el-select').first().click()
      await page.getByRole('option', { name: cycle.name }).click()
      await page.getByRole('button', { name: '查询' }).click()
      await page.waitForTimeout(500)

      await expect(page.getByText('等级分布').first()).toBeVisible()
      await expect(page.getByText('总人数').first()).toBeVisible()
      await expect(page.getByText(/B 等级/).first()).toBeVisible()
    })

    test('员工管理 CRUD', async ({ page }) => {
      test.setTimeout(60000)
      await hrLogin(page)
      await page.goto('/employees')
      await page.waitForTimeout(500)
      await expect(page.locator('table').first()).toBeVisible()

      // 1. 新增员工
      await page.getByRole('button', { name: '新增员工' }).click()
      await page.waitForTimeout(300)
      const addDialog = page.locator('.el-dialog').filter({ hasText: '新增员工' })
      await expect(addDialog).toBeVisible()

      const empNo = `HR-${Date.now()}`
      const empName = `HR测试-${Date.now()}`

      await addDialog.locator('.el-form-item').filter({ hasText: '工号' }).locator('input').first().fill(empNo)
      await addDialog.locator('.el-form-item').filter({ hasText: '姓名' }).locator('input').first().fill(empName)

      await addDialog.locator('.el-form-item').filter({ hasText: '部门' }).locator('.el-select').first().click()
      await page.waitForTimeout(300)
      await page.getByRole('option', { name: '管理部' }).click()

      await addDialog.locator('.el-form-item').filter({ hasText: '岗位' }).locator('.el-select').first().click()
      await page.waitForTimeout(300)
      await page.getByRole('option', { name: '系统管理员' }).click()

      await addDialog.getByRole('button', { name: '确定' }).click()
      await expect(page.getByText('创建成功')).toBeVisible()

      // 2. 编辑员工
      await page.locator('.search-form .el-form-item').filter({ hasText: '关键词' }).locator('input').first().fill(empNo)
      await page.getByRole('button', { name: '查询' }).click()
      await page.waitForTimeout(300)

      const row = page.locator('table tbody tr').filter({ hasText: empNo })
      await row.getByRole('button', { name: '编辑' }).click()
      await page.waitForTimeout(300)
      const editDialog = page.locator('.el-dialog').filter({ hasText: '编辑员工' })
      await expect(editDialog).toBeVisible()

      const newName = `HR编辑-${Date.now()}`
      await editDialog.locator('.el-form-item').filter({ hasText: '姓名' }).locator('input').first().fill(newName)
      await editDialog.getByRole('button', { name: '确定' }).click()
      await expect(page.getByText('更新成功')).toBeVisible()

      // 3. 删除员工
      await page.waitForTimeout(300)
      const updatedRow = page.locator('table tbody tr').filter({ hasText: newName })
      await updatedRow.getByRole('button', { name: '删除' }).click()
      await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
      await expect(page.getByText('删除成功')).toBeVisible()
      await expect(page.locator('table tbody tr').filter({ hasText: newName })).toHaveCount(0)
    })
  })
})