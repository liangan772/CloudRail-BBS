<script setup lang="ts">
import { useUnreadCount } from '@/composables/useUnreadCount'

/**
 * 消息中心（文档 4.5）：回复 / 点赞 / 关注 / 系统公告 / 私信通知。
 * TODO：接入 GET /notifications、POST /notifications/read。
 */
const { unreadCount } = useUnreadCount()
</script>

<template>
  <div class="page">
    <h2>消息</h2>
    <p class="tip">未读：{{ unreadCount }}（通知列表待接入 GET /notifications）</p>
  </div>
</template>

<style scoped>
.tip {
  color: var(--color-text-secondary);
}
</style>
