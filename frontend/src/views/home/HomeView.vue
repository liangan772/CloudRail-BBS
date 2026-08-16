<script setup lang="ts">
import { ref } from 'vue'

import BannerCarousel from '@/components/BannerCarousel.vue'
import PostCard, { type PostCardData } from '@/components/PostCard.vue'

/**
 * 首页：轮播图 + 推荐流 / 热门 / 最新（文档 4.11）。
 * TODO：接入 GET /banners、GET /posts/recommend、GET /posts?sort=latest|hot。
 */
const banners = ref<{ id: number; title: string; image_url: string; link_type: string; link_value: string }[]>([])

const posts = ref<PostCardData[]>([
  { id: 1, title: '欢迎使用 CloudRail 论坛（骨架占位数据）', summary: '帖子列表待接入 GET /posts 接口。', created_at: new Date().toISOString(), view_count: 128, comment_count: 6 },
  { id: 2, title: '开发文档已就绪：docs/开发文档.md', summary: '包含数据库设计、API 清单、缓存策略、部署方案。', created_at: new Date().toISOString(), view_count: 64, comment_count: 2 },
])
</script>

<template>
  <div class="page">
    <BannerCarousel :banners="banners" />
    <PostCard v-for="post in posts" :key="post.id" :post="post" />
  </div>
</template>
