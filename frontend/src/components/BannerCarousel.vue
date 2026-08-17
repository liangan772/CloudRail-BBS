<script setup lang="ts">
/**
 * 首页轮播图（文档 4.11 / 9.12）。
 * TODO：接入 GET /banners（banner:list 缓存），link_type 支持 post/topic/announcement/url。
 * 无图片时以品牌色文字卡渲染（真实运营位常配图，接接口后由 image_url 提供）。
 */
export interface Banner {
  id: number
  title: string
  subtitle?: string
  image_url?: string
  link_type: string
  link_value: string
}

withDefaults(defineProps<{ banners?: Banner[] }>(), {
  banners: () => [],
})
</script>

<template>
  <div v-if="banners.length" class="banner-carousel">
    <el-carousel height="168px" :interval="5000" indicator-position="outside" arrow="never">
      <el-carousel-item v-for="(banner, index) in banners" :key="banner.id">
        <img v-if="banner.image_url" :src="banner.image_url" :alt="banner.title" class="banner-img" loading="lazy" />
        <div v-else class="banner-text" :class="`banner-text--${(index % 3) + 1}`">
          <div class="banner-title">{{ banner.title }}</div>
          <div v-if="banner.subtitle" class="banner-subtitle">{{ banner.subtitle }}</div>
        </div>
      </el-carousel-item>
    </el-carousel>
  </div>
  <div v-else class="banner-placeholder">运营位（轮播图待接入 /banners）</div>
</template>

<style scoped>
.banner-carousel {
  margin-bottom: var(--space-4);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* 无图时的运营文字卡：深色品牌底 + 白色文字，避免花哨渐变 */
.banner-text {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--space-2);
  height: 100%;
  padding: 0 var(--space-6);
  color: #fff;
}

.banner-text--1 {
  background: #1d3f8f;
}

.banner-text--2 {
  background: #2f6bff;
}

.banner-text--3 {
  background: #14305f;
}

.banner-title {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.banner-subtitle {
  font-size: var(--font-size-sm);
  opacity: 0.85;
}

.banner-placeholder {
  height: 168px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-card);
  color: var(--color-text-3);
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-4);
}
</style>
