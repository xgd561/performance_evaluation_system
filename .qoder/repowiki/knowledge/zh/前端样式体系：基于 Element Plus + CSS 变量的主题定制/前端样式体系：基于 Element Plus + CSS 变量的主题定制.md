---
kind: frontend_style
name: 前端样式体系：基于 Element Plus + CSS 变量的主题定制
category: frontend_style
scope:
    - '**'
source_files:
    - frontend/package.json
    - frontend/src/main.js
    - frontend/src/styles/variables.css
    - frontend/src/styles/index.css
    - frontend/src/components/Layout.vue
---

## 1. 采用的系统与工具

- **UI 框架**：Vue 3（Composition API + `<script setup>`）+ Vite 构建。
- **组件库**：Element Plus `^2.7.5`，图标库 `@element-plus/icons-vue`，在 `frontend/src/main.js` 中全局注册。
- **样式方案**：原生 CSS + CSS Custom Properties（CSS 变量），未使用 Sass/Less 预处理器（尽管 devDependencies 中有 `sass`，但源码中未见 `.scss` 文件）。无 Tailwind、无 CSS Modules、无 styled-components。
- **设计系统载体**：通过 `src/styles/variables.css` 集中定义设计令牌（Design Tokens），再由 `src/styles/index.css` 覆盖 Element Plus 的 CSS 变量实现主题统一。

## 2. 关键文件

- `frontend/package.json` — 声明依赖（vue、element-plus、pinia、echarts、axios 等）。
- `frontend/src/main.js` — 应用入口，引入 Element Plus 及其默认样式、全局图标、以及 `@/styles/index.css`。
- `frontend/src/styles/variables.css` — 全部设计令牌（颜色、阴影、圆角、过渡、布局尺寸）。
- `frontend/src/styles/index.css` — 全局重置、Element Plus 主题覆盖、通用工具类。
- `frontend/src/components/Layout.vue` — 主布局（侧边栏 + 顶栏 + 面包屑 + 内容区），展示 CSS 变量与渐变的使用方式。

## 3. 架构与约定

### 3.1 设计令牌（Design Tokens）

所有视觉常量集中在 `:root` 下，分为若干语义分组：

| 分组 | 示例变量 | 用途 |
|---|---|---|
| Layout | `--sidebar-width: 240px`、`--header-height: 64px` | 侧边栏宽度、头部高度 |
| Brand Palette | `--primary-color: #6366f1`、`--accent-color: #f59e0b` | 主色（Deep Indigo）+ 强调色（Amber Gold） |
| Surfaces | `--bg-color`、`--bg-sidebar`、`--bg-card` | 背景面 |
| Text | `--text-primary`、`--text-secondary`、`--text-muted` | 文本层级 |
| Borders & Shadows | `--border-color`、`--shadow-sm/md/lg/xl` | 边框与阴影 |
| Radius | `--radius-sm/md/lg/xl` | 统一圆角 |
| Transitions | `--transition-fast/base/slow` | 统一缓动曲线 `cubic-bezier(0.4, 0, 0.2, 1)` |

### 3.2 Element Plus 主题映射

`index.css` 将业务设计令牌映射到 Element Plus 的 CSS 变量前缀 `--el-*`，例如：

```
--el-color-primary: var(--primary-color);
--el-border-radius-base: var(--radius-md);
--el-bg-color-page: var(--bg-color);
```

并进一步对常用组件进行手工微调：

- `.el-button--primary / --success / --danger / --warning`：使用 `linear-gradient(135deg, ...)` 渐变 + 彩色阴影，替代 Element Plus 默认纯色按钮。
- `.el-table`：设置 `--el-table-border-color`、圆角、条纹行背景为 `rgba(99, 102, 241, 0.02)`。
- `.el-input__wrapper`、`.el-textarea__inner`：内嵌 1px 边框 + focus 时添加 `box-shadow` 光晕。
- `.el-dialog`、`.el-card`、`.el-dropdown-menu`、`.el-message`、`.el-notification`：统一圆角与阴影。

### 3.3 全局样式约定

- 字体栈：`-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', ...`，基础字号 `14px`，行高 `1.5`。
- 滚动条：通过 `::-webkit-scrollbar` 自定义为 6px 宽、半透明轨道、可悬停变深。
- 通用工具类：`.page-container`（页面容器）、`.card-shadow`、`.text-ellipsis`、`.flex-center`。

### 3.4 布局结构

`Layout.vue` 使用 Element Plus 的 `el-container/el-aside/el-header/el-main` 组合，侧边栏宽度由 Pinia store `appStore.sidebarCollapsed` 在 `64px` 与 `240px` 之间切换；顶部 header 和面包屑区域使用 `backdrop-filter: blur(...)` 毛玻璃效果；路由视图包裹在 `transition name="slide-fade"` 中，实现左右滑入淡出动画。

## 4. 约定与约束

- **主题色单一来源**：所有颜色来自 `variables.css` 中的 CSS 变量，Element Plus 的 `--el-*` 变量仅作为映射层，业务组件不应直接写死十六进制色值。
- **Element Plus 样式覆盖位置**：组件级样式覆盖统一放在 `src/styles/index.css`，而非各 Vue 组件的 `<style scoped>` 中，以保证全局一致性。
- **交互反馈风格**：按钮 hover 采用 `translateY(-1px)` 微位移 + 加深阴影，focus 输入框使用 `box-shadow` 外发光，形成统一的“浮起”反馈语言。
- **圆角规范**：通过 `--radius-sm/md/lg/xl` 四档半径统一，Element Plus 的 `--el-border-radius-base` 与 `--el-border-radius-round` 也绑定到这些变量。
- **过渡动画**：统一使用 `cubic-bezier(0.4, 0, 0.2, 1)` 缓动，时长分 fast/base/slow 三档。
- **响应式策略**：未发现媒体查询或断点变量；当前样式以桌面端为主，侧边栏折叠通过 JS 控制宽度而非 CSS 媒体查询。
- **构建产物**：Vite 直接编译原生 CSS，无 PostCSS/Tailwind 插件链参与样式处理。