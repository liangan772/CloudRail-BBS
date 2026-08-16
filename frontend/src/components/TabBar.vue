<script setup lang="ts">
import { HomeFilled, Message, Plus, Star, User } from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

/**
 * 移动端底部导航栏（文档 4.12）：
 * 五 Tab：首页 / 话题 / 发帖（中间凸起主按钮）/ 消息 / 我的。
 */
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeTab = computed(() => (route.meta.tab as string) || '')

// TODO：接入 /notifications/unread-count 轮询后展示真实未读数（useUnreadCount）
const unreadCount = 0

function goPost() {
  if (!userStore.isLoggedIn) {
    router.push({ path: '/login', query: { redirect: '/post/create' } })
    return
  }
  router.push('/post/create')
}
</script>

<template>
  <nav class="tabbar">
    <RouterLink to="/home" class="tab-item" :class="{ active: activeTab === 'home' }">
      <el-icon :size="22"><HomeFilled /></el-icon>
      <span>首页</span>
    </RouterLink>

    <RouterLink to="/topic" class="tab-item" :class="{ active: activeTab === 'topic' }">
      <el-icon :size="22"><Star /></el-icon>
      <span>话题</span>
    </RouterLink>

    <!-- 中间凸起发帖主按钮 -->
    <button class="post-button" aria-label="发帖" @click="goPost">
      <el-icon :size="26"><Plus /></el-icon>
    </button>

    <RouterLink to="/notify" class="tab-item" :class="{ active: activeTab === 'notify' }">
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
        <el-icon :size="22"><Message /></el-icon>
      </el-badge>
      <span>消息</span>
    </RouterLink>

    <RouterLink to="/me" class="tab-item" :class="{ active: activeTab === 'me' }">
      <el-icon :size="22"><User /></el-icon>
      <span>我的</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: calc(var(--tabbar-height) + var(--safe-area-bottom));
  padding-bottom: var(--safe-area-bottom);
  background: var(--color-card);
  border-top: 1px solid #e5e6eb;
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 44px;
  min-height: 44px;
  justify-content: center;
  color: var(--color-text-secondary);
  font-size: 11px;
}

.tab-item.active {
  color: var(--color-primary);
}

.post-button {
  width: 48px;
  height: 48px;
  margin-top: -18px;
  border: none;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgb(47 107 255 / 40%);
  cursor: pointer;
}
</style>
