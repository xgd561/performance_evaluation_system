import { test, expect } from '@playwright/test'

/**
 * Employee（普通员工）端到端场景测试
 * 覆盖：员工仪表盘、自评、我的绩效、发起申诉、保存草稿、考核详情、PDF下载、申诉历史
 *
 * 账号-职责映射：
 * - 提交自评、保存草稿、查看我的绩效、发起申诉、查看申诉历史：emp001（前端操作）
 * - 创建考核周期、发起考核、汇总计算、发布结果：admin/hr（API 前置数据准备）
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

// --- API helpers (前置数据准备，非员工职责范围) ---
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

async function assignPeerReviewerViaApi(page, token, cycleId, employeeId, peerId) {
  const res = await page.request.post('/api/peer-reviewers', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ cycle_id: cycleId, employee_id: employeeId, peer_id: peerId })
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Assign peer reviewer failed: ${JSON.stringify(body)}`)
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

// 面谈是发布前的强制节点：发布前必须先为该记录提交面谈
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

async function publishCycleViaApi(page, token, cycleId) {
  const res = await page.request.post(`/api/assessment-cycles/${cycleId}/publish`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  const body = await res.json()
  if (!res.ok()) throw new Error(`Publish cycle failed: ${JSON.stringify(body)}`)
  return body
}

// --- Frontend login helpers ---
async function employeeLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('emp001')
  await page.getByPlaceholder('密码').fill('Emp001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

// --- Existing simple tests ---
test.describe('Employee 准入性场景', () => {
  test('登录后仪表盘显示员工专属统计与快捷操作', async ({ page }) => {
    await employeeLogin(page)

    await expect(page.getByRole('heading', { name: '我的绩效首页' })).toBeVisible()

    // 员工专属统计卡片
    await expect(page.locator('.stat-label').filter({ hasText: '当前状态' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '待自评' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '历史考核' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '申诉记录' })).toBeVisible()

    // 快捷操作入口
    await expect(page.getByRole('button', { name: '进入自评' })).toBeVisible()
    await expect(page.getByRole('button', { name: '查看历史' })).toBeVisible()
    await expect(page.getByRole('button', { name: '发起申诉' })).toBeVisible()
  })

  test('可进入自评页面', async ({ page }) => {
    await employeeLogin(page)

    await page.goto('/self-assessment')
    await expect(page).toHaveURL(/.*\/self-assessment/)
    await expect(page.getByRole('heading', { name: '自评' })).toBeVisible()
    await expect(page.getByRole('button', { name: '提交自评' })).toBeVisible()
  })

  test('可进入我的绩效页面', async ({ page }) => {
    await employeeLogin(page)

    await page.goto('/my-performance')
    await expect(page).toHaveURL(/.*\/my-performance/)
    // 页面核心内容：加载状态、状态卡片或历史记录表格至少其一可见
    await expect(page.locator('.status-card, .el-empty, .loading-wrap, table').first()).toBeVisible()
  })

  test('未登录访问员工页面被重定向到登录页', async ({ page }) => {
    await page.goto('/self-assessment')
    await page.waitForURL('**/login')
    await expect(page).toHaveURL(/.*\/login/)
  })
})

