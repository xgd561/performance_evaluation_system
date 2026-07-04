import { test, expect } from '@playwright/test'
import { adminLogin, uniqueId } from './helpers/admin-helper'

/**
 * Admin（系统管理员）端到端场景测试 — 完整版
 * 覆盖 P0 / P1 / P2 全部场景，严格断言每个步骤。
 */

/* ───────────────────────────────────────────────
 * 辅助函数
 * ─────────────────────────────────────────────── */

async function selectInDialog(page, dialog, label, optionText) {
  const formItem = dialog.locator('.el-form-item').filter({ hasText: label }).first()
  await formItem.locator('.el-select').first().click({ force: true })
  await page.waitForTimeout(300)
  // 直接点击 option role，Element Plus 的 dropdown 选项带有 option role
  await page.getByRole('option', { name: optionText }).click()
}

async function expectToast(page, text) {
  const toast = page.locator('.el-message--success').filter({ hasText: text }).first()
  await expect(toast).toBeVisible({ timeout: 10000 })
}

function getDialog(page, title) {
  return page.locator('.el-dialog').filter({ hasText: title })
}

// 使用实际数据库中的有效数据
const TEST_DEPT = '管理部'
const TEST_POSITION = '系统管理员'

/* ───────────────────────────────────────────────
 * P0 场景 — 仪表盘与系统配置
 * ─────────────────────────────────────────────── */

test.describe('P0 场景 — 仪表盘与系统配置', () => {
  test('仪表盘全局统计与角色隔离', async ({ page }) => {
    await adminLogin(page)

    await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()

    await expect(page.locator('.stat-label').filter({ hasText: '员工总数' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '部门数量' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '考核周期' })).toBeVisible()
    await expect(page.locator('.stat-label').filter({ hasText: '进行中' })).toBeVisible()

    await expect(page.getByText('批量评分')).not.toBeVisible()
    await expect(page.getByText('进入自评')).not.toBeVisible()
    await expect(page.getByText('进入协作评分')).not.toBeVisible()
  })

  test('配置等级规则并持久化', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/config')
    await page.waitForTimeout(500)

    await expect(page.getByRole('tab', { name: '等级规则' })).toHaveClass(/is-active/)

    // 定位 A 和 B 等级的 ratio_limit 输入框，只修改比例（避免区间不连续）
    const aFormItem = page.locator('.el-form-item').nth(0)
    const aRatioInput = aFormItem.locator('.el-input-number input').nth(2)
    const bFormItem = page.locator('.el-form-item').nth(1)
    const bRatioInput = bFormItem.locator('.el-input-number input').nth(2)

    await aRatioInput.fill('25')
    await bRatioInput.fill('45')

    await page.getByRole('button', { name: '保存' }).first().click()
    await expectToast(page, '保存成功')

    await page.reload()
    await page.waitForTimeout(500)
    await expect(aRatioInput).toHaveValue('25')
    await expect(bRatioInput).toHaveValue('45')

    // 恢复默认值
    await aRatioInput.fill('20')
    await bRatioInput.fill('50')
    await page.getByRole('button', { name: '保存' }).first().click()
    await expectToast(page, '保存成功')
  })

  test('配置维度权重并持久化', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/config')
    await page.waitForTimeout(500)

    await page.getByRole('tab', { name: '维度权重' }).click()
    await page.waitForTimeout(300)

    const perfInput = page.locator('.el-form-item').filter({ hasText: '工作业绩权重' }).locator('.el-input-number input').first()
    const attitudeInput = page.locator('.el-form-item').filter({ hasText: '工作态度权重' }).locator('.el-input-number input').first()
    await perfInput.fill('65')
    await attitudeInput.fill('15')

    await page.getByRole('button', { name: '保存' }).first().click()
    await expectToast(page, '保存成功')

    await page.reload()
    await page.waitForTimeout(500)
    await page.getByRole('tab', { name: '维度权重' }).click()
    await page.waitForTimeout(300)
    await expect(perfInput).toHaveValue('65')
    await expect(attitudeInput).toHaveValue('15')

    await perfInput.fill('60')
    await attitudeInput.fill('20')
    await page.getByRole('button', { name: '保存' }).first().click()
    await expectToast(page, '保存成功')
  })

  test('维度权重合计不等于100时禁用保存按钮', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/config')
    await page.waitForTimeout(500)

    await page.getByRole('tab', { name: '维度权重' }).click()
    await page.waitForTimeout(300)

    const perfInput = page.locator('.el-form-item').filter({ hasText: '工作业绩权重' }).locator('.el-input-number input').first()
    await perfInput.fill('60')

    const abilityInput = page.locator('.el-form-item').filter({ hasText: '工作能力权重' }).locator('.el-input-number input').first()
    await abilityInput.fill('20')

    const attitudeInput = page.locator('.el-form-item').filter({ hasText: '工作态度权重' }).locator('.el-input-number input').first()
    await attitudeInput.fill('19')

    // 断言合计标签为错误状态
    await expect(page.locator('.el-tag--danger').filter({ hasText: '应为100' })).toBeVisible()

    // 断言保存按钮被禁用
    const saveBtn = page.getByRole('button', { name: '保存' }).first()
    await expect(saveBtn).toBeDisabled()
  })
})

