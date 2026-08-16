import { onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * 未读通知数（文档 9.15）：30s 轮询 /notifications/unread-count。
 * TODO：接入 API 与推送到达刷新；骨架阶段返回 0。
 */
export function useUnreadCount(pollIntervalMs = 30_000) {
  const unreadCount = ref(0)
  let timer: number | undefined

  async function refresh() {
    // unreadCount.value = (await getUnreadCount()).data
  }

  onMounted(() => {
    void refresh()
    timer = window.setInterval(refresh, pollIntervalMs)
  })

  onBeforeUnmount(() => {
    if (timer !== undefined) window.clearInterval(timer)
  })

  return { unreadCount, refresh }
}
