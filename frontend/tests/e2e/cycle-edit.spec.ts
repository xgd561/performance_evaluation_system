import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 考核周期编辑/新增 (CycleEdit)
 * 覆盖：表单渲染、日期校验、类型选择、保存
 */

test.describe('考核周期编辑页', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
  })

  test('新增模式页面标题和表单字段可见', async ({ page }) => {
    await page.goto('/cycles/edit')
    await expect(page.getByRole('heading', { name: '新增考核周期' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '周期名称' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '考核类型' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '开始日期' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '结束日期' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '自评截止' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '上级评分截止' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '是否启用' })).toBeVisible()
  })

  test('编辑模式页面标题为编辑考核周期', async ({ page }) => {
    await page.goto('/cycles/edit?id=1&name=2026Q1')
    await expect(page.getByRole('heading', { name: '编辑考核周期' })).toBeVisible()
  })

  test('必填字段为空时提交被拦截', async ({ page }) => {
    await page.goto('/cycles/edit')
    await page.getByRole('button', { name: '保存' }).click()
    await expect(page.locator('.el-form-item__error').filter({ hasText: '周期名称不能为空' })).toBeVisible()
  })

  test('考核类型单选按钮存在', async ({ page }) => {
    await page.goto('/cycles/edit')
    await expect(page.getByText('季度')).toBeVisible()
    await expect(page.getByText('年度')).toBeVisible()
  })

  test('是否启用开关存在且可交互', async ({ page }) => {
    await page.goto('/cycles/edit')
    const switchBtn = page.locator('.el-switch').first()
    await expect(switchBtn).toBeVisible()
    // 获取当前状态
    const isChecked = await switchBtn.locator('input').isChecked()
    await switchBtn.click()
    await expect(switchBtn.locator('input')).toBeChecked({ checked: !isChecked })
  })

  test('取消按钮跳转回周期列表', async ({ page }) => {
    await page.goto('/cycles/edit')
    await page.getByRole('button', { name: '取消' }).click()
    await page.waitForURL('**/cycles')
    await expect(page).toHaveURL(/.*\/cycles/)
  })
})
