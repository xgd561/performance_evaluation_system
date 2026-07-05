import { test, expect } from '@playwright/test'
import { adminLogin, uniqueId } from './helpers/admin-helper'

/**
 * E2E: 员工编辑/新增 (EmployeeEdit)
 * 覆盖：表单渲染、字段必填校验、新增/编辑模式、保存
 */

test.describe('员工编辑页', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
  })

  test('新增模式页面标题和表单字段可见', async ({ page }) => {
    await page.goto('/employees/edit')
    await expect(page.getByRole('heading', { name: '新增员工' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '姓名' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '工号' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '部门' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '岗位' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '职级' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '入职日期' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '状态' })).toBeVisible()
  })

  test('编辑模式页面标题为编辑员工', async ({ page }) => {
    await page.goto('/employees/edit?id=1&name=张三&employee_no=E001')
    await expect(page.getByRole('heading', { name: '编辑员工' })).toBeVisible()
  })

  test('工号字段在编辑模式下禁用', async ({ page }) => {
    await page.goto('/employees/edit?id=1&name=张三&employee_no=E001')
    const input = page.locator('.el-form-item').filter({ hasText: '工号' }).locator('input').first()
    await expect(input).toBeDisabled()
  })

  test('必填字段为空时提交被拦截', async ({ page }) => {
    await page.goto('/employees/edit')
    await page.getByRole('button', { name: '保存' }).click()
    await expect(page.locator('.el-form-item__error').filter({ hasText: '姓名不能为空' })).toBeVisible()
    await expect(page.locator('.el-form-item__error').filter({ hasText: '工号不能为空' })).toBeVisible()
  })

  test('取消按钮跳转回员工列表', async ({ page }) => {
    await page.goto('/employees/edit')
    await page.getByRole('button', { name: '取消' }).click()
    await page.waitForURL('**/employees')
    await expect(page).toHaveURL(/.*\/employees/)
  })
})
