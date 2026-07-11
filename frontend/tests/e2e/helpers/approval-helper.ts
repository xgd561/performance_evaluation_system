import { Page } from '@playwright/test'

export async function managerLogin(page: Page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('mgr001')
  await page.getByPlaceholder('密码').fill('Mgr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

export async function hrLogin(page: Page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('hr001')
  await page.getByPlaceholder('密码').fill('Hr001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

export async function employeeLogin(page: Page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('emp001')
  await page.getByPlaceholder('密码').fill('Emp001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}

export async function executiveLogin(page: Page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('exec001')
  await page.getByPlaceholder('密码').fill('Exec001@123')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/dashboard')
}