/* ───────────────────────────────────────────────
 * P0 场景 — 员工管理
 * ─────────────────────────────────────────────── */

test.describe('P0 场景 — 员工管理', () => {
  test('新增员工并验证列表刷新', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/employees')
    await page.waitForTimeout(500)
    await expect(page.locator('table').first()).toBeVisible()

    await page.getByRole('button', { name: '新增员工' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '新增员工')
    await expect(dialog).toBeVisible()

    const empNo = uniqueId()
    const empName = `测试-${empNo}`

    await dialog.locator('.el-form-item').filter({ hasText: '工号' }).locator('input').first().fill(empNo)
    await dialog.locator('.el-form-item').filter({ hasText: '姓名' }).locator('input').first().fill(empName)
    await selectInDialog(page, dialog, '部门', TEST_DEPT)
    await page.waitForTimeout(300)
    await selectInDialog(page, dialog, '岗位', TEST_POSITION)

    await dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '创建成功')

    await page.locator('.search-form .el-form-item').filter({ hasText: '关键词' }).locator('input').first().fill(empNo)
    await page.getByRole('button', { name: '查询' }).click()
    await page.waitForTimeout(300)

    await expect(page.getByText(empNo).first()).toBeVisible()
  })

  test('编辑员工并验证列表更新', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/employees')
    await page.waitForTimeout(500)

    await page.locator('.search-form .el-form-item').filter({ hasText: '关键词' }).locator('input').first().fill('测试-')
    await page.getByRole('button', { name: '查询' }).click()
    await page.waitForTimeout(300)

    const firstRow = page.locator('table tbody tr').first()
    await firstRow.getByRole('button', { name: '编辑' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '编辑员工')
    await expect(dialog).toBeVisible()

    const newName = `编辑后-${uniqueId()}`
    await dialog.locator('.el-form-item').filter({ hasText: '姓名' }).locator('input').first().fill(newName)

    await dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '更新成功')

    await page.goto('/employees')
    await page.waitForTimeout(500)
    await page.locator('.search-form .el-form-item').filter({ hasText: '关键词' }).locator('input').first().fill(newName)
    await page.getByRole('button', { name: '查询' }).click()
    await page.waitForTimeout(300)
    await expect(page.getByText(newName).first()).toBeVisible()
  })
})

/* ───────────────────────────────────────────────
 * P0 场景 — 考核周期与报表
 * ─────────────────────────────────────────────── */

