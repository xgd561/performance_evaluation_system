<template>
  <div class="page-container">
    <div v-if="title" class="page-header">
      <h2 class="page-title">{{ title }}</h2>
      <div v-if="$slots.actions" class="page-actions">
        <slot name="actions" />
      </div>
    </div>
    <div class="page-content">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.page-container {
  padding: 20px;
  min-height: calc(100vh - var(--header-height));
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.page-content {
  background-color: #fff;
  border-radius: 4px;
  padding: 20px;
  min-height: 400px;
}
</style>
