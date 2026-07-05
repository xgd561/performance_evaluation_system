import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 考核周期列表页 (CycleList)
 * 覆盖：表格渲染、筛选栏、分页、操作按钮、详情弹窗
 */

test.describe('考核周期列表页', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
    await page.goto('/cycles')
  })

  test('页面标题和表格列可见', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '考核周期管理' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '名称' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '类型' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '开始日期' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '结束日期' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '自评截止' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '上级评截止' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '协作评截止' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '考核对象' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '状态' })).toBeVisible()
    await expect(page.locator('th .cell').filter({ hasText: '操作' })).toBeVisible()
  })

  test('筛选栏存在且可交互', async ({ page }) => {
    await expect(page.locator('.filter-bar').first()).toBeVisible()
    const statusSelect = page.locator('.filter-bar .el-select').nth(0)
    await expect(statusSelect).toBeVisible()
    const typeSelect = page.locator('.filter-bar .el-select').nth(1)
    await expect(typeSelect).toBeVisible()
    await expect(page.getByRole('button', { name: '查询' })).toBeVisible()
    await expect(page.getByRole('button', { name: '重置' })).toBeVisible()
  })

  test('新增周期按钮存在', async ({ page }) => {
    await expect(page.getByRole('button', { name: '新增周期' })).toBeVisible()
  })

  test('表格数据行存在', async ({ page }) => {
    const firstRow = page.locator('.el-table__row').first()
    await expect(firstRow).toBeVisible()
  })

  test('已发布状态行仅显示查看详情按钮', async ({ page }) => {
    const rows = page.locator('.el-table__row')
    const count = await rows.count()
    for (let i = 0; i < count; i++) {
      const statusCell = rows.nth(i).locator('.el-tag').first()
      const text = await statusCell.textContent()
      if (text?.includes('已发布') || text?.includes('已归档')) {
        const actionsCell = rows.nth(i).locator('td').last()
        await expect(actionsCell.getByRole('button', { name: '查看详情' })).toBeVisible()
        await expect(actionsCell.getByRole('button', { name: '编辑' })).not.toBeVisible()
        await expect(actionsCell.getByRole('button', { name: '删除' })).not.toBeVisible()
        break
      }
    }
  })

  test('未开始状态行显示编辑、启动、删除按钮', async ({ page }) => {
    const rows = page.locator('.el-table__row')
    const count = await rows.count()
    for (let i = 0; i < count; i++) {
      const statusCell = rows.nth(i).locator('.el-tag').first()
      const text = await statusCell.textContent()
      if (text?.includes('未开始')) {
        const actionsCell = rows.nth(i).locator('td').last()
        await expect(actionsCell.getByRole('button', { name: '编辑' })).toBeVisible()
        await expect(actionsCell.getByRole('button', { name: '启动' })).toBeVisible()
        await expect(actionsCell.getByRole('button', { name: '删除' })).toBeVisible()
        break
      }
    }
  })

  test('详情弹窗可打开并显示周期信息', async ({ page }) => {
    await page.locator('.el-table__row').first().getByRole('button', { name: '查看' }).click()
    const dialog = page.locator('.el-dialog').filter({ hasText: '考核周期详情' })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('名称')).toBeVisible()
    await expect(dialog.getByText('类型')).toBeVisible()
    await expect(dialog.getByText('开始日期')).toBeVisible()
    await expect(dialog.getByText('结束日期')).toBeVisible()
  })

  test('分页组件存在', async ({ page }) => {
    await expect(page.locator('.el-pagination')).toBeVisible()
  })
})
