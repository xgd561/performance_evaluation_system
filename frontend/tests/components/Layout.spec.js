import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'

// 子组件 mock
vi.mock('@/components/AppSidebar.vue', () => ({
  default: defineComponent({ name: 'AppSidebar', template: '<div class="app-sidebar">Sidebar</div>' }),
}))
vi.mock('@/components/AppHeader.vue', () => ({
  default: defineComponent({ name: 'AppHeader', template: '<div class="app-header">Header</div>' }),
}))
vi.mock('@/components/BreadcrumbNav.vue', () => ({
  default: defineComponent({ name: 'BreadcrumbNav', template: '<div class="breadcrumb-nav">Breadcrumb</div>' }),
}))

// 路由 stub
const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: defineComponent({ template: '<div>Home</div>' }) }],
})

async function mountLayout() {
  const wrapper = mount(Layout, {
    global: {
      plugins: [createPinia(), router],
    },
  })
  await flushPromises()
  return wrapper
}

describe('P0-18 Layout.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('应渲染侧边栏、顶部栏和面包屑导航', async () => {
    const wrapper = await mountLayout()
    expect(wrapper.find('.app-sidebar').exists()).toBe(true)
    expect(wrapper.find('.app-header').exists()).toBe(true)
    expect(wrapper.find('.breadcrumb-nav').exists()).toBe(true)
  })

  it('应包含 router-view 用于内容渲染', async () => {
    const wrapper = await mountLayout()
    // router-view 被真实路由解析为当前匹配组件，transition-stub 包裹实际内容即表示 router-view 生效
    expect(wrapper.find('transition-stub').exists()).toBe(true)
    expect(wrapper.find('transition-stub').text()).toContain('Home')
  })

  it('应使用 el-container 作为根布局容器', async () => {
    const wrapper = await mountLayout()
    expect(wrapper.find('.layout-container').exists()).toBe(true)
  })

  it('侧边栏应位于 el-aside 内', async () => {
    const wrapper = await mountLayout()
    const aside = wrapper.find('.layout-container > .el-aside')
    expect(aside.exists()).toBe(true)
    expect(aside.find('.app-sidebar').exists()).toBe(true)
  })

  it('顶部栏应位于 el-header 内', async () => {
    const wrapper = await mountLayout()
    const header = wrapper.find('.layout-container .layout-header')
    expect(header.exists()).toBe(true)
    expect(header.find('.app-header').exists()).toBe(true)
  })
})
