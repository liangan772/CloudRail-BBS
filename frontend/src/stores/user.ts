import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/** 用户状态（骨架：localStorage 持久化 token；接口接入后补充用户资料拉取）。 */
export const useUserStore = defineStore('user', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const userInfo = ref<{ id: number; username: string; role: number } | null>(null)

  const isLoggedIn = computed(() => Boolean(accessToken.value))

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function logout() {
    accessToken.value = null
    userInfo.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { accessToken, userInfo, isLoggedIn, setTokens, logout }
})
