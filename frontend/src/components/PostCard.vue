<script setup lang="ts">
import { formatCount, formatTime } from '@/utils/format'

/**
 * 帖子卡片（列表项，文档 6.5 轻量字段：id/title/summary/cover/created_at/stats）。
 * TODO：接入 GET /posts 列表数据与跳转 /post/:id。
 */
export interface PostCardData {
  id: number
  title: string
  summary?: string
  cover?: string
  created_at: string
  view_count?: number
  comment_count?: number
  like_count?: number
}

withDefaults(defineProps<{ post: PostCardData }>(), {
  post: () => ({ id: 0, title: '', created_at: '' }),
})
</script>

<template>
  <article class="post-card">
    <div class="post-main">
      <h3 class="post-title">{{ post.title || '（占位标题）' }}</h3>
      <p v-if="post.summary" class="post-summary">{{ post.summary }}</p>
      <div class="post-meta">
        <span>{{ formatTime(post.created_at) }}</span>
        <span v-if="post.view_count !== undefined">浏览 {{ formatCount(post.view_count) }}</span>
        <span v-if="post.comment_count !== undefined">评论 {{ formatCount(post.comment_count) }}</span>
      </div>
    </div>
    <img v-if="post.cover" :src="post.cover" alt="" class="post-cover" loading="lazy" />
  </article>
</template>

<style scoped>
.post-card {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: var(--color-card);
  border-radius: 8px;
  margin-bottom: 10px;
}

.post-main {
  flex: 1;
  min-width: 0;
}

.post-title {
  margin: 0 0 6px;
  font-size: 16px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.post-summary {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.post-cover {
  width: 96px;
  height: 72px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}
</style>
