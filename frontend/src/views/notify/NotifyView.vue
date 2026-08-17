<script setup lang="ts">
import PagePlaceholder from '@/components/PagePlaceholder.vue'
import { useUnreadCount } from '@/composables/useUnreadCount'

/**
 * 消息中心（文档 4.5）：回复 / 点赞 / 关注 / 系统公告 / 私信通知。
 * TODO：接入 GET /notifications、POST /notifications/read。
 */
const { unreadCount } = useUnreadCount()
</script>

<template>
  <PagePlaceholder title="消息" desc="回复、点赞、关注与系统通知" icon="💬">
    未读数：{{ unreadCount }}；待接入 GET /notifications
  </PagePlaceholder>
</template>
