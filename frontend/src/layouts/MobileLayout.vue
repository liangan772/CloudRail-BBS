<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import TabBar from '@/components/TabBar.vue'

const route = useRoute()
// 仅标记了 meta.tab 的页面显示底部导航栏（文档 4.12：二级页面全屏沉浸）
const showTabBar = computed(() => Boolean(route.meta.tab))
</script>

<template>
  <div class="mobile-layout">
    <main class="mobile-content">
      <slot />
    </main>
    <TabBar v-if="showTabBar" />
  </div>
</template>

<style scoped>
.mobile-layout {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.mobile-content {
  flex: 1;
  padding-bottom: calc(var(--tabbar-height) + var(--safe-area-bottom));
}
</style>