// --- P0 + P1 核心操作流 ---
test.describe.serial('Employee 核心操作流', () => {
  test('填写并提交自评', async ({ page }) => {
    // 前置：admin 创建周期，HR 发起考核（包含 emp001）
    // 注意：以下 API 调用属于 admin/HR 职责范围，仅作为测试数据前置准备
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `EMP-自评-${Date.now()}`)
    const employees = await getEmployeesViaApi(page, adminToken)
    const employee = employees.find(e => e.employee_no === 'WANG001')
    if (!employee) throw new Error('Employee WANG001 not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

    // 员工操作：emp001 登录并提交自评
    await employeeLogin(page)

    await page.goto('/self-assessment')
    await page.waitForLoadState('networkidle')

    // 断言考核信息已加载
    await expect(page.getByText(cycle.name)).toBeVisible()
    await expect(page.getByText('截止日期')).toBeVisible()

    // 填写三个维度分数
    const inputs = page.locator('.dimension-item .score-input input')
    await expect(inputs).toHaveCount(3)
    await inputs.nth(0).fill('85') // 工作业绩
    await inputs.nth(1).fill('80') // 工作能力
    await inputs.nth(2).fill('90') // 工作态度

    // 点击提交自评
    await page.getByRole('button', { name: '提交自评' }).click()

    // 确认弹窗
    await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()

    // 断言提交成功提示
    await expect(page.getByText('自评提交成功')).toBeVisible()

    // 断言跳转至我的绩效页面
    await expect(page).toHaveURL(/.*\/my-performance/)

    // 断言当前考核状态变为"待上级评"
    await expect(page.getByText('待上级评').first()).toBeVisible()
  })

  test('保存自评草稿', async ({ page }) => {
    // 前置：admin 创建周期，HR 发起考核（包含 emp001）
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `EMP-草稿-${Date.now()}`)
    const employees = await getEmployeesViaApi(page, adminToken)
    const employee = employees.find(e => e.employee_no === 'WANG001')
    if (!employee) throw new Error('Employee WANG001 not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

    // 员工操作：emp001 登录并保存草稿
    await employeeLogin(page)

    await page.goto('/self-assessment')
    await page.waitForLoadState('networkidle')

    // 断言考核信息已加载
    await expect(page.getByText(cycle.name)).toBeVisible()

    // 填写部分分数（仅工作业绩和工作能力）
    const inputs = page.locator('.dimension-item .score-input input')
    await expect(inputs).toHaveCount(3)
    await inputs.nth(0).fill('88') // 工作业绩
    await inputs.nth(1).fill('82') // 工作能力
    // 工作态度不填，保持 null

    // 点击保存草稿
    await page.getByRole('button', { name: '保存草稿' }).click()

    // 断言草稿保存成功提示
    await expect(page.getByText('草稿保存成功')).toBeVisible()

    // 刷新页面，断言草稿回显
    await page.reload()
    await page.waitForLoadState('networkidle')

    await expect(inputs.nth(0)).toHaveValue('88.0')
    await expect(inputs.nth(1)).toHaveValue('82.0')
    await expect(inputs.nth(2)).toHaveValue('')
  })

  test('查看考核详情并下载 PDF', async ({ page }) => {
    // 前置：创建完整考核流程并发布
    // 注意：以下 API 调用属于 admin/HR/manager/peer 职责范围，仅作为测试数据前置准备
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `EMP-详情-${Date.now()}`)
    const employees = await getEmployeesViaApi(page, adminToken)
    const employee = employees.find(e => e.employee_no === 'WANG001')
    const mgr = employees.find(e => e.employee_no === 'MGR001')
    const peer = employees.find(e => e.employee_no === 'PEER001')
    if (!employee || !mgr || !peer) throw new Error('Required employees not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === employee.id)
    if (!record) throw new Error('Record not found')

    const empToken = await getToken(page, 'emp001', 'Emp001@123')
    await submitSelfScoreViaApi(page, empToken, record.record_id, {
      performance: 85, ability: 80, attitude: 90
    })

    const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
    await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
      performance: 88, ability: 82, attitude: 85
    })

    await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee.id, peer.id)
    const peerToken = await getToken(page, 'peer001', 'Peer001@123')
    await submitPeerScoreViaApi(page, peerToken, record.record_id, 78)

    await calculateScoresViaApi(page, hrToken, cycle.id)
    await advanceToInterviewViaApi(page, hrToken, cycle.id)
    await submitInterviewViaApi(page, hrToken, record.record_id)
    await publishCycleViaApi(page, hrToken, cycle.id)

    // 员工操作：emp001 登录并查看考核详情
    await employeeLogin(page)

    await page.goto('/my-performance')
    await page.waitForLoadState('networkidle')

    // 点击"查看详情"
    await page.getByRole('button', { name: '查看详情' }).first().click()

    // 断言抽屉标题
    await expect(page.getByText(`${cycle.name} - 考核详情`)).toBeVisible()

    // 断言基本信息
    await expect(page.getByText('总分').first()).toBeVisible()
    await expect(page.getByText('等级').first()).toBeVisible()
    await expect(page.getByText('部门').first()).toBeVisible()
    await expect(page.getByText('岗位').first()).toBeVisible()

    // 断言三维评分对比表
    await expect(page.getByText('三维评分对比')).toBeVisible()
    await expect(page.locator('table').filter({ hasText: '维度' }).filter({ hasText: '自评' }).filter({ hasText: '上级评' }).first()).toBeVisible()

    // 断言上级评语
    await expect(page.getByText('上级评语')).toBeVisible()
    await expect(page.getByText('This is a test comment with more than 20 characters required.')).toBeVisible()

    // 断言下载 PDF 按钮
    await expect(page.getByRole('button', { name: '下载 PDF 档案' })).toBeVisible()

    // 下载 PDF 档案
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: '下载 PDF 档案' }).click()
    ])
    const downloadPath = await download.path()
    expect(downloadPath).toBeTruthy()
  })

  test('发起申诉', async ({ page }) => {
    // 前置：创建完整考核流程，生成已发布的考核记录供 emp001 申诉
    // 注意：以下 API 调用属于 admin/HR/manager/peer 职责范围，仅作为测试数据前置准备
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `EMP-申诉-${Date.now()}`)
    const employees = await getEmployeesViaApi(page, adminToken)
    const employee = employees.find(e => e.employee_no === 'WANG001')
    const mgr = employees.find(e => e.employee_no === 'MGR001')
    const peer = employees.find(e => e.employee_no === 'PEER001')
    if (!employee || !mgr || !peer) throw new Error('Required employees not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === employee.id)
    if (!record) throw new Error('Record not found')

    const empToken = await getToken(page, 'emp001', 'Emp001@123')
    await submitSelfScoreViaApi(page, empToken, record.record_id, {
      performance: 85, ability: 80, attitude: 90
    })

    const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
    await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
      performance: 88, ability: 82, attitude: 85
    })

    await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee.id, peer.id)
    const peerToken = await getToken(page, 'peer001', 'Peer001@123')
    await submitPeerScoreViaApi(page, peerToken, record.record_id, 78)

    await calculateScoresViaApi(page, hrToken, cycle.id)
    await advanceToInterviewViaApi(page, hrToken, cycle.id)
    await submitInterviewViaApi(page, hrToken, record.record_id)
    await publishCycleViaApi(page, hrToken, cycle.id)

    // 员工操作：emp001 登录并发起申诉
    await employeeLogin(page)

    await page.goto('/appeal')
    await page.waitForLoadState('networkidle')

    // 断言可申诉的考核记录列表已加载
    await expect(page.getByText('可申诉的考核记录')).toBeVisible()
    await expect(page.getByText(cycle.name)).toBeVisible()

    // 点击"发起申诉"按钮
    await page.getByRole('button', { name: '发起申诉' }).first().click()

    // 断言申诉表单已显示
    await expect(page.getByText('发起申诉')).toBeVisible()
    await expect(page.getByText(cycle.name)).toBeVisible()

    // 选择申诉理由
    await page.locator('.el-select').click()
    await page.getByRole('option', { name: '对评分结果有异议' }).click()

    // 填写详细说明（≥20 字）
    const detailText = `对本次考核评分结果有异议，认为评分偏低，需要重新复核。${Date.now()}`
    await page.locator('textarea').fill(detailText)

    // 点击提交申诉
    await page.getByRole('button', { name: '提交申诉' }).click()

    // 断言提交成功提示
    await expect(page.getByText('申诉提交成功')).toBeVisible()

    // 断言申诉历史新增一条记录
    await expect(page.getByText('申诉历史')).toBeVisible()
    await expect(page.getByText(detailText)).toBeVisible()
    await expect(page.getByText('对评分结果有异议').first()).toBeVisible()
    await expect(page.getByText('待处理').first()).toBeVisible()
  })

  test('查看申诉历史', async ({ page }) => {
    // 前置：创建完整考核流程并发布，然后通过 API 创建申诉记录
    // 注意：以下 API 调用属于 admin/HR/manager/peer 职责范围，仅作为测试数据前置准备
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `EMP-历史-${Date.now()}`)
    const employees = await getEmployeesViaApi(page, adminToken)
    const employee = employees.find(e => e.employee_no === 'WANG001')
    const mgr = employees.find(e => e.employee_no === 'MGR001')
    const peer = employees.find(e => e.employee_no === 'PEER001')
    if (!employee || !mgr || !peer) throw new Error('Required employees not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === employee.id)
    if (!record) throw new Error('Record not found')

    const empToken = await getToken(page, 'emp001', 'Emp001@123')
    await submitSelfScoreViaApi(page, empToken, record.record_id, {
      performance: 85, ability: 80, attitude: 90
    })

    const mgrToken = await getToken(page, 'mgr001', 'Mgr001@123')
    await submitManagerScoreViaApi(page, mgrToken, record.record_id, {
      performance: 88, ability: 82, attitude: 85
    })

    await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee.id, peer.id)
    const peerToken = await getToken(page, 'peer001', 'Peer001@123')
    await submitPeerScoreViaApi(page, peerToken, record.record_id, 78)

    await calculateScoresViaApi(page, hrToken, cycle.id)
    await advanceToInterviewViaApi(page, hrToken, cycle.id)
    await submitInterviewViaApi(page, hrToken, record.record_id)
    await publishCycleViaApi(page, hrToken, cycle.id)

    // 通过 API 创建申诉记录（属于员工职责，但为前置数据准备）
    const appealReason = '对等级划分有异议'
    const appealDetail = `我认为本次考核等级划分不合理，需要重新复核。${Date.now()}`
    const appealRes = await page.request.post('/api/appeals', {
      headers: { Authorization: `Bearer ${empToken}`, 'Content-Type': 'application/json' },
      data: JSON.stringify({ record_id: record.record_id, reason: appealReason, detail: appealDetail })
    })
    if (!appealRes.ok()) throw new Error('Create appeal failed')

    // 员工操作：emp001 登录并查看申诉历史
    await employeeLogin(page)

    await page.goto('/appeal')
    await page.waitForLoadState('networkidle')

    // 断言申诉历史可见
    await expect(page.getByText('申诉历史')).toBeVisible()
    await expect(page.getByText(appealReason).first()).toBeVisible()
    await expect(page.getByText(appealDetail)).toBeVisible()
    await expect(page.getByText('待处理').first()).toBeVisible()

    // 断言时间线组件存在
    await expect(page.locator('.el-timeline').first()).toBeVisible()
  })
})
