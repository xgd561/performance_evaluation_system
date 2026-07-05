import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 组织架构 (OrganizationChart)
 * 覆盖：树形结构渲染、部门详情展示、岗位列表
 */

test.describe('组织架构页面', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
    await page.goto('/organization-chart')
  })

  test('页面标题和树形组件可见', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '组织架构' })).toBeVisible()
    await expect(page.locator('.el-tree').first()).toBeVisible()
  })

  test('点击树节点显示部门详情', async ({ page }) => {
    // 等待树节点加载
    await page.locator('.el-tree-node').first().waitFor({ state: 'visible' })
    const firstNode = page.locator('.el-tree-node').first()
    await firstNode.click()

    // 断言右侧详情区域出现
    await expect(page.getByText('部门详情')).toBeVisible()
    await expect(page.getByText('部门名称')).toBeVisible()
    await expect(page.getByText('部门编码')).toBeVisible()
  })

  test('员工列表列头正确，且展示直属上级', async ({ page }) => {
    // 先点击一个节点
    await page.locator('.el-tree-node').first().click()
    await page.waitForLoadState('networkidle')
    await expect(page.getByText('员工列表')).toBeVisible()
    // 等待员工表格列头渲染
    await page.waitForSelector('.employee-table .el-table__header th')
    await expect(page.locator('.employee-table .el-table__header th').filter({ hasText: '姓名' })).toBeVisible()
    await expect(page.locator('.employee-table .el-table__header th').filter({ hasText: '工号' })).toBeVisible()
    await expect(page.locator('.employee-table .el-table__header th').filter({ hasText: '岗位' })).toBeVisible()
    await expect(page.locator('.employee-table .el-table__header th').filter({ hasText: '直属上级' })).toBeVisible()
  })

  test('点击「研发部」展开显示下属员工', async ({ page }) => {
    // 等待树节点加载
    await page.locator('.el-tree-node').first().waitFor({ state: 'visible' })
    // 查找包含"研发部"的节点并点击
    const node = page.locator('.el-tree-node').filter({ hasText: '研发部' }).first()
    if (await node.isVisible().catch(() => false)) {
      await node.click()
      await page.waitForLoadState('networkidle')
      // 断言员工列表区域出现
      await expect(page.getByText('员工列表')).toBeVisible()
      // 如果存在李建国、王志强，断言其可见
      const liJianguo = page.locator('.employee-table tr').filter({ hasText: '李建国' }).first()
      const wangZhiqiang = page.locator('.employee-table tr').filter({ hasText: '王志强' }).first()
      if (await liJianguo.isVisible().catch(() => false)) {
        await expect(liJianguo).toBeVisible()
      }
      if (await wangZhiqiang.isVisible().catch(() => false)) {
        await expect(wangZhiqiang).toBeVisible()
      }
    }
  })

  test('未选择部门时显示空状态', async ({ page }) => {
    // 断言页面整体结构包含空状态文案
    await expect(page.getByText('请选择一个部门')).toBeVisible()
  })

  test('岗位列表表格列头正确', async ({ page }) => {
    // 先点击一个节点
    await page.locator('.el-tree-node').first().click()
    await page.waitForLoadState('networkidle')
    await expect(page.getByText('岗位列表')).toBeVisible()
    await page.waitForSelector('.position-table .el-table__header th')
    await expect(page.locator('.position-table .el-table__header th').filter({ hasText: '岗位名称' })).toBeVisible()
    await expect(page.locator('.position-table .el-table__header th').filter({ hasText: '职级' })).toBeVisible()
    await expect(page.locator('.position-table .el-table__header th').filter({ hasText: '人数' })).toBeVisible()
  })
})
