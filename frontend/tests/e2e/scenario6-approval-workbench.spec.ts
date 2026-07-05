import { test, expect } from '@playwright/test'
import { managerLogin, hrLogin, employeeLogin } from './helpers/approval-helper'

/**
 * Scenario 6: Approval Workbench 端到端测试
 * 覆盖：Manager Step1 视图、HR Step2 视图、未授权访问、部门筛选
 */

test.describe('审批工作台 — Manager Step 1 视图', () => {
  test.beforeEach(async ({ page }) => {
    await managerLogin(page)
    await page.goto('/approval-workbench')
    await page.waitForTimeout(500)
  })

  test('应仅显示 Step 1 待审批记录', async ({ page }) => {
    const table = page.locator('table').first()
    await expect(table).toBeVisible()

    const rows = table.locator('tbody tr')
    const count = await rows.count()
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        await expect(rows.nth(i).locator('td').filter({ hasText: 'Step 1 待审批' }).first()).toBeVisible()
      }
    }
  })

  test('操作按钮和查看详情按钮应存在', async ({ page }) => {
    const firstRow = page.locator('table tbody tr').first()
    if (await firstRow.isVisible().catch(() => false)) {
      await expect(firstRow.getByRole('button', { name: '通过' })).toBeVisible()
      await expect(firstRow.getByRole('button', { name: '驳回' })).toBeVisible()
      await expect(firstRow.getByRole('button', { name: '打回重评' })).toBeVisible()
      await expect(firstRow.getByRole('button', { name: '查看详情' })).toBeVisible()
    }
  })

  test('查看详情按钮应导航到 ApprovalDetail', async ({ page }) => {
    const firstRow = page.locator('table tbody tr').first()
    if (await firstRow.isVisible().catch(() => false)) {
      await firstRow.getByRole('button', { name: '查看详情' }).click()
      await page.waitForURL('**/approval-detail?record_id=*')
      await expect(page).toHaveURL(/.*/approval-detail\?record_id=.*/)
      await expect(page.getByRole('heading', { name: '审批详情' })).toBeVisible()
    }
  })
})

test.describe('审批工作台 — HR Step 2 视图', () => {
  test.beforeEach(async ({ page }) => {
    await hrLogin(page)
    await page.goto('/approval-workbench')
    await page.waitForTimeout(500)
  })

  test('应显示 Step 2 待审批记录', async ({ page }) => {
    const table = page.locator('table').first()
    await expect(table).toBeVisible()

    // 先切换到 Step 2 筛选
    await page.getByRole('radio', { name: 'Step 2 待审批' }).click()
    await page.waitForTimeout(300)

    const rows = table.locator('tbody tr')
    const count = await rows.count()
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        await expect(rows.nth(i).locator('td').filter({ hasText: 'Step 2 待审批' }).first()).toBeVisible()
      }
    }
  })

  test('筛选器应正常工作', async ({ page }) => {
    await expect(page.getByRole('button', { name: '查询' })).toBeVisible()
    await expect(page.getByRole('button', { name: '重置' })).toBeVisible()

    // 切换 Step 1
    await page.getByRole('radio', { name: 'Step 1 待审批' }).click()
    await page.waitForTimeout(300)

    // 切换全部
    await page.getByRole('radio', { name: '全部' }).click()
    await page.waitForTimeout(300)
  })
})

test.describe('审批工作台 — 未授权访问', () => {
  test('普通员工应被重定向到 403 或仪表盘', async ({ page }) => {
    await employeeLogin(page)
    await page.goto('/approval-workbench')
    await page.waitForTimeout(500)

    const url = page.url()
    const is403 = url.includes('/403')
    const isDashboard = url.includes('/dashboard')
    expect(is403 || isDashboard).toBe(true)
  })
})

test.describe('审批工作台 — 部门筛选', () => {
  test.beforeEach(async ({ page }) => {
    await hrLogin(page)
    await page.goto('/approval-workbench')
    await page.waitForTimeout(500)
  })

  test('按部门筛选后表格应更新', async ({ page }) => {
    const table = page.locator('table').first()
    await expect(table).toBeVisible()

    // 打开部门下拉框
    const deptSelect = page.locator('.el-form-item').filter({ hasText: '部门' }).locator('.el-select').first()
    await deptSelect.click()
    await page.waitForTimeout(300)

    // 选择第一个部门选项（如果存在）
    const firstOption = page.locator('.el-select-dropdown__item').first()
    const hasOptions = await firstOption.isVisible().catch(() => false)

    if (hasOptions) {
      const deptName = await firstOption.textContent() || ''
      await firstOption.click()
      await page.waitForTimeout(200)

      await page.getByRole('button', { name: '查询' }).click()
      await page.waitForTimeout(500)

      // 断言表格中所有行的部门列都等于选中的部门
      const rows = table.locator('tbody tr')
      const count = await rows.count()
      if (count > 0) {
        for (let i = 0; i < count; i++) {
          const deptCell = rows.nth(i).locator('td').nth(2) // 部门列是第3列
          await expect(deptCell).toHaveText(deptName.trim())
        }
      }
    }
  })
})
