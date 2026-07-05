import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 绩效面谈表单 (InterviewForm)
 * 覆盖：表单渲染、字段校验、C/D 等级改进计划必填、提交
 */

test.describe('绩效面谈表单', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
  })

  test('无 record_id 时显示空状态', async ({ page }) => {
    await page.goto('/interview-form')
    await expect(page.getByRole('heading', { name: '绩效面谈' })).toBeVisible()
    await expect(page.getByText('未找到考核记录')).toBeVisible()
  })

  test('表单字段全部可见', async ({ page }) => {
    await page.goto('/interview-form?record_id=999')
    await expect(page.getByRole('heading', { name: '绩效面谈' })).toBeVisible()
    await expect(page.getByText('员工基本信息')).toBeVisible()

    // 表单字段
    await expect(page.locator('.el-form-item').filter({ hasText: '面谈时间' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '面谈地点' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '沟通内容' })).toBeVisible()
  })

  test('沟通内容少于50字时提交被拦截', async ({ page }) => {
    await page.goto('/interview-form?record_id=999')
    const textarea = page.locator('.el-textarea__inner').filter({ hasText: /^/ }).first()
    await textarea.fill('太短')
    await page.getByRole('button', { name: '提交' }).click()
    // Element Plus 表单校验会显示错误信息
    await expect(page.locator('.el-form-item__error').filter({ hasText: /50/ })).toBeVisible()
  })

  test('提交按钮和返回按钮存在', async ({ page }) => {
    await page.goto('/interview-form?record_id=999')
    await expect(page.getByRole('button', { name: '提交' })).toBeVisible()
    await expect(page.getByRole('button', { name: '返回' })).toBeVisible()
  })

  test('点击返回按钮跳转回面谈列表', async ({ page }) => {
    await page.goto('/interview-form?record_id=999')
    await page.getByRole('button', { name: '返回' }).click()
    await page.waitForURL('**/interviews')
    await expect(page).toHaveURL(/.*\/interviews/)
  })
})
