<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const navs = [
  { name: 'home', label: '首页', to: '/home' },
  { name: 'topic', label: '话题', to: '/topic' },
  { name: 'notify', label: '消息', to: '/notify' },
  { name: 'me', label: '我的', to: '/me' },
]
</script>

<template>
  <header class="desktop-header">
    <div class="brand" @click="router.push('/home')">CloudRail 论坛</div>
    <nav class="navs">
      <RouterLink v-for="nav in navs" :key="nav.name" :to="nav.to" class="nav-item">
        {{ nav.label }}
      </RouterLink>
    </nav>
    <div class="actions">
      <RouterLink to="/search">搜索</RouterLink>
      <RouterLink to="/announcements">公告</RouterLink>
    </div>
  </header>
  <main class="desktop-body">
    <slot />
  </main>
</template>

<style scoped>
.desktop-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 24px;
  height: 56px;
  padding: 0 24px;
  background: var(--color-card);
  border-bottom: 1px solid #e5e6eb;
}

.brand {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary);
  cursor: pointer;
}

.navs {
  display: flex;
  gap: 16px;
  flex: 1;
}

.nav-item {
  color: var(--color-text);
}

.nav-item.router-link-active {
  color: var(--color-primary);
  font-weight: 600;
}

.desktop-body {
  min-height: calc(100% - 56px);
}
</style>
