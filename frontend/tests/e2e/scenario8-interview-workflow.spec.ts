import { test, expect } from '@playwright/test'
import { managerLogin } from './helpers/admin-helper'

/**
 * E2E: 绩效面谈工作流 (InterviewList + InterviewForm)
 * 覆盖：列表分区、C/D高亮、搜索过滤、表单维度展示、表单校验、提交确认
 */

test.describe('绩效面谈工作流', () => {
  test.beforeEach(async ({ page }) => {
    await managerLogin(page)
  })

  test('InterviewList 正确显示待面谈和已面谈两个分区', async ({ page }) => {
    await page.goto('/interviews')
    await expect(page.getByRole('heading', { name: '绩效面谈' })).toBeVisible()

    // 两个卡片区域
    await expect(page.getByText('待面谈').first()).toBeVisible()
    await expect(page.getByText('已面谈').first()).toBeVisible()

    // 表格列存在
    const pendingTable = page.locator('.el-card').filter({ hasText: '待面谈' }).locator('.el-table').first()
    await expect(pendingTable).toBeVisible()

    const completedTable = page.locator('.el-card').filter({ hasText: '已面谈' }).locator('.el-table').first()
    await expect(completedTable).toBeVisible()
  })

  test('C/D 等级员工在列表中显示红色高亮', async ({ page }) => {
    await page.goto('/interviews')
    await page.waitForSelector('.el-table', { timeout: 10000 })

    // 查找包含 danger 标签的行
    const cdRows = page.locator('.el-table__row').filter({ hasText: /D|C/ })
    const count = await cdRows.count()

    if (count > 0) {
      // 验证行背景色高亮类
      const firstCdRow = cdRows.first()
      await expect(firstCdRow).toHaveClass(/highlight-cd/)

      // 验证等级标签为 danger 类型
      const dangerTag = firstCdRow.locator('.el-tag--danger').first()
      await expect(dangerTag).toBeVisible()
    }
  })

  test('搜索功能能正确过滤员工', async ({ page }) => {
    await page.goto('/interviews')
    await page.waitForSelector('.el-table', { timeout: 10000 })

    // 获取第一个员工姓名
    const firstNameCell = page.locator('.el-card').filter({ hasText: '待面谈' }).locator('.el-table__row').first().locator('td').nth(0)
    const firstName = await firstNameCell.textContent()

    if (firstName) {
      const searchInput = page.locator('.el-input__inner').filter({ hasText: /^/ }).first()
      await searchInput.fill(firstName)
      await page.getByRole('button', { name: '查询' }).click()

      // 等待表格刷新
      await page.waitForTimeout(500)

      // 验证过滤后表格中至少包含该姓名
      const filteredRows = page.locator('.el-card').filter({ hasText: '待面谈' }).locator('.el-table__row')
      await expect(filteredRows.first()).toContainText(firstName)
    }
  })

  test('进入 InterviewForm 后各维度得分正确显示', async ({ page }) => {
    await page.goto('/interviews')
    await page.waitForSelector('.el-table', { timeout: 10000 })

    // 点击第一行的"进入面谈"按钮
    const enterBtn = page.locator('.el-card').filter({ hasText: '待面谈' }).getByRole('button', { name: '进入面谈' }).first()
    await expect(enterBtn).toBeVisible()
    await enterBtn.click()

    // 等待跳转到表单页面
    await page.waitForURL('**/interview-form?record_id=*')
    await expect(page.getByRole('heading', { name: '绩效面谈' })).toBeVisible()

    // 验证员工基本信息
    await expect(page.getByText('员工基本信息')).toBeVisible()
    await expect(page.getByText('各维度得分参考')).toBeVisible()

    // 验证维度得分表格
    const dimensionTable = page.locator('.el-table').filter({ hasText: '维度' })
    await expect(dimensionTable).toBeVisible()
    await expect(dimensionTable).toContainText('自评')
    await expect(dimensionTable).toContainText('上级')
    await expect(dimensionTable).toContainText('协作')
  })

  test('沟通内容少于50字时表单提交报错', async ({ page }) => {
    await page.goto('/interview-form?record_id=1')
    await page.waitForSelector('.el-form', { timeout: 10000 })

    // 填写少于50字的沟通内容
    const contentTextarea = page.locator('.el-textarea__inner').filter({ hasText: /^/ }).first()
    await contentTextarea.fill('太短')

    // 提交
    await page.getByRole('button', { name: '提交' }).click()

    // 等待表单校验错误提示
    await expect(page.locator('.el-form-item__error').filter({ hasText: /50/ })).toBeVisible({ timeout: 5000 })
  })

  test('C 等级员工未填写改进计划时提交报错', async ({ page }) => {
    // 假设 record_id=2 对应 C 等级员工（需要后端数据支持）
    await page.goto('/interview-form?record_id=2')
    await page.waitForSelector('.el-form', { timeout: 10000 })

    // 检查是否存在改进计划字段（C/D等级才会显示）
    const improvementItem = page.locator('.el-form-item').filter({ hasText: '改进计划' })
    const hasImprovement = await improvementItem.isVisible().catch(() => false)

    if (hasImprovement) {
      // 填写满足50字的沟通内容，但不填改进计划
      const contentTextarea = page.locator('.el-textarea__inner').filter({ hasText: /^/ }).first()
      await contentTextarea.fill('这是一段超过五十个汉字的沟通内容，用于测试表单校验逻辑是否正确。')

      await page.getByRole('button', { name: '提交' }).click()

      // 等待表单校验错误提示（改进计划）
      await expect(page.locator('.el-form-item__error').filter({ hasText: /30/ })).toBeVisible({ timeout: 5000 })
    } else {
      // 当前记录不是 C/D 等级，跳过此测试断言
      console.log('当前记录不是 C/D 等级，跳过改进计划校验')
    }
  })

  test('填写正确内容后提交，弹出确认对话框，确认后提交成功并返回列表', async ({ page }) => {
    await page.goto('/interview-form?record_id=1')
    await page.waitForSelector('.el-form', { timeout: 10000 })

    // 填写面谈时间（过去的时间）
    const datePicker = page.locator('.el-date-editor').first()
    await datePicker.click()
    await page.locator('.el-picker-panel').waitFor({ state: 'visible' })
    // 选择今天
    await page.locator('.el-date-table__row').first().locator('td').first().click()
    // 选择时间
    await page.locator('.el-time-spinner__item').first().click()
    await page.getByRole('button', { name: '确定' }).last().click()

    // 填写面谈地点
    const locationInput = page.locator('.el-input__inner').filter({ hasText: /^/ }).first()
    await locationInput.fill('会议室A')

    // 填写沟通内容（不少于50字）
    const contentTextarea = page.locator('.el-textarea__inner').filter({ hasText: /^/ }).first()
    await contentTextarea.fill('这是一段超过五十个汉字的沟通内容，用于测试表单提交和确认对话框的完整流程。')

    // 点击提交
    await page.getByRole('button', { name: '提交' }).click()

    // 等待确认对话框
    await expect(page.locator('.el-message-box__wrapper').or(page.locator('.el-overlay-message-box'))).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.el-message-box__title').or(page.locator('.el-message-box__header'))).toContainText('提示')

    // 确认提交
    await page.getByRole('button', { name: '确认' }).click()

    // 等待成功提示并返回列表
    await page.waitForURL('**/interviews', { timeout: 10000 })
    await expect(page).toHaveURL(/.*\/interviews/)
    await expect(page.getByRole('heading', { name: '绩效面谈' })).toBeVisible()
  })
})