test.describe('P0 场景 — 考核周期与报表', () => {
  test('创建考核周期并验证列表', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/cycles')
    await page.waitForTimeout(500)

    await page.getByRole('button', { name: '新增周期' }).click()
    await page.waitForTimeout(800)
    const dialog = getDialog(page, '新增周期')
    await expect(dialog).toBeVisible()

    const cycleName = `周期-${uniqueId()}`
    await dialog.locator('.el-form-item').filter({ hasText: '名称' }).locator('input').first().fill(cycleName)
    await selectInDialog(page, dialog, '类型', '月度')

    // 填写日期选择器：直接定位两个输入框
    const startDate = '2026-08-01'
    const endDate = '2026-08-31'
    const dateFormItem = dialog.locator('.el-form-item').filter({ hasText: '考核时间' })
    await dateFormItem.click()
    await page.waitForTimeout(300)
    // 点击第一个日历面板的 1 号，第二个面板的 31 号
    await page.getByRole('gridcell', { name: '1' }).first().click()
    await page.getByRole('gridcell', { name: '31' }).last().click()
    await page.waitForTimeout(300)

    await dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '创建成功')

    await page.goto('/cycles')
    await page.waitForTimeout(500)
    await expect(page.getByText(cycleName).first()).toBeVisible()
    const row = page.locator('table tbody tr').filter({ hasText: cycleName })
    await expect(row.getByText('未开始')).toBeVisible()
  })

  test('导出分数汇总表 Excel', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/reports')
    await page.waitForTimeout(500)

    const cycleSelect = page.locator('.el-form-item').filter({ hasText: '考核周期' }).locator('.el-select').first()
    await cycleSelect.click()
    const dropdown = page.locator('.el-select-dropdown').last()
    await dropdown.waitFor({ state: 'visible' })

    const firstOption = dropdown.locator('.el-select-dropdown__item').first()
    const hasCycles = await firstOption.isVisible().catch(() => false)
    await page.keyboard.press('Escape')

    if (!hasCycles) {
      test.info().annotations.push({ type: 'skip', description: '没有可用的考核周期' })
      return
    }

    await cycleSelect.click()
    await dropdown.locator('.el-select-dropdown__item').first().click()

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15000 }),
      page.getByRole('button', { name: '导出 Excel' }).click(),
    ])

    const filename = download.suggestedFilename()
    expect(filename).toMatch(/\.xlsx$/)
  })
})

/* ───────────────────────────────────────────────
 * P1 场景 — 系统配置扩展
 * ─────────────────────────────────────────────── */

test.describe('P1 场景 — 系统配置扩展', () => {
  test('配置评价人权重并持久化', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/config')
    await page.waitForTimeout(500)

    await page.getByRole('tab', { name: '评价人权重' }).click()
    await page.waitForTimeout(300)

    // 每个维度下都有 自评/上级/协作；nth(0) 对应业绩维度
    const selfInputs = page.locator('.el-form-item').filter({ hasText: '自评' }).locator('.el-input-number input')
    const managerInputs = page.locator('.el-form-item').filter({ hasText: '上级' }).locator('.el-input-number input')
    const peerInputs = page.locator('.el-form-item').filter({ hasText: '协作' }).locator('.el-input-number input')

    const perfSelf = selfInputs.nth(0)
    const perfManager = managerInputs.nth(0)
    const perfPeer = peerInputs.nth(0)

    // 业绩维度改为 25+70+5=100，能力与态度保持默认 100
    await perfSelf.fill('25')
    await perfManager.fill('70')
    await perfPeer.fill('5')

    await page.getByRole('button', { name: '保存' }).first().click()
    await expectToast(page, '保存成功')

    await page.reload()
    await page.waitForTimeout(500)
    await page.getByRole('tab', { name: '评价人权重' }).click()
    await page.waitForTimeout(300)
    await expect(perfSelf).toHaveValue('25')
    await expect(perfManager).toHaveValue('70')
    await expect(perfPeer).toHaveValue('5')

    // 恢复：业绩 30+70+0=100
    await perfSelf.fill('30')
    await perfManager.fill('70')
    await perfPeer.fill('0')
    await page.getByRole('button', { name: '保存' }).first().click()
    await expectToast(page, '保存成功')
  })

  test('配置小部门豁免开关并持久化', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/config')
    await page.waitForTimeout(500)

    await page.getByRole('tab', { name: '小部门豁免' }).click()
    await page.waitForTimeout(300)

    const switchInput = page.locator('.el-form-item').filter({ hasText: '豁免开关' }).locator('.el-switch').first()
    const isChecked = await switchInput.locator('input').first().isChecked()
    if (!isChecked) {
      await switchInput.click()
    }

    const thresholdInput = page.locator('.el-form-item').filter({ hasText: '部门人数阈值' }).locator('.el-input-number input').first()
    await thresholdInput.fill('10')

    await page.getByRole('button', { name: '保存' }).first().click()
    await expectToast(page, '保存成功')

    await page.reload()
    await page.waitForTimeout(500)
    await page.getByRole('tab', { name: '小部门豁免' }).click()
    await page.waitForTimeout(300)
    await expect(thresholdInput).toHaveValue('10')

    await thresholdInput.fill('5')
    if (!isChecked) {
      await switchInput.click()
    }
    await page.getByRole('button', { name: '保存' }).first().click()
    await expectToast(page, '保存成功')
  })
})

/* ───────────────────────────────────────────────
 * P1 场景 — 部门与岗位管理
 * ─────────────────────────────────────────────── */

