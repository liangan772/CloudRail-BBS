<script setup lang="ts">
import { View, ChatDotRound, Star } from '@element-plus/icons-vue'
import { computed } from 'vue'

import { useSiteConfig } from '@/composables/useSiteConfig'
import { formatCount, formatRelativeTime } from '@/utils/format'

/**
 * 帖子卡片（列表项，文档 6.5 轻量字段）。
 * TODO：接入 GET /posts 列表数据与跳转 /post/:id。
 * 封面展示受后台站点配置 post_image_enabled 控制（文档 v1.4）。
 */
export interface PostAuthor {
  id: number
  nickname: string
  avatar?: string
}

export interface PostCardData {
  id: number
  title: string
  summary?: string
  cover?: string
  created_at: string
  view_count?: number
  comment_count?: number
  like_count?: number
  is_pinned?: boolean
  is_essence?: boolean
  is_anonymous?: boolean
  category?: string
  author?: PostAuthor
}

const props = withDefaults(defineProps<{ post: PostCardData }>(), {
  post: () => ({ id: 0, title: '', created_at: '' }),
})

const { postImageEnabled } = useSiteConfig()
const showCover = computed(() => Boolean(props.post.cover) && postImageEnabled.value)
</script>

<template>
  <article class="post-card" :class="{ 'post-card--pinned': post.is_pinned }">
    <div class="post-main">
      <div class="post-title-row">
        <span v-if="post.is_pinned" class="badge badge-pinned">置顶</span>
        <span v-if="post.is_essence" class="badge badge-essence">精华</span>
        <h3 class="post-title">{{ post.title || '（无标题）' }}</h3>
      </div>

      <p v-if="post.summary" class="post-summary">{{ post.summary }}</p>

      <div class="post-meta">
        <span v-if="post.category" class="post-category">{{ post.category }}</span>
        <span class="meta-item meta-author">
          <img
            v-if="post.author?.avatar && !post.is_anonymous"
            :src="post.author.avatar"
            alt=""
            class="avatar"
          />
          <span class="avatar avatar--fallback" v-else-if="!post.is_anonymous">
            {{ (post.author?.nickname || 'U').slice(0, 1) }}
          </span>
          {{ post.is_anonymous ? '匿名用户' : post.author?.nickname || '未知用户' }}
        </span>
        <span class="meta-dot">·</span>
        <span class="meta-item">{{ formatRelativeTime(post.created_at) }}</span>
        <span v-if="post.view_count !== undefined" class="meta-item meta-stat">
          <el-icon :size="13"><View /></el-icon>
          <span class="num">{{ formatCount(post.view_count) }}</span>
        </span>
        <span v-if="post.comment_count !== undefined" class="meta-item meta-stat">
          <el-icon :size="13"><ChatDotRound /></el-icon>
          <span class="num">{{ formatCount(post.comment_count) }}</span>
        </span>
        <span v-if="post.like_count !== undefined" class="meta-item meta-stat">
          <el-icon :size="13"><Star /></el-icon>
          <span class="num">{{ formatCount(post.like_count) }}</span>
        </span>
      </div>
    </div>

    <img v-if="showCover" :src="post.cover" alt="" class="post-cover" loading="lazy" />
  </article>
</template>

<style scoped>
.post-card {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition:
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.post-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.post-card--pinned {
  background: var(--color-primary-soft);
}

.post-main {
  flex: 1;
  min-width: 0;
}

.post-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.post-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  line-height: 1.45;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.15s ease;
}

.post-card:hover .post-title {
  color: var(--color-primary);
}

.post-summary {
  margin: 0 0 var(--space-3);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  color: var(--color-text-2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}

.post-category {
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
}

.meta-author {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-2);
}

.avatar {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.avatar--fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 10px;
  font-weight: 600;
}

.meta-dot {
  color: var(--color-border);
}

.meta-stat {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.post-cover {
  width: 120px;
  height: 84px;
  border-radius: var(--radius-md);
  object-fit: cover;
  flex-shrink: 0;
  background: var(--color-bg);
}
</style>
