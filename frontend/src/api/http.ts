import axios, { type AxiosError, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

/**
 * Axios 实例：统一 baseURL、Token 注入、错误提示。
 * TODO：40101 时用 refresh_token 自动刷新并重放请求（文档 6.4 认证流程）。
 */
const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error: AxiosError<{ code?: number; message?: string }>) => {
    const status = error.response?.status
    const message = error.response?.data?.message || '网络异常，请稍后重试'
    if (status === 401) {
      // 登录态失效：清理并跳转登录（TODO 接入刷新逻辑）
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    } else {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  },
)

export default http
