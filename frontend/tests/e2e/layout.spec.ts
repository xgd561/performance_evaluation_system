import { test, expect } from '@playwright/test'

/**
 * 辅助：模拟登录状态（直接写入 localStorage，不依赖后端）
 */
async function mockLogin(page: any, role: string, name: string) {
  await page.goto('/login')
  await page.evaluate(
    ({ role, name }) => {
      localStorage.setItem('pes_access_token', `mock_jwt_${role}`)
      localStorage.setItem(
        'pes_user_info',
        JSON.stringify({ id: 1, username: role, name, role })
      )
    },
    { role, name }
  )
  await page.goto('/dashboard')
  await page.waitForURL('**/dashboard')
}

test.describe('P0-18 Layout — 侧边栏与顶部栏', () => {
  test('admin 登录后侧边栏应显示系统配置、员工管理、考核周期等', async ({ page }) => {
    await mockLogin(page, 'admin', '张系管')

    // 仪表盘应在菜单中
    await expect(page.locator('.app-sidebar').getByText('仪表盘')).toBeVisible()
    // 员工管理
    await expect(page.locator('.app-sidebar').getByText('员工管理')).toBeVisible()
    // 部门岗位
    await expect(page.locator('.app-sidebar').getByText('部门岗位')).toBeVisible()
    // 考核周期
    await expect(page.locator('.app-sidebar').getByText('考核周期')).toBeVisible()
    // KPI模板
    await expect(page.locator('.app-sidebar').getByText('KPI模板')).toBeVisible()
    // 系统配置
    await expect(page.locator('.app-sidebar').getByText('系统配置')).toBeVisible()
    // 操作日志
    await expect(page.locator('.app-sidebar').getByText('操作日志')).toBeVisible()
    // 申诉管理
    await expect(page.locator('.app-sidebar').getByText('申诉管理')).toBeVisible()

    // 顶部栏应显示用户名和角色标签
    await expect(page.locator('.app-header .user-name')).toHaveText('张系管')
    await expect(page.locator('.app-header .role-tag')).toHaveText('系统管理员')
  })

  test('employee 登录后侧边栏应仅显示我的绩效、自评、申诉等', async ({ page }) => {
    await mockLogin(page, 'employee', '王志强')

    // 应有菜单项
    await expect(page.locator('.app-sidebar').getByText('仪表盘')).toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('自评')).toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('我的绩效')).toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('申诉')).toBeVisible()

    // 不应出现 admin 专属菜单
    await expect(page.locator('.app-sidebar').getByText('员工管理')).not.toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('系统配置')).not.toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('考核周期')).not.toBeVisible()

    // 顶部栏
    await expect(page.locator('.app-header .user-name')).toHaveText('王志强')
    await expect(page.locator('.app-header .role-tag')).toHaveText('普通员工')
  })

  test('manager 登录后侧边栏应显示评分、审批工作台、绩效面谈', async ({ page }) => {
    await mockLogin(page, 'manager', '李建国')

    await expect(page.locator('.app-sidebar').getByText('上级评分')).toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('审批工作台')).toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('绩效面谈')).toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('KPI调整申请')).toBeVisible()

    await expect(page.locator('.app-sidebar').getByText('系统配置')).not.toBeVisible()
    await expect(page.locator('.app-header .role-tag')).toHaveText('部门负责人')
  })

  test('peer 登录后侧边栏应仅显示协作评分', async ({ page }) => {
    await mockLogin(page, 'peer', '赵晓峰')

    await expect(page.locator('.app-sidebar').getByText('协作评分')).toBeVisible()
    await expect(page.locator('.app-sidebar').getByText('我的绩效')).not.toBeVisible()
    await expect(page.locator('.app-header .role-tag')).toHaveText('协作评分人')
  })

  test('点击菜单项应正确跳转', async ({ page }) => {
    await mockLogin(page, 'admin', '张系管')

    // 点击系统配置（直接点击 el-menu-item 包含文本的父元素，确保事件冒泡触发）
    await page.locator('.el-menu-item').filter({ hasText: '系统配置' }).click()
    await page.waitForURL('**/config')
    expect(page.url()).toContain('/config')

    // 点击员工管理
    await page.locator('.el-menu-item').filter({ hasText: '员工管理' }).click()
    await page.waitForURL('**/employees')
    expect(page.url()).toContain('/employees')
  })

  test('面包屑导航在仪表盘应显示', async ({ page }) => {
    await mockLogin(page, 'admin', '张系管')
    await page.goto('/dashboard')
    await page.waitForURL('**/dashboard')

    await expect(page.locator('.breadcrumb-nav')).toBeVisible()
  })

  test('面包屑导航在配置页应显示', async ({ page }) => {
    await mockLogin(page, 'admin', '张系管')
    await page.goto('/config')
    await page.waitForURL('**/config')

    await expect(page.locator('.breadcrumb-nav')).toBeVisible()
  })

  test('点击退出登录应清除 localStorage 并跳转 /login', async ({ page }) => {
    await mockLogin(page, 'admin', '张系管')

    await page.locator('.app-header .user-dropdown').click()
    await page.getByText('退出登录').click()

    await page.waitForURL('**/login')
    expect(page.url()).toContain('/login')

    const token = await page.evaluate(() => localStorage.getItem('pes_access_token'))
    const user = await page.evaluate(() => localStorage.getItem('pes_user_info'))
    expect(token).toBeNull()
    expect(user).toBeNull()
  })

  test('侧边栏折叠/展开按钮应生效', async ({ page }) => {
    await mockLogin(page, 'admin', '张系管')

    const aside = page.locator('.layout-container > .el-aside')
    // 初始展开
    await expect(aside).toHaveCSS('width', '210px')

    // 点击折叠
    await page.locator('.app-header .collapse-btn').click()
    await expect(aside).toHaveCSS('width', '64px')

    // 点击展开
    await page.locator('.app-header .collapse-btn').click()
    await expect(aside).toHaveCSS('width', '210px')
  })
})
