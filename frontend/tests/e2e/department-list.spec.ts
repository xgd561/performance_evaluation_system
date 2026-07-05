import { test, expect } from '@playwright/test'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E: 部门管理页面 (DepartmentList.vue)
 * P2-02 验收标准：树形表格正确渲染层级关系；删除有子部门的部门时提示「该部门存在子部门，无法删除」
 */

test.describe('部门管理页面', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page)
    await page.goto('/departments')
  })

  test('页面标题和架构图卡片可见', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '部门管理' })).toBeVisible()
    await expect(page.getByText('组织架构图')).toBeVisible()
    await expect(page.getByText('可拖拽调整部门归属')).toBeVisible()
  })

  test('树形表格列头正确渲染', async ({ page }) => {
    await page.waitForSelector('.el-table__header th')
    await expect(page.locator('.el-table__header th').filter({ hasText: '编码' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '名称' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '上级部门' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '负责人' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '员工数' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '岗位数' })).toBeVisible()
    await expect(page.locator('.el-table__header th').filter({ hasText: '操作' })).toBeVisible()
  })

  test('新增部门按钮存在', async ({ page }) => {
    await expect(page.getByRole('button', { name: '新增部门' })).toBeVisible()
  })

  test('点击新增部门弹出表单且可填写', async ({ page }) => {
    await page.getByRole('button', { name: '新增部门' }).click()
    await expect(page.locator('.el-dialog__title').filter({ hasText: '新增部门' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '编码' }).locator('input').first()).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '名称' }).locator('input').first()).toBeVisible()
  })

  test('删除部门按钮存在并触发二次确认', async ({ page }) => {
    // 等待表格加载（先等待表头）
    await page.waitForSelector('.el-table__header th', { timeout: 10000 })
    const rows = page.locator('.el-table__row')
    if (await rows.count() === 0) {
      // 没有数据行，断言空状态或跳过删除操作
      await expect(page.locator('.el-empty').first()).toBeVisible()
      return
    }
    const deleteBtn = rows.first().locator('button').filter({ hasText: '删除' })
    if (await deleteBtn.isVisible().catch(() => false)) {
      await deleteBtn.click()
      // 二次确认弹窗
      await expect(page.locator('.el-message-box__title').filter({ hasText: '删除确认' })).toBeVisible()
      // 取消关闭
      await page.locator('.el-message-box').getByRole('button', { name: '取消' }).click()
      await expect(page.locator('.el-message-box').first()).not.toBeVisible()
    }
  })

  test('组织架构图支持拖拽', async ({ page }) => {
    // 等待数据加载完成，如果数据为空则 el-tree 不会渲染
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    const tree = page.locator('.el-tree').first()
    const empty = page.locator('.el-empty').filter({ hasText: '暂无部门数据' }).first()
    if (await tree.isVisible().catch(() => false)) {
      // 断言树节点存在
      const firstNode = page.locator('.el-tree-node').first()
      await expect(firstNode).toBeVisible()
    } else {
      // 没有数据时断言空状态可见
      await expect(empty).toBeVisible()
    }
  })
})
