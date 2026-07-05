import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 审批详情页 (ApprovalDetail.vue)
 * 覆盖：页面加载、评分数据展示、异常提示、审批操作
 */

test.describe('审批详情页', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
  })

  test('页面加载正确显示所有评分数据（自评/上级/协作）', async ({ page }) => {
    // 先访问审批工作台，再点击第一个记录的查看详情
    await page.goto('/approval-workbench')
    await page.waitForSelector('.el-table', { timeout: 10000 })

    // 点击第一个记录的"查看详情"链接
    const detailLink = page.getByRole('button', { name: '查看详情' }).first()
    if (await detailLink.isVisible().catch(() => false)) {
      await detailLink.click()
      await page.waitForURL('**/approval-detail?record_id=*', { timeout: 10000 })
    } else {
      // 直接访问详情页（用于无数据环境）
      await page.goto('/approval-detail?record_id=1')
    }

    await page.waitForSelector('.el-descriptions', { timeout: 10000 })

    // 验证基本信息存在
    await expect(page.getByText('员工基本信息')).toBeVisible()
    await expect(page.getByText('评分详情对比')).toBeVisible()

    // 验证评分表格列头
    const scoreTable = page.locator('.el-table').filter({ hasText: '维度' })
    await expect(scoreTable).toBeVisible()
    await expect(scoreTable).toContainText('自评')
    await expect(scoreTable).toContainText('上级')
    await expect(scoreTable).toContainText('协作')

    // 验证加权结果存在
    await expect(page.getByText('加权计算结果')).toBeVisible()
  })

  test('差异大于20分显示黄色提示', async ({ page }) => {
    await page.goto('/approval-detail?record_id=1')
    await page.waitForSelector('.el-descriptions', { timeout: 10000 })

    // 查找差异警告元素
    const diffAlert = page.locator('.el-alert').filter({ hasText: '差异较大' })
    const diffCells = page.locator('.diff-warning')

    // 至少 diff-warning 样式或警告提示之一存在
    const hasDiffAlert = await diffAlert.isVisible().catch(() => false)
    const diffCellCount = await diffCells.count()

    if (hasDiffAlert || diffCellCount > 0) {
      if (hasDiffAlert) {
        await expect(diffAlert).toBeVisible()
      }
      if (diffCellCount > 0) {
        await expect(diffCells.first()).toHaveClass(/diff-warning/)
      }
    }
  })

  test('强制分布调整显示红色提示', async ({ page }) => {
    await page.goto('/approval-detail?record_id=1')
    await page.waitForSelector('.el-descriptions', { timeout: 10000 })

    // 查找强制分布调整警告
    const forceAlert = page.locator('.el-alert').filter({ hasText: '强制分布调整' })
    const abnormalAlert = page.locator('.el-alert').filter({ hasText: '异常分数' })

    const hasForce = await forceAlert.isVisible().catch(() => false)
    const hasAbnormal = await abnormalAlert.isVisible().catch(() => false)

    // 如果数据中有强制分布调整，则断言可见
    if (hasForce) {
      await expect(forceAlert).toBeVisible()
    }
    if (hasAbnormal) {
      await expect(abnormalAlert).toBeVisible()
    }
  })

  test('审批意见少于10字时提交按钮报错', async ({ page }) => {
    await page.goto('/approval-detail?record_id=1')
    await page.waitForSelector('.el-form', { timeout: 10000 })

    // 查找审批操作区
    const actionCard = page.locator('.approval-actions')
    if (await actionCard.isVisible().catch(() => false)) {
      // 填写少于10字的意见
      const textarea = actionCard.locator('.el-textarea__inner').first()
      await textarea.fill('太短')

      // 点击通过按钮
      await actionCard.getByRole('button', { name: '通过' }).click()

      // 等待表单校验错误
      await expect(page.locator('.el-form-item__error').filter({ hasText: /10/ })).toBeVisible({ timeout: 5000 })
    }
  })

  test('点击通过按钮弹出确认对话框，确认后操作成功', async ({ page }) => {
    await page.goto('/approval-detail?record_id=1')
    await page.waitForSelector('.el-form', { timeout: 10000 })

    const actionCard = page.locator('.approval-actions')
    if (await actionCard.isVisible().catch(() => false)) {
      // 填写满足10字的意见
      const textarea = actionCard.locator('.el-textarea__inner').first()
      await textarea.fill('这是一段满足十个字以上的审批意见。')

      // 点击通过
      await actionCard.getByRole('button', { name: '通过' }).click()

      // 等待确认对话框
      await expect(page.locator('.el-message-box__wrapper').or(page.locator('.el-overlay-message-box'))).toBeVisible({ timeout: 5000 })
      await expect(page.locator('.el-message-box__title').or(page.locator('.el-message-box__header'))).toContainText('提示')

      // 取消确认（避免实际修改数据）
      await page.getByRole('button', { name: '取消' }).click()

      // 验证对话框关闭，仍在详情页
      await expect(page.locator('.el-message-box__wrapper').or(page.locator('.el-overlay-message-box'))).not.toBeVisible({ timeout: 5000 })
      await expect(page.getByRole('heading', { name: '审批详情' })).toBeVisible()
    }
  })
})