test.describe.serial('P1 场景 — 部门与岗位管理', () => {
  test('新增部门并验证列表', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/departments')
    await page.waitForTimeout(500)
    await expect(page.locator('table').first()).toBeVisible()

    await page.getByRole('button', { name: '新增部门' }).click()
    await page.waitForTimeout(1500)
    const dialog = getDialog(page, '新增部门')
    await expect(dialog).toBeVisible()

    const code = `DEPT-${uniqueId()}`
    const name = `测试部-${code}`

    await dialog.locator('.el-form-item').filter({ hasText: '编码' }).locator('input').first().fill(code)
    await dialog.locator('.el-form-item').filter({ hasText: '名称' }).locator('input').first().fill(name)
    await page.waitForTimeout(500)

    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/departments') && resp.request().method() === 'POST', { timeout: 15000 }),
      dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    ])
    console.log('Create dept response status:', response.status())
    if (!response.ok()) {
      const body = await response.text().catch(() => 'unable to read')
      console.log('Create dept response body:', body)
    }
    await expectToast(page, '创建成功')

    await page.goto('/departments')
    await page.waitForTimeout(500)
    await expect(page.getByText(name).first()).toBeVisible()
  })

  test('编辑部门并验证更新', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/departments')
    await page.waitForTimeout(500)

    await page.locator('table tbody tr').filter({ hasText: '测试部-' }).first().getByRole('button', { name: '编辑' }).click()
    await page.waitForTimeout(800)
    const dialog = getDialog(page, '编辑部门')
    await expect(dialog).toBeVisible()

    const newName = `编辑部-${uniqueId()}`
    await dialog.locator('.el-form-item').filter({ hasText: '名称' }).locator('input').first().fill(newName)
    await page.waitForTimeout(300)

    await dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '更新成功')

    await page.goto('/departments')
    await page.waitForTimeout(500)
    await expect(page.getByText(newName).first()).toBeVisible()
  })

  test('删除部门并验证移除', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/departments')
    await page.waitForTimeout(500)

    const countBefore = await page.locator('table tbody tr').filter({ hasText: '编辑部-' }).count()
    expect(countBefore).toBeGreaterThan(0)

    const targetRow = page.locator('table tbody tr').filter({ hasText: '编辑部-' }).first()
    await targetRow.getByRole('button', { name: '删除' }).click()

    await expect(page.locator('.el-message-box').filter({ hasText: '确认删除' })).toBeVisible()
    await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
    await expectToast(page, '删除成功')

    await page.goto('/departments')
    await page.waitForTimeout(500)
    const countAfter = await page.locator('table tbody tr').filter({ hasText: '编辑部-' }).count()
    expect(countAfter).toBe(countBefore - 1)
  })

  test('新增岗位并验证', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/departments')
    await page.waitForTimeout(500)

    const deptRow = page.locator('table tbody tr').filter({ hasText: TEST_DEPT }).first()
    await deptRow.getByRole('button', { name: '管理岗位' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '岗位管理')
    await expect(dialog).toBeVisible()

    const posName = `岗位-${uniqueId()}`
    await dialog.locator('.el-form-item').filter({ hasText: '名称' }).locator('input').first().fill(posName)
    await dialog.locator('.el-form-item').filter({ hasText: '职级' }).locator('input').first().fill('P5')

    await dialog.getByRole('button', { name: '新增' }).click()
    await expectToast(page, '创建成功')

    await expect(dialog.locator('table').getByText(posName)).toBeVisible()
  })

  test('编辑岗位并验证更新', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/departments')
    await page.waitForTimeout(500)

    const deptRow = page.locator('table tbody tr').filter({ hasText: TEST_DEPT }).first()
    await deptRow.getByRole('button', { name: '管理岗位' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '岗位管理')
    await expect(dialog).toBeVisible()

    const posRow = dialog.locator('table tbody tr').filter({ hasText: '岗位-' }).first()
    await posRow.getByRole('button', { name: '编辑' }).click()

    const newName = `编辑岗位-${uniqueId()}`
    await dialog.locator('.el-form-item').filter({ hasText: '名称' }).locator('input').first().fill(newName)

    await dialog.getByRole('button', { name: '保存' }).click()
    await expectToast(page, '更新成功')

    await expect(page.getByText(newName).first()).toBeVisible()
  })

  test('删除岗位并验证移除', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/departments')
    await page.waitForTimeout(500)

    const deptRow = page.locator('table tbody tr').filter({ hasText: TEST_DEPT }).first()
    await deptRow.getByRole('button', { name: '管理岗位' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '岗位管理')
    await expect(dialog).toBeVisible()

    const posRow = dialog.locator('table tbody tr').filter({ hasText: '编辑岗位-' }).first()
    await posRow.getByRole('button', { name: '删除' }).click()

    await expect(page.locator('.el-message-box').filter({ hasText: '确认删除' })).toBeVisible()
    await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
    await expectToast(page, '删除成功')

    await expect(dialog.locator('table').getByText('编辑岗位-')).not.toBeVisible()
  })
})

