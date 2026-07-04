import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

async function selectInRow(row, optionText) {
  // 点击当前行内的 select（计分方式列）
  await row.locator('.el-select').first().click()
  // 等待下拉并选择选项
  const option = row.page().getByRole('option', { name: optionText }).last()
  await option.click()
}

async function expectToast(page, text) {
  const toast = page.locator('.el-message').filter({ hasText: text }).first()
  await expect(toast).toBeVisible({ timeout: 5000 })
}

test.describe('P1-11 KPI 模板编辑页', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
  })

  test('新建模板 — 添加 3 个指标并保存，权重合计 100%', async ({ page }) => {
    await page.goto('/kpi-templates')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2').filter({ hasText: 'KPI 模板管理' })).toBeVisible()

    await page.getByRole('button', { name: '新建模板' }).click()
    await page.waitForURL('**/kpi-templates/create')
    await expect(page.locator('h2').filter({ hasText: '新建 KPI 模板' })).toBeVisible()

    // 选择岗位（表单中的 select，使用 label 方式）
    const positionSelect = page.locator('.el-form-item').filter({ hasText: '关联岗位' }).locator('.el-select').first()
    await positionSelect.click()
    await page.getByRole('option', { name: '系统管理员' }).last().click()

    const table = page.locator('.el-table')
    await expect(table.locator('tbody tr')).toHaveCount(1)

    // 第1行
    const row0 = table.locator('tbody tr').nth(0)
    await row0.locator('input').nth(0).fill('工作业绩')
    await row0.locator('.el-input-number input').fill('60')
    await row0.locator('input').nth(2).fill('100万')
    await selectInRow(row0, '百分比')
    await row0.locator('textarea').fill('按完成率计分')

    // 第2行
    await page.getByRole('button', { name: '+ 添加指标' }).click()
    await expect(table.locator('tbody tr')).toHaveCount(2)
    const row1 = table.locator('tbody tr').nth(1)
    await row1.locator('input').nth(0).fill('工作能力')
    await row1.locator('.el-input-number input').fill('20')
    await row1.locator('input').nth(2).fill('95%')
    await selectInRow(row1, '定性评价')
    await row1.locator('textarea').fill('按能力评价计分')

    // 第3行
    await page.getByRole('button', { name: '+ 添加指标' }).click()
    await expect(table.locator('tbody tr')).toHaveCount(3)
    const row2 = table.locator('tbody tr').nth(2)
    await row2.locator('input').nth(0).fill('工作态度')
    await row2.locator('.el-input-number input').fill('20')
    await row2.locator('input').nth(2).fill('100%')
    await selectInRow(row2, '定量计数')
    await row2.locator('textarea').fill('按态度评价计分')

    await expect(page.locator('.el-tag').filter({ hasText: '权重合计: 100% (正确)' })).toBeVisible()

    await page.getByRole('button', { name: '保存' }).click()
    await page.waitForURL('**/kpi-templates')
    await expect(page.locator('h2').filter({ hasText: 'KPI 模板管理' })).toBeVisible()

    await expect(page.locator('.el-table__body').getByText('工作业绩')).toBeVisible()
    await expect(page.locator('.el-table__body').getByText('工作能力')).toBeVisible()
    await expect(page.locator('.el-table__body').getByText('工作态度')).toBeVisible()
  })

  test('权重合计 ≠ 100% 时保存按钮禁用', async ({ page }) => {
    await page.goto('/kpi-templates/create')
    await page.waitForLoadState('networkidle')

    const positionSelect = page.locator('.el-form-item').filter({ hasText: '关联岗位' }).locator('.el-select').first()
    await positionSelect.click()
    await page.getByRole('option', { name: '系统管理员' }).last().click()

    await page.locator('.el-table tbody tr').nth(0).locator('input').nth(0).fill('指标A')
    await page.locator('.el-table tbody tr').nth(0).locator('.el-input-number input').fill('50')

    await expect(page.locator('.el-tag').filter({ hasText: '权重合计: 50% (应为100%)' })).toBeVisible()
    const saveBtn = page.getByRole('button', { name: '保存' })
    await expect(saveBtn).toBeDisabled()
  })

  test('编辑模板 — 加载数据并修改保存', async ({ page }) => {
    await page.goto('/kpi-templates')
    await page.waitForLoadState('networkidle')

    const rows = page.locator('.el-table__body tbody tr')
    const count = await rows.count()
    test.skip(count === 0, '列表无模板数据，跳过编辑测试')

    await rows.nth(0).getByRole('button', { name: '编辑' }).click()
    await page.waitForURL(/\/kpi-templates\/\d+\/edit/)
    await expect(page.locator('h2').filter({ hasText: '编辑 KPI 模板' })).toBeVisible()

    await expect(page.locator('.el-select').first()).toHaveClass(/is-disabled/)

    const editTable = page.locator('.el-table')
    await expect(editTable.locator('tbody tr').first().locator('input').nth(0)).toHaveValue(/.+/)

    const firstWeight = editTable.locator('tbody tr').nth(0).locator('.el-input-number input')
    const currentWeight = await firstWeight.inputValue()
    await firstWeight.fill('1')
    await firstWeight.fill(String(currentWeight))

    await page.getByRole('button', { name: '保存' }).click()
    await page.waitForURL('**/kpi-templates')
    await expect(page.locator('h2').filter({ hasText: 'KPI 模板管理' })).toBeVisible()
  })

  test('复制模板 — 列表出现副本', async ({ page }) => {
    await page.goto('/kpi-templates')
    await page.waitForLoadState('networkidle')

    const rows = page.locator('.el-table__body tbody tr')
    const count = await rows.count()
    test.skip(count === 0, '列表无模板数据，跳过复制测试')

    const firstRowName = await rows.nth(0).locator('td').nth(1).textContent()

    await rows.nth(0).getByRole('button', { name: '复制' }).click()
    await page.getByRole('dialog').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '复制成功')

    await page.waitForTimeout(500)
    await expect(page.locator('.el-table__body').getByText(`${firstRowName}-副本`)).toBeVisible()
  })

  test('删除指标行时至少保留一个', async ({ page }) => {
    await page.goto('/kpi-templates/create')
    await page.waitForLoadState('networkidle')

    const positionSelect = page.locator('.el-form-item').filter({ hasText: '关联岗位' }).locator('.el-select').first()
    await positionSelect.click()
    await page.getByRole('option', { name: '系统管理员' }).last().click()

    const table = page.locator('.el-table')
    await expect(table.locator('tbody tr')).toHaveCount(1)

    await table.locator('tbody tr').nth(0).getByRole('button', { name: '删除' }).click()
    await expectToast(page, '至少需要保留一个指标')

    await expect(table.locator('tbody tr')).toHaveCount(1)
  })
})