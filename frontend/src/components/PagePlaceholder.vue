<script setup lang="ts">
/**
 * 统一占位页：标题 + 说明 + 空状态（供待开发视图使用）。
 */
withDefaults(
  defineProps<{
    title: string
    desc?: string
    icon?: string
  }>(),
  { desc: '', icon: '📝' },
)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>{{ title }}</h2>
      <p v-if="desc" class="page-header-desc">{{ desc }}</p>
    </div>

    <div class="card empty-state">
      <div class="empty-icon" aria-hidden="true">{{ icon }}</div>
      <p>该页面功能开发中，接入对应 API 后展示真实数据</p>
      <p class="empty-desc">
        <slot />
      </p>
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  padding: var(--space-10) var(--space-4);
}

.empty-desc {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}
</style>
