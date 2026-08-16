<script setup lang="ts">
/**
 * 首页轮播图（文档 4.11 / 9.12）。
 * TODO：接入 GET /banners（banner:list 缓存），link_type 支持 post/topic/announcement/url。
 */
interface Banner {
  id: number
  title: string
  image_url: string
  link_type: string
  link_value: string
}

withDefaults(defineProps<{ banners?: Banner[] }>(), {
  banners: () => [],
})
</script>

<template>
  <div v-if="banners.length" class="banner-carousel">
    <el-carousel height="160px" indicator-position="outside">
      <el-carousel-item v-for="banner in banners" :key="banner.id">
        <img :src="banner.image_url" :alt="banner.title" class="banner-img" loading="lazy" />
      </el-carousel-item>
    </el-carousel>
  </div>
  <!-- 骨架占位：无数据时显示运营位留白 -->
  <div v-else class="banner-placeholder">运营位（轮播图待接入 /banners）</div>
</template>

<style scoped>
.banner-carousel {
  margin-bottom: 12px;
}

.banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.banner-placeholder {
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #e8ebf0;
  color: var(--color-text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}
</style>
