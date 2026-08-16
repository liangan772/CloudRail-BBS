<script setup lang="ts">
/**
 * 话题广场（文档 4.11）。
 * TODO：接入 GET /topics/hot（话题热度榜）、GET /topics/{id}/posts、POST /topics/{id}/follow。
 */
</script>

<template>
  <div class="page">
    <h2>话题广场</h2>
    <p class="tip">热门话题榜待接入 GET /topics/hot</p>
  </div>
</template>

<style scoped>
.tip {
  color: var(--color-text-secondary);
}
</style>
