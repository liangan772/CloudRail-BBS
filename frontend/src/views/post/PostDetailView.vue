<script setup lang="ts">
import { useRoute } from 'vue-router'

/**
 * 帖子详情（文档 4.2 / 6.2）。
 * TODO：接入 GET /posts/{id}（含缓存）、评论列表、点赞/收藏/投票。
 */
const route = useRoute()
const postId = route.params.id
</script>

<template>
  <div class="page">
    <h2>帖子详情 #{{ postId }}</h2>
    <p class="tip">正文、评论、点赞、投票待接入（GET /posts/{id}）</p>
  </div>
</template>

<style scoped>
.tip {
  color: var(--color-text-secondary);
}
</style>
