import { test, expect } from '@playwright/test'

/**
 * Peer（跨部门协作人）端到端场景测试
 * 覆盖：协作人仪表盘、协作评分待办列表、提交协作评分、查看参考评分、角色隔离、未登录重定向
 *
 * 账号-职责映射：
 * - 提交协作评分、查看协作评分待办：peer001（前端操作）
 * - 创建考核周期、发起考核：admin/hr（API 前置数据准备）
 * - 员工自评、上级评分：emp001/mgr001（API 前置，供协作人查看参考）
 * - 分配协作关系：hr001（API 前置）
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

// --- API helpers (前置数据准备，非协作人职责范围) ---
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

// --- Frontend login helpers ---
async function peerLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('peer001')
  await page.getByPlaceholder('密码').fill('Peer001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

// --- Admission tests ---
test.describe('Peer 准入性场景', () => {
  test('登录后仪表盘显示协作人专属统计与快捷操作', async ({ page }) => {
    await peerLogin(page)

    await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()

    // 协作人专属统计卡片
    await expect(page.locator('.stat-label').filter({ hasText: '待协作评分' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '已完成评分' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '总协作评分' })).toBeVisible()

    // 快捷操作入口
    await expect(page.getByRole('button', { name: '进入协作评分' })).toBeVisible()
  })

  test('可进入协作评分待办页面', async ({ page }) => {
    await peerLogin(page)

    await page.goto('/peer-review')
    await expect(page).toHaveURL(/.*\/peer-review/)
    // 断言页面存在评分卡片或空状态提示
    const reviewCard = page.locator('.review-card').first()
    const emptyTip = page.locator('.el-empty').first()
    await expect(reviewCard.or(emptyTip)).toBeVisible()
  })
})

// --- P0 + P1 核心操作流 ---
test.describe.serial('Peer 核心操作流', () => {
  test('填写并提交协作评分', async ({ page }) => {
    // 前置：admin 创建周期，HR 发起考核（包含 emp001），HR 分配 peer001 为协作人
    // 注意：以下 API 调用属于 admin/HR 职责范围，仅作为测试数据前置准备
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `PEER-评分-${Date.now()}`)
    const employees = await getEmployeesViaApi(page, adminToken)
    const employee = employees.find(e => e.employee_no === 'WANG001')
    const peer = employees.find(e => e.employee_no === 'PEER001')
    if (!employee || !peer) throw new Error('Required employees not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === employee.id)
    if (!record) throw new Error('Record not found')

    await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee.id, peer.id)

    // 协作人操作：peer001 登录并提交协作评分
    await peerLogin(page)

    await page.goto('/peer-review')
    await page.waitForLoadState('networkidle')

    // 断言考核周期信息已加载
    await expect(page.getByText(cycle.name)).toBeVisible()

    // 点击"开始评分"（根据考核周期名称定位卡片）
    await page.locator('.review-card').filter({ hasText: cycle.name }).getByRole('button', { name: '开始评分' }).click()

    // 等待评分页面加载
    await page.waitForURL(/.*\/peer-review\/.+/)
    await expect(page.getByRole('heading', { name: /协作评分/ })).toBeVisible()

    // 填写工作能力分数
    await page.locator('.score-input input').fill('88')

    // 点击提交评分
    await page.getByRole('button', { name: '提交评分' }).click()

    // 断言提交成功提示
    await expect(page.getByText('评分提交成功')).toBeVisible()

    // 断言返回协作评分待办列表
    await expect(page).toHaveURL(/.*\/peer-review/)
    await page.waitForLoadState('networkidle')

    // 断言该评分卡片已不在待办列表中（状态变为完成后从 pending 列表消失）
    await expect(page.locator('.review-card').filter({ hasText: cycle.name })).toHaveCount(0)
  })

  test('查看评分参考（自评/上级评）', async ({ page }) => {
    // 前置：admin 创建周期，HR 发起考核，emp001 自评，mgr001 上级评，HR 分配 peer001
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `PEER-参考-${Date.now()}`)
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

    // 协作人操作：peer001 登录并查看评分参考
    await peerLogin(page)

    await page.goto('/peer-review')
    await page.waitForLoadState('networkidle')

    // 断言列表中显示了该卡片的自评和上级评参考
    const card = page.locator('.review-card').filter({ hasText: cycle.name })
    await expect(card).toBeVisible()
    await expect(card.getByText('员工自评：')).toBeVisible()
    await expect(card.getByText('上级评分：')).toBeVisible()

    // 点击该卡片的开始评分
    await card.getByRole('button', { name: '开始评分' }).click()
    await page.waitForURL(/.*\/peer-review\/.+/)

    // 断言评分详情页显示自评参考和上级评分参考
    await expect(page.getByText('员工自评参考')).toBeVisible()
    await expect(page.getByText('上级评分参考')).toBeVisible()

    // 断言具体分数值可见
    await expect(page.getByText('85').first()).toBeVisible()
    await expect(page.getByText('80').first()).toBeVisible()
    await expect(page.getByText('88').first()).toBeVisible()
    await expect(page.getByText('82').first()).toBeVisible()
  })

  test('验证协作人角色隔离', async ({ page }) => {
    await peerLogin(page)

    await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()

    // 协作人应能看到"进入协作评分"
    await expect(page.getByRole('button', { name: '进入协作评分' })).toBeVisible()

    // 协作人不应看到员工专属入口
    await expect(page.getByRole('button', { name: '进入自评' })).not.toBeVisible()
    await expect(page.getByRole('button', { name: '查看历史绩效' })).not.toBeVisible()
    await expect(page.getByRole('button', { name: '发起申诉' })).not.toBeVisible()

    // 协作人不应看到管理菜单
    await expect(page.getByText('员工管理').first()).not.toBeVisible()
    await expect(page.getByText('考核管理').first()).not.toBeVisible()
  })

  test('未登录访问协作评分页面被重定向到登录页', async ({ page }) => {
    await page.goto('/peer-review')
    await page.waitForURL('**/login')
    await expect(page).toHaveURL(/.*\/login/)
  })

  test('空状态（无待办协作评分任务）', async ({ page }) => {
    await peerLogin(page)

    await page.goto('/peer-review')
    await page.waitForLoadState('networkidle')

    // 清理所有待办卡片，使其变为完成状态，从而确保空状态出现
    let cards = page.locator('.review-card')
    while (await cards.count() > 0) {
      await cards.first().getByRole('button', { name: '开始评分' }).click()
      await page.waitForURL(/.*\/peer-review\/.+/)
      await page.locator('.score-input input').fill('0')
      await page.getByRole('button', { name: '提交评分' }).click()
      await expect(page.getByText('评分提交成功')).toBeVisible()
      await page.waitForURL(/.*\/peer-review/)
      await page.waitForLoadState('networkidle')
      cards = page.locator('.review-card')
    }

    // 断言空状态
    await expect(page.locator('.el-empty')).toBeVisible()
    await expect(page.getByText('暂无待办协作评分任务')).toBeVisible()
  })
})

