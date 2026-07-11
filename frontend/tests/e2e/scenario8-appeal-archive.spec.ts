import { test, expect } from '@playwright/test'

/**
 * E2E 场景 8：申诉与归档
 * 覆盖：完成考核 → 发布 → 员工查看结果 → 发起申诉 → 填写理由 →
 *       HR 查看申诉详情 → 复核评分数据 → 选择「维持原结果」→ 录入结论 →
 *       员工查看申诉结果 → HR 执行归档 → 验证状态变为 archived → 下载 PDF 档案
 */

async function adminLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('admin')
  await page.getByPlaceholder('密码').fill('admin123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

async function hrLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('hr001')
  await page.getByPlaceholder('密码').fill('admin123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

async function employeeLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('emp001')
  await page.getByPlaceholder('密码').fill('admin123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

async function managerLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('mgr001')
  await page.getByPlaceholder('密码').fill('admin123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

async function getToken(page, username, password) {
  const res = await page.request.post('/api/v1/auth/login', {
    headers: { 'Content-Type': 'application/json' },
    data: JSON.stringify({ username, password })
  })
  const body = await res.json()
  if (!body.access_token) throw new Error(`Login failed for ${username}: ${JSON.stringify(body)}`)
  return body.access_token
}

async function createCycleViaApi(page, token, name) {
  const today = new Date().toISOString().split('T')[0]
  const end = new Date()
  end.setMonth(end.getMonth() + 1)
  const endDate = end.toISOString().split('T')[0]
  const res = await page.request.post('/api/v1/assessment-cycles', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ name, type: 'monthly', start_date: today, end_date: endDate, weights: { self: 30, manager: 50, peer: 20 }, grade_rules: { A: 90, B: 80, C: 60, D: 0 } })
  })
  return await res.json()
}

async function launchCycleViaApi(page, token, cycleId, employeeIds) {
  const res = await page.request.post('/api/v1/assessment-cycles/launch', {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ cycle_id: cycleId, employee_ids: employeeIds })
  })
  return await res.json()
}

