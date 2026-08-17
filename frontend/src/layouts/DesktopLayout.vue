<script setup lang="ts">
import { EditPen, Search } from '@element-plus/icons-vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const keyword = ref('')

const navs = [
  { name: 'home', label: '首页', to: '/home' },
  { name: 'topic', label: '话题', to: '/topic' },
  { name: 'notify', label: '消息', to: '/notify' },
  { name: 'me', label: '我的', to: '/me' },
]

function onSearch() {
  const q = keyword.value.trim()
  if (q) router.push({ path: '/search', query: { q } })
}

function logout() {
  userStore.logout()
  router.push('/home')
}
</script>

<template>
  <header class="desktop-header">
    <div class="brand" @click="router.push('/home')">
      <span class="brand-logo">C</span>
      <span class="brand-name">CloudRail 论坛</span>
    </div>

    <nav class="navs">
      <RouterLink v-for="nav in navs" :key="nav.name" :to="nav.to" class="nav-item">
        {{ nav.label }}
      </RouterLink>
    </nav>

    <div class="header-search">
      <el-input
        v-model="keyword"
        placeholder="搜索帖子 / 话题 / 用户"
        :prefix-icon="Search"
        clearable
        size="default"
        @keyup.enter="onSearch"
      />
    </div>

    <div class="actions">
      <el-button type="primary" :icon="EditPen" round @click="router.push('/post/create')">
        发帖
      </el-button>
      <template v-if="userStore.isLoggedIn">
        <el-dropdown trigger="click">
          <el-button round>{{ userStore.userInfo?.username || '我的' }}</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/me')">个人中心</el-dropdown-item>
              <el-dropdown-item v-if="(userStore.userInfo?.role ?? 0) >= 2" @click="router.push('/admin')">
                管理后台
              </el-dropdown-item>
              <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
      <el-button v-else round @click="router.push('/login')">登录</el-button>
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
  gap: var(--space-6);
  height: var(--header-height);
  padding: 0 var(--space-6);
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 1px 4px rgb(31 35 41 / 3%);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  flex-shrink: 0;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.brand-name {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.01em;
}

.navs {
  display: flex;
  gap: var(--space-2);
  flex: 1;
}

.nav-item {
  padding: 6px 12px;
  border-radius: var(--radius-md);
  color: var(--color-text-2);
  font-size: var(--font-size-md);
  transition:
    color 0.15s ease,
    background 0.15s ease;
}

.nav-item:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.nav-item.router-link-active {
  color: var(--color-primary);
  font-weight: 600;
  background: var(--color-primary-light);
}

.header-search {
  width: 240px;
  flex-shrink: 0;
}

.actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.desktop-body {
  min-height: calc(100% - var(--header-height));
}

@media (max-width: 1023px) {
  .desktop-header {
    gap: var(--space-3);
    padding: 0 var(--space-4);
  }

  .brand-name {
    display: none;
  }

  .header-search {
    width: 160px;
  }
}
</style>