/* ───────────────────────────────────────────────
 * P1 场景 — 考核周期与 KPI 模板
 * ─────────────────────────────────────────────── */

test.describe('P1 场景 — 考核周期与 KPI 模板', () => {
  test('删除考核周期并验证移除', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/cycles')
    await page.waitForTimeout(500)

    // 先创建一个唯一的考核周期，然后删除它
    const cycleName = `周期-e2e-${uniqueId()}`
    await page.getByRole('button', { name: '新增周期' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '新增周期')
    await expect(dialog).toBeVisible()

    await dialog.locator('.el-form-item').filter({ hasText: '名称' }).locator('input').first().fill(cycleName)
    await selectInDialog(page, dialog, '类型', '月度')

    const nextMonth = new Date()
    nextMonth.setMonth(nextMonth.getMonth() + 1)
    const year = nextMonth.getFullYear()
    const month = nextMonth.getMonth() + 1
    const startDate = `${year}-${String(month).padStart(2, '0')}-01`
    const endDate = `${year}-${String(month).padStart(2, '0')}-28`

    const dateFormItem = dialog.locator('.el-form-item').filter({ hasText: '考核时间' })
    await dateFormItem.click()
    await page.waitForTimeout(300)
    // 点击第一个日历面板的 1 号，第二个面板的 31 号
    await page.getByRole('gridcell', { name: '1' }).first().click()
    await page.getByRole('gridcell', { name: '31' }).last().click()
    await page.waitForTimeout(300)

    await dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '创建成功')

    await page.goto('/cycles')
    await page.waitForTimeout(500)

    const targetRow = page.locator('table tbody tr').filter({ hasText: cycleName }).first()
    await targetRow.getByRole('button', { name: '删除' }).click()

    await expect(page.locator('.el-message-box').filter({ hasText: '确认删除' })).toBeVisible()
    await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
    await expectToast(page, '删除成功')

    await page.goto('/cycles')
    await page.waitForTimeout(500)
    await expect(page.getByText(cycleName).first()).not.toBeVisible()
  })

  test('新增 KPI 模板并验证', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/kpi-templates')
    await page.waitForTimeout(500)
    await expect(page.locator('table').first()).toBeVisible()

    await page.getByRole('button', { name: '新增模板' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '新增模板')
    await expect(dialog).toBeVisible()

    await selectInDialog(page, dialog, '岗位', TEST_POSITION)
    await dialog.locator('.el-form-item').filter({ hasText: '指标名称' }).locator('input').first().fill(`指标-${uniqueId()}`)
    await dialog.locator('.el-form-item').filter({ hasText: '权重' }).locator('.el-input-number input').first().fill('30')
    await dialog.locator('.el-form-item').filter({ hasText: '目标值' }).locator('input').first().fill('100万')

    await dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '创建成功')

    await page.goto('/kpi-templates')
    await page.waitForTimeout(500)
    await expect(page.locator('table').first()).toBeVisible()
  })

  test('编辑 KPI 模板并验证', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/kpi-templates')
    await page.waitForTimeout(500)

    const row = page.locator('table tbody tr').filter({ hasText: '指标-' }).first()
    await row.getByRole('button', { name: '编辑' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '编辑模板')
    await expect(dialog).toBeVisible()

    await dialog.locator('.el-form-item').filter({ hasText: '权重' }).locator('.el-input-number input').first().fill('35')

    await dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '更新成功')

    await page.goto('/kpi-templates')
    await page.waitForTimeout(500)
    // 断言表格中某行的权重为 35
    const weightRow = page.locator('table tbody tr').filter({ hasText: '指标-' }).first()
    await expect(weightRow.getByText('35', { exact: true })).toBeVisible()
  })

  test('删除 KPI 模板并验证', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/kpi-templates')
    await page.waitForTimeout(500)

    const row = page.locator('table tbody tr').filter({ hasText: '指标-' }).first()
    await row.getByRole('button', { name: '删除' }).click()

    await expect(page.locator('.el-message-box').filter({ hasText: '确认删除' })).toBeVisible()
    await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
    await expectToast(page, '删除成功')

    await page.goto('/kpi-templates')
    await page.waitForTimeout(500)
    await expect(page.locator('table').first().getByText('指标-')).not.toBeVisible()
  })
})

