import { test, expect } from '@playwright/test'
import { adminLogin, expectToast } from './helpers/admin-helper'

test.describe('P1-18 系统配置模块端到端测试（场景 1）', () => {
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

  test('场景 1 — 管理员配置全局并验证持久化', async ({ page }) => {
    // 1. 进入系统配置页面
    await page.goto('/config')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2').filter({ hasText: '系统配置' })).toBeVisible()

    // 2. 填写等级规则（修改 A 的比例上限从 20% 到 15%）
    const gradeTab = page.getByRole('tab', { name: '等级规则' })
    await gradeTab.click()

    const gradePane = page.locator('.el-tab-pane').filter({ hasText: '比例上限合计' })
    await expect(gradePane).toBeVisible()

    // 3rd input is A.ratio_limit (min, max, ratio_limit)
    const ratioInput = gradePane.locator('.el-input-number input').nth(2)
    await ratioInput.fill('15')
    await ratioInput.fill('15')

    await gradePane.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '保存成功')

    // 验证红点消失
    await expect(gradeTab.locator('.el-badge__content.is-dot')).not.toBeVisible()

    // 3. 填写维度权重（performance 60→50, ability 20→30, attitude 20→20）
    const weightsTab = page.getByRole('tab', { name: '维度权重' })
    await weightsTab.click()

    const weightsPane = page.locator('.el-tab-pane').filter({ hasText: '工作业绩权重' })
    await expect(weightsPane).toBeVisible()

    const weightInputs = weightsPane.locator('.el-input-number input')
    await expect(weightInputs).toHaveCount(3)

    await weightInputs.nth(0).fill('50') // performance
    await weightInputs.nth(1).fill('30') // ability
    await weightInputs.nth(2).fill('20') // attitude

    await expect(weightsPane.locator('.el-tag').filter({ hasText: '当前合计: 100% (正确)' })).toBeVisible()

    await weightsPane.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '保存成功')

    // 验证红点消失
    await expect(weightsTab.locator('.el-badge__content.is-dot')).not.toBeVisible()

    // 4. 填写评价人权重（performance: self 30→20, manager 70→80, peer 0→0）
    const reviewersTab = page.getByRole('tab', { name: '评价人权重' })
    await reviewersTab.click()

    const reviewersPane = page.locator('.el-tab-pane').filter({ hasText: '业绩维度' })
    await expect(reviewersPane).toBeVisible()

    const reviewerInputs = reviewersPane.locator('.el-input-number input')
    // 9 inputs total: 3 per dimension (self, manager, peer) × 3 dimensions
    await expect(reviewerInputs).toHaveCount(9)

    // Performance: self=20, manager=80, peer=0
    await reviewerInputs.nth(0).fill('20')
    await reviewerInputs.nth(1).fill('80')
    await reviewerInputs.nth(2).fill('0')

    await expect(reviewersPane.locator('.el-tag').filter({ hasText: '业绩维度合计: 100% (正确)' })).toBeVisible()

    await reviewersPane.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '保存成功')

    // 验证红点消失
    await expect(reviewersTab.locator('.el-badge__content.is-dot')).not.toBeVisible()

    // 5. 开启协作评分（默认已开启，直接保存消除红点）
    const peerTab = page.getByRole('tab', { name: '协作评分开关' })
    await peerTab.click()

    const peerPane = page.locator('.el-tab-pane').filter({ hasText: '协作评分全局默认值' })
    await expect(peerPane).toBeVisible()

    // Ensure switch is on
    const switchInput = peerPane.locator('.el-switch__input')
    if (await switchInput.inputValue() === 'false') {
      await peerPane.locator('.el-switch').click()
    }

    await peerPane.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '保存成功')

    // 验证红点消失
    await expect(peerTab.locator('.el-badge__content.is-dot')).not.toBeVisible()

    // 6. 验证各 Tab 数据持久化 — 刷新页面后数据应保留
    await page.reload()
    await page.waitForLoadState('networkidle')

    // 验证等级规则持久化
    await gradeTab.click()
    await expect(gradePane).toBeVisible()
    const persistedRatio = gradePane.locator('.el-input-number input').nth(2)
    await expect(persistedRatio).toHaveValue('15')

    // 验证维度权重持久化
    await weightsTab.click()
    await expect(weightsPane).toBeVisible()
    const persistedWeightInputs = weightsPane.locator('.el-input-number input')
    await expect(persistedWeightInputs.nth(0)).toHaveValue('50')
    await expect(persistedWeightInputs.nth(1)).toHaveValue('30')
    await expect(persistedWeightInputs.nth(2)).toHaveValue('20')

    // 验证评价人权重持久化
    await reviewersTab.click()
    await expect(reviewersPane).toBeVisible()
    const persistedReviewerInputs = reviewersPane.locator('.el-input-number input')
    await expect(persistedReviewerInputs.nth(0)).toHaveValue('20')
    await expect(persistedReviewerInputs.nth(1)).toHaveValue('80')
    await expect(persistedReviewerInputs.nth(2)).toHaveValue('0')

    // 验证协作评分开关持久化
    await peerTab.click()
    await expect(peerPane).toBeVisible()
    const switchCore = peerPane.locator('.el-switch')
    await expect(switchCore).toHaveClass(/is-checked/)
  })
})