async function getScoreSummaryViaApi(page, token, cycleId) {
  const res = await page.request.get(`/api/v1/scores/summary/${cycleId}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

async function publishCycleViaApi(page, token, cycleId) {
  const res = await page.request.post(`/api/v1/assessment-cycles/${cycleId}/publish`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

async function advanceToInterviewViaApi(page, token, cycleId) {
  const res = await page.request.post(`/api/v1/assessment-cycles/${cycleId}/advance-to-interview`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  return await res.json()
}

async function submitInterviewViaApi(page, token, recordId) {
  const res = await page.request.post(`/api/v1/interviews/${recordId}`, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: JSON.stringify({ content: '本次面谈确认绩效结果，员工认可。', improvement_plan: '继续保持现有工作状态。' })
  })
  return await res.json()
}

test.describe('场景 8 — 申诉与归档', () => {
  test('员工申诉后 HR 维持原结果并归档周期', async ({ page }) => {
    test.setTimeout(180000)

    // ============================
    // 前置：API 准备完整考核数据
    // ============================
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `场景8-${Date.now()}`)
    const emps = await page.request.get('/api/v1/employees?page=1&size=100', {
      headers: { Authorization: `Bearer ${adminToken}` }
    }).then(r => r.json()).then(j => j.items || [])
    const emp = emps.find(e => e.employee_no === 'EMP001')
    if (!emp) throw new Error('EMP001 not found')

    const hrToken = await getToken(page, 'hr001', 'admin123')
    await launchCycleViaApi(page, hrToken, cycle.id, [emp.id])

    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === emp.id)
    if (!record) throw new Error('Record not found')
    const recordId = record.record_id

    // 员工自评
    const empToken = await getToken(page, 'emp001', 'admin123')
    await page.request.post(`/api/v1/scores/self/${recordId}`, {
      headers: { Authorization: `Bearer ${empToken}`, 'Content-Type': 'application/json' },
      data: JSON.stringify({ performance: 85, ability: 80, attitude: 90 })
    })

    // 经理评分
    const mgrToken = await getToken(page, 'mgr001', 'admin123')
    await page.request.post(`/api/v1/scores/manager/${recordId}`, {
      headers: { Authorization: `Bearer ${mgrToken}`, 'Content-Type': 'application/json' },
      data: JSON.stringify({ performance: 88, ability: 82, attitude: 85, comment: 'This is a test comment with more than 20 characters required.' })
    })

    // 汇总 + 推进到面谈 + 发布
    await page.request.post(`/api/v1/scores/calculate/${cycle.id}`, {
      headers: { Authorization: `Bearer ${hrToken}` }
    })
    await advanceToInterviewViaApi(page, adminToken, cycle.id)
    await submitInterviewViaApi(page, mgrToken, recordId)
    await publishCycleViaApi(page, hrToken, cycle.id)

    // ============================
    // ① 员工登录 → 查看结果 → 发起申诉
    // ============================
    await employeeLogin(page)
    await page.goto('/my-performance')
    await page.waitForLoadState('networkidle')
    await expect(page.getByText('历史考核记录')).toBeVisible()

    // 断言已发布记录可见（包含总分和等级）
    const recordRow = page.locator('table tbody tr').filter({ hasText: cycle.name })
    await expect(recordRow).toBeVisible()
    await expect(recordRow).toContainText('已发布')

    // 查看详情：断言总分、等级、三维评分对比、上级评语、下载 PDF 按钮可见
    await recordRow.getByRole('button', { name: '查看详情' }).first().click()
    await expect(page.locator('.el-drawer')).toBeVisible()
    await expect(page.getByText('考核详情')).toBeVisible()
    await expect(page.getByText('三维评分对比')).toBeVisible()
    await expect(page.getByText('上级评语')).toBeVisible()
    await expect(page.locator('.detail-actions').getByRole('button', { name: '下载 PDF 档案' })).toBeVisible()
    await page.locator('.el-drawer__header .el-drawer__close').click()

    // 发起申诉
    await page.goto('/appeal')
    await page.waitForLoadState('networkidle')
    await expect(page.getByText('可申诉的考核记录')).toBeVisible()
    await expect(page.getByText(cycle.name)).toBeVisible()
    await page.getByRole('button', { name: '发起申诉' }).first().click()
    await page.locator('.el-select').click()
    await page.getByRole('option', { name: '对评分结果有异议' }).click()
    const appealDetail = `本季度主导了多个重点项目，业绩完成度高于预期，认为等级应为A。${Date.now()}`
    await page.locator('textarea').nth(0).fill(appealDetail)
    await page.getByRole('button', { name: '提交申诉' }).click()
    await expect(page.getByText('申诉提交成功')).toBeVisible()

    // ============================
    // ② HR 登录 → 申诉管理 → 查看详情 → 复核评分数据 → 维持原结果
    // ============================
    await hrLogin(page)
    await page.goto('/appeals')
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/.*\/appeals/)

    // 查看申诉列表，存在待处理申诉
    const appealRow = page.locator('table tbody tr').filter({ hasText: '对评分结果有异议' }).first()
    await expect(appealRow).toBeVisible()
    await expect(appealRow.getByText('待处理')).toBeVisible()

    // 点击查看详情，复核评分数据
    await appealRow.getByRole('button', { name: '查看' }).click()
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/.*\/appeal-detail/)
    await expect(page.getByText('申诉信息')).toBeVisible()
    await expect(page.getByText('评分原始数据')).toBeVisible()
    await expect(page.getByText('自评 - 业绩')).toBeVisible()
    await expect(page.getByText('上级评 - 业绩')).toBeVisible()
    await expect(page.getByText('总分', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: '返回' }).click()
    await page.waitForLoadState('networkidle')

    // 点击处理，选择维持原结果
    await appealRow.getByRole('button', { name: '处理' }).click()
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/.*\/appeal-detail/)
    await expect(page.getByText('复核处理')).toBeVisible()

    // 选择维持原结果，填写复核结论
    await page.getByRole('radio', { name: '维持原结果' }).check()
    await page.getByPlaceholder('请填写复核结论').fill('经复核，评分数据完整，计算过程无误，维持原结果。')
    await page.getByRole('button', { name: '提交复核' }).click()
    await expect(page.getByText('复核处理成功')).toBeVisible()

    // ============================
    // ③ 员工登录 → 查看申诉结果
    // ============================
    await employeeLogin(page)
    await page.goto('/my-performance')
    await page.waitForLoadState('networkidle')
    await expect(page.getByText('历史考核记录')).toBeVisible()

    // 再次查看详情，断言申诉记录显示已处理和处理结果
    await recordRow.getByRole('button', { name: '查看详情' }).first().click()
    await expect(page.locator('.el-drawer')).toBeVisible()
    await expect(page.getByText('申诉记录')).toBeVisible()
    await expect(page.getByText('经复核，评分数据完整，计算过程无误，维持原结果。')).toBeVisible()
    await page.locator('.el-drawer__header .el-drawer__close').click()

    // ============================
    // ④ HR 登录 → 通过 API 执行归档 → 验证状态变为 archived
    // ============================
    await hrLogin(page)
    // 前端暂无归档按钮，直接调用 API 归档
    const archiveRes = await page.request.post(`/api/v1/assessment-cycles/${cycle.id}/archive`, {
      headers: { Authorization: `Bearer ${hrToken}` }
    })
    const archiveBody = await archiveRes.json()
    if (archiveRes.status() !== 200 && archiveBody?.message !== '考核周期已归档') {
      throw new Error(`Archive failed: ${JSON.stringify(archiveBody)}`)
    }
    await page.goto('/cycles')
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/.*\/cycles/)
    const cycleRow = page.locator('table tbody tr').filter({ hasText: cycle.name })
    await expect(cycleRow.locator('td').nth(8)).toContainText('已归档')

    // ============================
    // ⑤ 员工登录 → 下载 PDF 档案
    // ============================
    await employeeLogin(page)
    await page.goto('/my-performance')
    await page.waitForLoadState('networkidle')
    await recordRow.getByRole('button', { name: '查看详情' }).first().click()
    await expect(page.locator('.el-drawer')).toBeVisible()

    // 触发下载并断言下载行为
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.locator('.detail-actions').getByRole('button', { name: '下载 PDF 档案' }).click()
    ])
    expect(download.suggestedFilename()).toMatch(/performance_.*\.pdf/)
  })
})
