import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright 端到端测试配置
 * - 测试目录：tests/e2e
 * - baseURL：前端开发服务器 http://localhost:3000
 * - 浏览器：Chromium（桌面版）
 * - 自动启动前端 dev server（npm run dev），需配合后端服务运行
 */

export default defineConfig({
  testDir: './tests/e2e',

  /* 测试超时：60 秒（配合 slowMo 模式） */
  timeout: 60 * 1000,

  /* 并行运行测试文件 */
  fullyParallel: true,

  /* CI 中禁止 test.only */
  forbidOnly: !!process.env.CI,

  /* CI 中重试失败用例，本地不重试 */
  retries: process.env.CI ? 2 : 0,

  /* CI 中限制 worker 数量 */
  workers: process.env.CI ? 1 : undefined,

  /* 测试报告 */
  reporter: [['list'], ['html', { outputFolder: 'playwright-report' }]],

  use: {
    /* 基础 URL，所有 page.goto('/xxx') 会基于此 */
    baseURL: 'http://localhost:3000',

    /* 收集追踪信息（首次失败时） */
    trace: 'on-first-retry',

    /* 失败时自动截图 */
    screenshot: 'only-on-failure',

    /* 失败时录制视频 */
    video: 'on-first-retry',

    /* 慢动作模式：每个操作延迟 800ms，方便观察 */
    launchOptions: {
      slowMo: 800,
    },
  },

  /* 项目配置 */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* 自动启动前端开发服务器 */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
