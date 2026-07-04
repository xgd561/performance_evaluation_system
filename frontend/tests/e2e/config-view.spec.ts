import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

async function expectToast(page, text) {
  const toast = page.locator('.el-message').filter({ hasText: text }).first()
  await expect(toast).toBeVisible({ timeout: 5000 })
}

test.describe('P1-13 系统配置页面整合', () => {
  test.describe.configure({ mode: 'serial' })

  test.beforeAll(async ({ request }) => {
    // Reset all configs to defaults via backend API so tests have deterministic state
    const login = await request.post('http://localhost:8000/auth/login', {
      data: { username: 'admin', password: 'admin123' }
    })
    const token = (await login.json()).access_token

    await request.put('http://localhost:8000/config/grade-rules', {
      data: {
        A: { min: 90, max: 100, ratio_limit: 0.2 },
        B: { min: 80, max: 89.9, ratio_limit: 0.5 },
        C: { min: 60, max: 79.9, ratio_limit: 0.25 },
        D: { min: 0, max: 59.9, ratio_limit: 0.05 },
      },
      headers: { Authorization: `Bearer ${token}` }
    })
    await request.put('http://localhost:8000/config/dimension-weights', {
      data: { performance: 60, ability: 20, attitude: 20 },
      headers: { Authorization: `Bearer ${token}` }
    })
    await request.put('http://localhost:8000/config/reviewer-weights', {
      data: {
        performance: { self: 30, manager: 70, peer: 0 },
        ability: { self: 20, manager: 60, peer: 20 },
        attitude: { self: 10, manager: 50, peer: 40 },
      },
      headers: { Authorization: `Bearer ${token}` }
    })
    await request.put('http://localhost:8000/config/small-dept-exemption', {
      data: { enabled: true, threshold: 5 },
      headers: { Authorization: `Bearer ${token}` }
    })
    await request.put('http://localhost:8000/config/peer-review-enabled', {
      data: { enabled: true },
      headers: { Authorization: `Bearer ${token}` }
    })
  })

  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
  })

  test('页面加载 — 显示顶部提示和 5 个 Tab', async ({ page }) => {
    await page.goto('/config')
    await page.waitForLoadState('networkidle')

    await expect(page.locator('h2').filter({ hasText: '系统配置' })).toBeVisible()

    // Top banner
    await expect(page.locator('.el-alert').filter({ hasText: '配置变更将仅影响新考核周期' })).toBeVisible()

    // 5 tabs
    await expect(page.getByRole('tab', { name: '等级规则' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '维度权重' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '评价人权重' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '小部门豁免' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '协作评分开关' })).toBeVisible()
  })

  test('未配置项显示红点 — 默认状态下 5 个 Tab 均有红点', async ({ page }) => {
    await page.goto('/config')
    await page.waitForLoadState('networkidle')

    for (const tabName of ['等级规则', '维度权重', '评价人权重', '小部门豁免', '协作评分开关']) {
      const tab = page.getByRole('tab', { name: tabName })
      await expect(tab).toBeVisible()
      // The badge dot is rendered as .el-badge__content.is-dot inside the tab
      await expect(tab.locator('.el-badge__content.is-dot')).toBeVisible()
    }
  })

  test('等级规则 Tab — 修改并保存后红点消失', async ({ page }) => {
    await page.goto('/config')
    await page.waitForLoadState('networkidle')

    const gradeTab = page.getByRole('tab', { name: '等级规则' })
    await gradeTab.click()

    // Use pane content-specific text to identify the active pane
    const pane = page.locator('.el-tab-pane').filter({ hasText: '比例上限合计' })
    await expect(pane).toBeVisible()

    // Modify a safe grade rule value: change A.ratio_limit from 20 to 15
    // (this won't break overlap/continuity or ratio total validation)
    const ratioInput = pane.locator('.el-input-number input').nth(2) // 3rd input is A.ratio_limit
    await ratioInput.fill('15')
    await ratioInput.fill('15') // ensure it sticks

    await pane.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '保存成功')

    // After saving, the red dot for grades should disappear
    await expect(gradeTab.locator('.el-badge__content.is-dot')).not.toBeVisible()
  })

  test('维度权重 Tab — 合计验证与保存', async ({ page }) => {
    await page.goto('/config')
    await page.waitForLoadState('networkidle')

    const weightsTab = page.getByRole('tab', { name: '维度权重' })
    await weightsTab.click()

    const pane = page.locator('.el-tab-pane').filter({ hasText: '工作业绩权重' })
    await expect(pane).toBeVisible()

    const inputs = pane.locator('.el-input-number input')
    await expect(inputs).toHaveCount(3)

    // Check total tag
    await expect(pane.locator('.el-tag').filter({ hasText: '当前合计: 100% (正确)' })).toBeVisible()

    // Change one value to break total (60 -> 50, total = 50+20+20 = 90)
    await inputs.nth(0).fill('50')
    await expect(pane.locator('.el-tag').filter({ hasText: '当前合计: 90% (应为100)' })).toBeVisible()

    // Save button should be disabled when total != 100
    const saveBtn = pane.getByRole('button', { name: '保存' })
    await expect(saveBtn).toBeDisabled()

    // Fix total
    await inputs.nth(1).fill('30')
    await inputs.nth(2).fill('20')
    await expect(pane.locator('.el-tag').filter({ hasText: '当前合计: 100% (正确)' })).toBeVisible()
    await expect(saveBtn).toBeEnabled()

    await saveBtn.click()
    await expectToast(page, '保存成功')

    // Red dot should disappear
    await expect(weightsTab.locator('.el-badge__content.is-dot')).not.toBeVisible()
  })

  test('评价人权重 Tab — 三个维度合计验证', async ({ page }) => {
    await page.goto('/config')
    await page.waitForLoadState('networkidle')

    const reviewersTab = page.getByRole('tab', { name: '评价人权重' })
    await reviewersTab.click()

    const pane = page.locator('.el-tab-pane').filter({ hasText: '业绩维度' })
    await expect(pane).toBeVisible()

    await expect(pane.locator('.el-tag').filter({ hasText: '业绩维度合计: 100% (正确)' })).toBeVisible()
    await expect(pane.locator('.el-tag').filter({ hasText: '能力维度合计: 100% (正确)' })).toBeVisible()
    await expect(pane.locator('.el-tag').filter({ hasText: '态度维度合计: 100% (正确)' })).toBeVisible()

    // Save button should be enabled when totals are valid
    const saveBtn = pane.getByRole('button', { name: '保存' })
    await expect(saveBtn).toBeEnabled()

    await saveBtn.click()
    await expectToast(page, '保存成功')

    await expect(reviewersTab.locator('.el-badge__content.is-dot')).not.toBeVisible()
  })

  test('小部门豁免 Tab — 保存并验证红点消失', async ({ page }) => {
    await page.goto('/config')
    await page.waitForLoadState('networkidle')

    const smallDeptTab = page.getByRole('tab', { name: '小部门豁免' })
    await smallDeptTab.click()

    const pane = page.locator('.el-tab-pane').filter({ hasText: '部门人数阈值' })
    await expect(pane).toBeVisible()

    // Toggle the switch to change from default
    await pane.locator('.el-switch').click()
    await pane.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '保存成功')

    await expect(smallDeptTab.locator('.el-badge__content.is-dot')).not.toBeVisible()
  })

  test('协作评分开关 Tab — 保存并验证红点消失', async ({ page }) => {
    await page.goto('/config')
    await page.waitForLoadState('networkidle')

    const peerTab = page.getByRole('tab', { name: '协作评分开关' })
    await peerTab.click()

    const pane = page.locator('.el-tab-pane').filter({ hasText: '协作评分全局默认值' })
    await expect(pane).toBeVisible()

    // Toggle switch
    await pane.locator('.el-switch').click()
    await pane.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '保存成功')

    await expect(peerTab.locator('.el-badge__content.is-dot')).not.toBeVisible()
  })

  test('非 admin 角色访问配置页面显示 403', async ({ page }) => {
    // Login as HR (non-admin role, is_first_login=false)
    await page.goto('/login')
    await page.getByPlaceholder('用户名').fill('hr001')
    await page.getByPlaceholder('密码').fill('Hr001@123')
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForURL('/dashboard')

    // Try to access /config
    await page.goto('/config')
    await page.waitForLoadState('networkidle')

    // Should be redirected to 403
    await expect(page).toHaveURL('/403')
    await expect(page.locator('.el-result__title').filter({ hasText: '403' })).toBeVisible()
    await expect(page.locator('.el-result__subtitle').filter({ hasText: '抱歉，您没有权限访问此页面' })).toBeVisible()
  })
})
