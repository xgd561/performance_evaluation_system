<template>
  <el-container class="layout-container">
    <el-aside :width="appStore.sidebarCollapsed ? '64px' : '240px'" class="sidebar">
      <AppSidebar />
    </el-aside>
    <el-container class="main-wrapper">
      <el-header class="layout-header">
        <AppHeader />
      </el-header>
      <div class="breadcrumb-wrapper">
        <BreadcrumbNav />
      </div>
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="slide-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import BreadcrumbNav from '@/components/BreadcrumbNav.vue'

const appStore = useAppStore()
</script>

<style scoped>
.layout-container {
  height: 100vh;
  background: var(--bg-color);
}

.sidebar {
  background: linear-gradient(180deg, var(--bg-sidebar) 0%, #0b1120 100%);
  transition: width var(--transition-base);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.12);
  z-index: 100;
}

.main-wrapper {
  background: var(--bg-color);
}

.layout-header {
  padding: 0;
  height: auto;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-light);
  z-index: 50;
}

.breadcrumb-wrapper {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border-light);
}

.layout-main {
  background: var(--bg-color);
  padding: 24px;
  overflow-y: auto;
}

/* Slide-fade transition */
.slide-fade-enter-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(12px);
}
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}
</style>