// --- P2 边界与校验测试 ---
// 将 B-6、B-4、B-5 合并为单个测试，避免 serial 块跨 worker 导致 page 状态丢失
test('B-6/B-4/B-5: 空值拦截、评分锚点、范围校验', async ({ page }) => {
  // 前置：创建考核周期并分配协作人
  const adminToken = await getToken(page, 'admin', 'admin123')
  const cycle = await createCycleViaApi(page, adminToken, `PEER-边界-${Date.now()}`)
  const employees = await getEmployeesViaApi(page, adminToken)
  const employee = employees.find(e => e.employee_no === 'WANG001')
  const peer = employees.find(e => e.employee_no === 'PEER001')
  if (!employee || !peer) throw new Error('Required employees not found')

  const hrToken = await getToken(page, 'hr001', 'Hr001@123')
  await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

  const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
  const record = summary.find(r => r.employee_id === employee.id)
  if (!record) throw new Error('Record not found')

  await assignPeerReviewerViaApi(page, hrToken, cycle.id, employee.id, peer.id)

  await peerLogin(page)
  await page.goto('/peer-review')
  await page.waitForLoadState('networkidle')
  await page.locator('.review-card').filter({ hasText: cycle.name }).getByRole('button', { name: '开始评分' }).click()
  await page.waitForURL(/.*\/peer-review\/.+/)

  // B-6: 空值提交拦截（提交按钮禁用）
  await expect(page.getByRole('button', { name: '提交评分' })).toBeDisabled()

  // B-4: 查看评分锚点说明
  await page.locator('.anchor-icon').hover()
  await expect(page.locator('.el-popper').filter({ hasText: '90-100 分 = 优秀' })).toBeVisible()
  await expect(page.getByText('90-100 分 = 优秀')).toBeVisible()
  await expect(page.getByText('超出预期，表现卓越')).toBeVisible()
  await expect(page.getByText('80-89 分 = 良好')).toBeVisible()
  await expect(page.getByText('0-59 分 = 待改进')).toBeVisible()

  // B-5: 校验分数范围拦截
  // 输入 -1，el-input-number 应自动截断为 0
  await page.locator('.score-input input').fill('-1')
  await page.locator('.score-input input').blur()
  await expect(page.locator('.score-input input')).toHaveValue('0.0')

  // 输入 101，el-input-number 应自动截断为 100
  await page.locator('.score-input input').fill('101')
  await page.locator('.score-input input').blur()
  await expect(page.locator('.score-input input')).toHaveValue('100.0')
})
