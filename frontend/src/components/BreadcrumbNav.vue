<template>
  <div class="breadcrumb-nav">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ path: '/' }">
        <div class="breadcrumb-home">
          <el-icon><HomeFilled /></el-icon>
        </div>
      </el-breadcrumb-item>
      <template v-for="(item, index) in appStore.breadcrumbs" :key="index">
        <el-breadcrumb-item :to="item.path ? { path: item.path } : null">
          <span class="breadcrumb-text">{{ item.title }}</span>
        </el-breadcrumb-item>
      </template>
    </el-breadcrumb>
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
</script>

<style scoped>
.breadcrumb-nav {
  padding: 14px 24px;
  background: transparent;
}

.breadcrumb-home {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: rgba(99, 102, 241, 0.08);
  color: var(--primary-color);
  transition: all var(--transition-fast);
}

.breadcrumb-home:hover {
  background: rgba(99, 102, 241, 0.15);
  transform: scale(1.1);
}

.breadcrumb-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

:deep(.el-breadcrumb__separator) {
  color: var(--border-color);
  font-weight: 500;
  margin: 0 6px;
}

:deep(.el-breadcrumb__inner.is-link) {
  color: var(--text-secondary);
  transition: color var(--transition-fast);
  font-weight: 500;
}

:deep(.el-breadcrumb__inner.is-link:hover) {
  color: var(--primary-color);
}

:deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--text-muted);
  font-weight: 500;
}
</style>
