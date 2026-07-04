import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'

/**
 * E2E 场景 1.5：HR 导入员工
 * 覆盖：登录 → 下载模板 → 上传导入 → 验证结果
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

test.describe('场景 1.5 — HR 导入员工', () => {
  test('HR 下载模板并导入员工', async ({ page }) => {
    const hrToken = await getToken(page, 'hr001', 'Hr001@123')

    // 下载样例模板
    const templateRes = await page.request.get('/api/employees/template?type=sample', {
      headers: { Authorization: `Bearer ${hrToken}` }
    })
    const buffer = await templateRes.body()
    const tmpPath = path.join(os.tmpdir(), `scenario1.5_${Date.now()}.xlsx`)
    fs.writeFileSync(tmpPath, buffer)

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
    await fileChooser.setFiles(tmpPath)
    await page.waitForTimeout(300)

    // 点击导入
    await importDialog.getByRole('button', { name: '导入' }).click()
    await expect(page.getByText('导入成功')).toBeVisible()

    // 清理
    try { fs.unlinkSync(tmpPath) } catch (_) {}
  })
})