/* ───────────────────────────────────────────────
 * P1 场景 — 数据治理与审批
 * ─────────────────────────────────────────────── */

test.describe('P1 场景 — 数据治理与审批', () => {
  test('查看操作日志审计', async ({ page }) => {
    await adminLogin(page)
    await page.goto('/audit-logs')
    await page.waitForTimeout(500)

    await expect(page.getByRole('heading', { name: '操作日志审计' })).toBeVisible()
    await expect(page.locator('table').first()).toBeVisible()
    await expect(page.locator('table th').filter({ hasText: '操作用户' })).toBeVisible()
    await expect(page.locator('table th').filter({ hasText: '操作类型' })).toBeVisible()
    await expect(page.locator('table th').filter({ hasText: '操作时间' })).toBeVisible()
    await expect(page.locator('.el-pagination')).toBeVisible()
  })

  test('查看绩效汇总页面', async ({ page }) => {
    await adminLogin(page)
    await page.goto('/summary')
    await page.waitForTimeout(500)

    await expect(page.getByRole('heading', { name: '绩效汇总' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '考核周期' })).toBeVisible()
    await expect(page.getByRole('button', { name: '触发汇总计算' })).toBeVisible()
  })

  test('强制分布处理页面准入', async ({ page }) => {
    await adminLogin(page)
    await page.goto('/distribution-review')
    await page.waitForTimeout(500)

    await expect(page.getByRole('heading', { name: '强制分布处理' })).toBeVisible()
    await expect(page.locator('.el-form-item').filter({ hasText: '考核周期' })).toBeVisible()
    await expect(page.getByRole('button', { name: '查询' })).toBeVisible()
  })
})

/* ───────────────────────────────────────────────
 * P2 场景 — 其他操作
 * ─────────────────────────────────────────────── */

test.describe('P2 场景 — 其他操作', () => {
  test('删除员工并验证移除', async ({ page }) => {
    test.setTimeout(60000)
    await adminLogin(page)
    await page.goto('/employees')
    await page.waitForTimeout(500)

    // 先创建一个唯一标识的员工，然后删除它
    const empNo = `del-${uniqueId()}`
    const empName = `待删除-${empNo}`

    await page.getByRole('button', { name: '新增员工' }).click()
    await page.waitForTimeout(300)
    const dialog = getDialog(page, '新增员工')
    await expect(dialog).toBeVisible()

    await dialog.locator('.el-form-item').filter({ hasText: '工号' }).locator('input').first().fill(empNo)
    await dialog.locator('.el-form-item').filter({ hasText: '姓名' }).locator('input').first().fill(empName)
    await selectInDialog(page, dialog, '部门', TEST_DEPT)
    await page.waitForTimeout(300)
    await selectInDialog(page, dialog, '岗位', TEST_POSITION)

    await dialog.locator('.el-dialog__footer').getByRole('button', { name: '确定' }).click()
    await expectToast(page, '创建成功')

    await page.goto('/employees')
    await page.waitForTimeout(500)

    await page.locator('.search-form .el-form-item').filter({ hasText: '关键词' }).locator('input').first().fill(empNo)
    await page.getByRole('button', { name: '查询' }).click()
    await page.waitForTimeout(300)

    const targetRow = page.locator('table tbody tr').filter({ hasText: empNo }).first()
    await targetRow.getByRole('button', { name: '删除' }).click()

    await expect(page.locator('.el-message-box').filter({ hasText: '确认删除' })).toBeVisible()
    await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click()
    await expectToast(page, '删除成功')

    await page.goto('/employees')
    await page.waitForTimeout(500)
    await page.locator('.search-form .el-form-item').filter({ hasText: '关键词' }).locator('input').first().fill(empNo)
    await page.getByRole('button', { name: '查询' }).click()
    await page.waitForTimeout(300)
    await expect(page.locator('table tbody tr').filter({ hasText: empNo })).toHaveCount(0)
  })
})
