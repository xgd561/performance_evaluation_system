<template>
  <el-container class="layout-container">
    <el-aside :width="appStore.sidebarCollapsed ? '64px' : '210px'" class="sidebar">
      <AppSidebar />
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <AppHeader />
      </el-header>
      <div class="breadcrumb-wrapper">
        <BreadcrumbNav />
      </div>
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
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
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s;
}

.layout-header {
  padding: 0;
  height: auto;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.breadcrumb-wrapper {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.layout-main {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
