import { test, expect } from '@playwright/test'
import { executiveLogin, employeeLogin } from './helpers/approval-helper'

/**
 * E2E: 高管仪表盘 (ExecutiveDashboard)
 * 覆盖：统计卡片、饼图、柱状图、折线图、强制调整列表
 */

test.describe('高管仪表盘', () => {
  test.beforeEach(async ({ page }) => {
    await executiveLogin(page)
  })

  test('页面显示高管仪表盘标题', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.getByText('部门筛选')).toBeVisible()
  })

  test('包含 4 个统计卡片', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.getByText('员工总数')).toBeVisible()
    await expect(page.getByText('考核覆盖率')).toBeVisible()
    await expect(page.getByText('公司平均总分')).toBeVisible()
    await expect(page.getByText('待审批数')).toBeVisible()
  })

  test('包含图表区（饼图+柱状图+折线图）', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.getByText('绩效分布')).toBeVisible()
    await expect(page.getByText('部门平均分对比')).toBeVisible()
    await expect(page.getByText('近 4 季度绩效趋势')).toBeVisible()
  })

  test('包含强制调整人员列表', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.getByText('强制调整人员列表')).toBeVisible()
  })

  test('无评分/审批/配置操作按钮', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.getByRole('button', { name: '评分' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '审批' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '配置' })).toHaveCount(0)
  })
})

test.describe('非高管角色访问', () => {
  test('employee 不显示 executive 仪表盘', async ({ page }) => {
    await employeeLogin(page)
    await page.goto('/dashboard')
    await expect(page.getByText('高管数据视图')).toHaveCount(0)
    await expect(page.getByText('我的绩效首页')).toBeVisible()
  })
})
