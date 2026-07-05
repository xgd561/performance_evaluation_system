import { test, expect } from '@playwright/test'

/**
 * E2E: 员工自评场景 (P4-21)
 * 场景：员工登录 → 进入我的绩效/自评页面 → 填写三维评分 → 保存草稿 → 刷新验证 → 提交自评
 */

// --- Auth helpers ---
async function employeeLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('emp001')
  await page.getByPlaceholder('密码').fill('Emp001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

// --- API helpers ---
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

test.describe('员工自评场景 (P4-21)', () => {
  test.describe.configure({ mode: 'serial' })

  test('员工自评完整流程：填写、保存草稿、刷新恢复、提交', async ({ page }) => {
    test.setTimeout(60000)

    // ========== 前置：admin 创建考核周期并发起，确保 emp001 有待自评记录 ==========
    const adminToken = await getToken(page, 'admin', 'admin123')
    const cycle = await createCycleViaApi(page, adminToken, `SELF-TEST-${Date.now()}`)
    const employees = await getEmployeesViaApi(page, adminToken)
    const employee = employees.find(e => e.employee_no === 'EMP001')
    if (!employee) throw new Error('Employee EMP001 not found')

    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    await launchCycleViaApi(page, hrToken, cycle.id, [employee.id])

    // 获取 record_id
    const summary = await getScoreSummaryViaApi(page, hrToken, cycle.id)
    const record = summary.find(r => r.employee_id === employee.id)
    if (!record) throw new Error('Record not found after launch')

    // ========== Step 1: 员工登录 ==========
    await employeeLogin(page)

    // 断言已进入员工仪表盘
    await expect(page.locator('.card-header').filter({ hasText: '我的绩效首页' })).toBeVisible()

    // ========== Step 2: 进入自评页面 ==========
    // 通过快捷操作"进入自评"按钮直接进入自评页
    await page.getByRole('button', { name: '进入自评' }).click()
    await page.waitForURL('**/self-assessment')
    await expect(page).toHaveURL(/.*\/self-assessment/)

    // 等待页面加载（考核信息、维度输入框）
    await page.waitForLoadState('networkidle')
    await expect(page.getByText('考核信息')).toBeVisible()
    await expect(page.getByText('维度自评')).toBeVisible()

    // ========== Step 3: 填写三维评分 ==========
    // 使用 .score-input 定位三个 el-input-number
    const scoreInputs = page.locator('.dimension-item .score-input input')
    await expect(scoreInputs).toHaveCount(3)

    // 填写：业绩 82，能力 84，态度 88
    await scoreInputs.nth(0).fill('82')
    await scoreInputs.nth(1).fill('84')
    await scoreInputs.nth(2).fill('88')

    // 断言输入值已写入（el-input-number 可能显示 82 或 82.0）
    await expect(scoreInputs.nth(0)).toHaveValue(/82(\.0)?/)
    await expect(scoreInputs.nth(1)).toHaveValue(/84(\.0)?/)
    await expect(scoreInputs.nth(2)).toHaveValue(/88(\.0)?/)

    // ========== Step 4: 保存草稿 ==========
    // 拦截草稿保存 API 以验证调用
    let draftSaved = false
    await page.route('**/api/v1/score-drafts', async (route) => {
      if (route.request().method() === 'POST') {
        draftSaved = true
      }
      await route.continue()
    })

    await page.getByRole('button', { name: '保存草稿' }).click()

    // 等待保存成功提示（Element Plus Message）
    await expect(page.getByText('草稿保存成功')).toBeVisible()
    expect(draftSaved).toBe(true)

    // ========== Step 5: 刷新页面，验证草稿恢复 ==========
    await page.reload()
    await page.waitForLoadState('networkidle')

    // 等待"已自动恢复上次保存的草稿"提示或分数直接恢复
    await expect(page.getByText('已自动恢复上次保存的草稿')).toBeVisible()

    // 断言三个分数已恢复（el-input-number 可能显示 82 或 82.0）
    await expect(scoreInputs.nth(0)).toHaveValue(/82(\.0)?/)
    await expect(scoreInputs.nth(1)).toHaveValue(/84(\.0)?/)
    await expect(scoreInputs.nth(2)).toHaveValue(/88(\.0)?/)

    // ========== Step 6: 提交自评 ==========
    // 点击提交按钮，会弹出确认对话框
    await page.getByRole('button', { name: '提交自评' }).click()

    // 确认对话框（Element Plus MessageBox 使用 OK / Cancel）
    await expect(page.getByText('确认提交自评？提交后不可修改')).toBeVisible()
    await page.getByRole('button', { name: 'OK' }).click()

    // 等待提交成功提示和跳转
    await expect(page.getByText('自评提交成功')).toBeVisible()
    await page.waitForURL('**/my-performance')
    await expect(page).toHaveURL(/.*\/my-performance/)

    // 断言状态变为"待上级评"（取第一个匹配的元素，即状态标签）
    await expect(page.getByText('待上级评').first()).toBeVisible()
  })

  test('未登录用户访问自评页面被重定向到登录页', async ({ page }) => {
    await page.goto('/self-assessment')
    await page.waitForURL('**/login')
    await expect(page).toHaveURL(/.*\/login/)
  })
})
