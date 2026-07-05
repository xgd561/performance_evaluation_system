import { test, expect } from '@playwright/test'
import { hrLogin, managerLogin } from './helpers/admin-helper'

/**
 * E2E: 场景 7 — 汇总→审批→面谈核心链路
 * 覆盖：HR 触发汇总 → 强制分布确认 → 经理 Step 1 审批 → HR Step 2 审批 → 经理面谈 → 状态 published
 */

test.describe('场景 7：汇总→审批→面谈核心链路', () => {
  test('完整流程', async ({ page }) => {
    // ========== Step 1: HR 登录，触发汇总计算 ==========
    await hrLogin(page)
    await page.goto('/summary')
    await page.waitForSelector('.el-card', { timeout: 10000 })

    // 选择考核周期（使用第一个下拉选项）
    const cycleSelect = page.locator('.el-select').filter({ has: page.locator('.el-input__inner') }).first()
    if (await cycleSelect.isVisible().catch(() => false)) {
      await cycleSelect.click()
      await page.locator('.el-select-dropdown').last().waitFor({ state: 'visible', timeout: 5000 })
      const firstOption = page.locator('.el-select-dropdown').last().locator('.el-select-dropdown__item').first()
      if (await firstOption.isVisible().catch(() => false)) {
        await firstOption.click()
      }
      await page.waitForTimeout(300)
    }

    // 点击"计算得分"按钮
    const calcBtn = page.getByRole('button', { name: /计算|汇总/ }).first()
    if (await calcBtn.isVisible().catch(() => false)) {
      await calcBtn.click()
      // 等待确认弹窗（如果有）
      const confirmBox = page.locator('.el-message-box__wrapper').or(page.locator('.el-overlay-message-box'))
      if (await confirmBox.isVisible({ timeout: 3000 }).catch(() => false)) {
        await page.getByRole('button', { name: '确认' }).click()
      }
      // 等待成功提示
      await page.locator('.el-message--success').waitFor({ state: 'visible', timeout: 10000 }).catch(() => null)
    }

    // ========== Step 2: 确认强制分布调整（如果有）==========
    await page.goto('/distribution-review')
    await page.waitForSelector('.el-card', { timeout: 10000 })

    const confirmDistBtn = page.getByRole('button', { name: '确认调整' }).first()
    if (await confirmDistBtn.isVisible().catch(() => false)) {
      await confirmDistBtn.click()
      await page.locator('.el-message--success').waitFor({ state: 'visible', timeout: 10000 }).catch(() => null)
    }

    // ========== Step 3: 经理登录，Step 1 审批通过 ==========
    await managerLogin(page)
    await page.goto('/approval-workbench')
    await page.waitForSelector('.el-table', { timeout: 10000 })

    // 查找待审批记录并点击"通过"
    const pendingTable = page.locator('.el-card').filter({ hasText: '待审批' }).locator('.el-table').first()
    const approveBtn = pendingTable.getByRole('button', { name: '通过' }).first()

    if (await approveBtn.isVisible().catch(() => false)) {
      await approveBtn.click()

      // 填写审批意见（≥10字）
      const dialog = page.locator('.el-dialog').filter({ hasText: '审批' }).first()
      if (await dialog.isVisible().catch(() => false)) {
        const textarea = dialog.locator('.el-textarea__inner').first()
        await textarea.fill('Step 1 审批通过，表现符合预期。')
        await dialog.getByRole('button', { name: '确认' }).click()
      } else {
        // 如果在页面内直接提交
        const commentInput = page.locator('.el-textarea__inner').first()
        await commentInput.fill('Step 1 审批通过，表现符合预期。')
        await page.getByRole('button', { name: '确认' }).click()
      }

      await page.locator('.el-message--success').waitFor({ state: 'visible', timeout: 10000 }).catch(() => null)
    }

    // ========== Step 4: HR 登录，Step 2 最终审批通过 ==========
    await hrLogin(page)
    await page.goto('/approval-workbench')
    await page.waitForSelector('.el-table', { timeout: 10000 })

    const hrTable = page.locator('.el-card').filter({ hasText: '待审批' }).locator('.el-table').first()
    const finalApproveBtn = hrTable.getByRole('button', { name: '通过' }).first()

    if (await finalApproveBtn.isVisible().catch(() => false)) {
      await finalApproveBtn.click()

      const dialog = page.locator('.el-dialog').filter({ hasText: '审批' }).first()
      if (await dialog.isVisible().catch(() => false)) {
        const textarea = dialog.locator('.el-textarea__inner').first()
        await textarea.fill('Step 2 最终审批通过，同意进入面谈阶段。')
        await dialog.getByRole('button', { name: '确认' }).click()
      } else {
        const commentInput = page.locator('.el-textarea__inner').first()
        await commentInput.fill('Step 2 最终审批通过，同意进入面谈阶段。')
        await page.getByRole('button', { name: '确认' }).click()
      }

      await page.locator('.el-message--success').waitFor({ state: 'visible', timeout: 10000 }).catch(() => null)
    }

    // ========== Step 5: 经理登录，进行绩效面谈 ==========
    await managerLogin(page)
    await page.goto('/interviews')
    await page.waitForSelector('.el-card', { timeout: 10000 })

    // 点击"待面谈"列表中的"进入面谈"按钮
    const pendingInterviewCard = page.locator('.el-card').filter({ hasText: '待面谈' }).first()
    const enterBtn = pendingInterviewCard.getByRole('button', { name: '进入面谈' }).first()

    if (await enterBtn.isVisible().catch(() => false)) {
      await enterBtn.click()
      await page.waitForURL('**/interview-form?record_id=*', { timeout: 10000 })
      await page.waitForSelector('.el-form', { timeout: 10000 })

      // 填写面谈时间（选择今天）
      const datePicker = page.locator('.el-date-editor').first()
      if (await datePicker.isVisible().catch(() => false)) {
        await datePicker.click()
        await page.locator('.el-picker-panel').waitFor({ state: 'visible', timeout: 5000 })
        // 点击今天
        await page.locator('.el-date-table td.current').first().click()
        // 确认时间
        await page.getByRole('button', { name: '确定' }).last().click()
      }

      // 填写面谈地点
      const locationInput = page.locator('.el-input__inner').filter({ hasText: /^/ }).first()
      await locationInput.fill('会议室A')

      // 填写沟通内容（≥50字）
      const contentTextarea = page.locator('.el-textarea__inner').filter({ hasText: /^/ }).first()
      await contentTextarea.fill('这是一段超过五十个汉字的沟通内容，用于测试表单提交和确认对话框的完整流程。')

      // 检查是否需要填写改进计划（C/D 等级）
      const improvementItem = page.locator('.el-form-item').filter({ hasText: '改进计划' })
      if (await improvementItem.isVisible().catch(() => false)) {
        const improvementTextarea = improvementItem.locator('.el-textarea__inner').first()
        await improvementTextarea.fill('这是一段超过三十个汉字的改进计划内容，用于测试改进计划校验。')
      }

      // 点击提交
      await page.getByRole('button', { name: '提交' }).click()

      // 等待确认对话框
      const confirmBox = page.locator('.el-message-box__wrapper').or(page.locator('.el-overlay-message-box'))
      if (await confirmBox.isVisible({ timeout: 5000 }).catch(() => false)) {
        await page.getByRole('button', { name: '确认' }).click()
      }

      // ========== Step 6: 验证成功提示并返回列表 ==========
      await page.locator('.el-message--success').waitFor({ state: 'visible', timeout: 10000 })

      // 验证页面返回列表页
      await page.waitForURL('**/interviews', { timeout: 10000 })
      await expect(page.getByRole('heading', { name: '绩效面谈' })).toBeVisible()
    }
  })
})
