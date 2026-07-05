import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'
import * as XLSX from 'xlsx'
import { adminLogin } from './helpers/admin-helper'

/**
 * E2E 场景 1.5：HR 导入员工
 * 覆盖：登录 → 下载模板 → 上传导入 → 验证结果 → 导入失败场景
 */

async function hrLogin(page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('hr001')
  await page.getByPlaceholder('密码').fill('Hr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

async function getToken(page, username, password) {
  const res = await page.request.post('/api/auth/login', {
    headers: { 'Content-Type': 'application/json' },
    data: JSON.stringify({ username, password })
  })
  const body = await res.json()
  if (!body.access_token) throw new Error(`Login failed for ${username}`)
  return body.access_token
}

function generateUniqueEmployeeNo() {
  return `E2E${Date.now()}${Math.floor(Math.random() * 1000)}`
}

test.describe('场景 1.5 — HR 导入员工', () => {
  test('HR 下载模板并导入员工，验证列表更新', async ({ page }) => {
    const hrToken = await getToken(page, 'hr001', 'Hr001@123')

    // 生成唯一工号，避免重复导入
    const empNo = generateUniqueEmployeeNo()
    const empName = `导入测试${Date.now()}`

    // 下载样例模板
    const templateRes = await page.request.get('/api/employees/template?type=sample', {
      headers: { Authorization: `Bearer ${hrToken}` }
    })
    const buffer = await templateRes.body()
    const tmpPath = path.join(os.tmpdir(), `scenario1.5_${Date.now()}.xlsx`)
    fs.writeFileSync(tmpPath, buffer)

    // 读取模板并在样例数据后追加一条新记录
    const wb = XLSX.readFile(tmpPath)
    const ws = wb.Sheets[wb.SheetNames[0]]
    const data = XLSX.utils.sheet_to_json(ws, { header: 1 }) as any[][]
    data.push([empNo, empName, '技术部', 'Java工程师', '', '否', '2024-06-01', '在职'])
    const newWs = XLSX.utils.aoa_to_sheet(data)
    wb.Sheets[wb.SheetNames[0]] = newWs
    const newPath = path.join(os.tmpdir(), `scenario1.5_import_${Date.now()}.xlsx`)
    XLSX.writeFile(wb, newPath)

    await hrLogin(page)
    await page.goto('/employees')
    await expect(page).toHaveURL(/.*\/employees/)

    // 导入前搜索，确认不存在
    const searchInput = page.locator('.el-form-item').filter({ hasText: '关键词' }).locator('input').first()
    await searchInput.fill(empNo)
    await page.getByRole('button', { name: '查询' }).click()
    await page.waitForTimeout(300)
    // 断言表格中没有该工号
    await expect(page.locator('table').filter({ hasText: '工号' })).not.toContainText(empNo)

    // 点击导入按钮
    await page.getByRole('button', { name: '导入员工' }).click()
    const importDialog = page.locator('.el-dialog').filter({ hasText: '导入员工' })
    await expect(importDialog).toBeVisible()

    // 上传文件
    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      importDialog.getByRole('button', { name: '选择Excel文件' }).first().click()
    ])
    await fileChooser.setFiles(newPath)
    await page.waitForTimeout(300)

    // 点击导入
    await importDialog.getByRole('button', { name: '导入' }).click()
    await expect(page.getByText('导入成功')).toBeVisible()

    // 导入后验证列表中出现了新员工
    await searchInput.clear()
    await searchInput.fill(empNo)
    await page.getByRole('button', { name: '查询' }).click()
    await page.waitForTimeout(300)
    await expect(page.locator('table').filter({ hasText: '工号' })).toContainText(empNo)
    await expect(page.locator('table').filter({ hasText: '工号' })).toContainText(empName)

    // 清理临时文件
    try { fs.unlinkSync(tmpPath) } catch (_) {}
    try { fs.unlinkSync(newPath) } catch (_) {}
  })

  test('导入重复工号应提示失败', async ({ page }) => {
    const hrToken = await getToken(page, 'hr001', 'Hr001@123')
    const empNo = generateUniqueEmployeeNo()

    // 构造含重复工号的 Excel
    const wb = XLSX.utils.book_new()
    const ws = XLSX.utils.aoa_to_sheet([
      ['工号', '姓名', '部门', '岗位', '直属上级工号', '是否部门负责人', '入职日期', '状态'],
      [empNo, '员工A', '技术部', 'Java工程师', '', '否', '2024-06-01', '在职'],
      [empNo, '员工B', '技术部', '前端工程师', '', '否', '2024-06-02', '在职'],
    ])
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
    const dupPath = path.join(os.tmpdir(), `scenario1.5_dup_${Date.now()}.xlsx`)
    XLSX.writeFile(wb, dupPath)

    await hrLogin(page)
    await page.goto('/employees')
    await expect(page).toHaveURL(/.*\/employees/)

    // 点击导入按钮
    await page.getByRole('button', { name: '导入员工' }).click()
    const importDialog = page.locator('.el-dialog').filter({ hasText: '导入员工' })
    await expect(importDialog).toBeVisible()

    // 上传文件
    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      importDialog.getByRole('button', { name: '选择Excel文件' }).first().click()
    ])
    await fileChooser.setFiles(dupPath)
    await page.waitForTimeout(300)

    // 点击导入
    await importDialog.getByRole('button', { name: '导入' }).click()
    // 应提示错误（文件内重复工号）
    await expect(page.getByText(/重复工号|存在重复/)).toBeVisible({ timeout: 5000 })

    try { fs.unlinkSync(dupPath) } catch (_) {}
  })

  test('导入必填字段缺失应提示失败', async ({ page }) => {
    const hrToken = await getToken(page, 'hr001', 'Hr001@123')

    // 构造缺少工号的 Excel
    const wb = XLSX.utils.book_new()
    const ws = XLSX.utils.aoa_to_sheet([
      ['工号', '姓名', '部门', '岗位', '直属上级工号', '是否部门负责人', '入职日期', '状态'],
      ['', '无名员工', '技术部', 'Java工程师', '', '否', '2024-06-01', '在职'],
    ])
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
    const missingPath = path.join(os.tmpdir(), `scenario1.5_missing_${Date.now()}.xlsx`)
    XLSX.writeFile(wb, missingPath)

    await hrLogin(page)
    await page.goto('/employees')
    await expect(page).toHaveURL(/.*\/employees/)

    // 点击导入按钮
    await page.getByRole('button', { name: '导入员工' }).click()
    const importDialog = page.locator('.el-dialog').filter({ hasText: '导入员工' })
    await expect(importDialog).toBeVisible()

    // 上传文件
    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      importDialog.getByRole('button', { name: '选择Excel文件' }).first().click()
    ])
    await fileChooser.setFiles(missingPath)
    await page.waitForTimeout(300)

    // 点击导入
    await importDialog.getByRole('button', { name: '导入' }).click()
    // 应提示必填字段缺失
    await expect(page.getByText(/工号为必填项|必填字段缺失/)).toBeVisible({ timeout: 5000 })

    try { fs.unlinkSync(missingPath) } catch (_) {}
  })
})
