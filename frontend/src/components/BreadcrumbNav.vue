<template>
  <div class="breadcrumb-nav">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ path: '/' }">
        <el-icon><HomeFilled /></el-icon>
      </el-breadcrumb-item>
      <template v-for="(item, index) in appStore.breadcrumbs" :key="index">
        <el-breadcrumb-item :to="item.path ? { path: item.path } : null">
          {{ item.title }}
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
  padding: 16px 20px;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
}
</style>
