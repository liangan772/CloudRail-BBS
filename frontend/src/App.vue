<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import DesktopLayout from '@/layouts/DesktopLayout.vue'
import MobileLayout from '@/layouts/MobileLayout.vue'

// 响应式断点：<768px 为移动端（底部 TabBar），桌面端保持顶部导航（文档 4.12）
const MOBILE_BREAKPOINT = 768
const isMobile = ref(window.innerWidth < MOBILE_BREAKPOINT)

function onResize() {
  isMobile.value = window.innerWidth < MOBILE_BREAKPOINT
}

onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<template>
  <MobileLayout v-if="isMobile">
    <RouterView />
  </MobileLayout>
  <DesktopLayout v-else>
    <RouterView />
  </DesktopLayout>
</template>
