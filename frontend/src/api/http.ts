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
  (response: AxiosResponse) => {
    // 统一业务响应 {code, message, data}：code != 0 视为业务失败
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        ElMessage.error(body.message || '请求失败')
        return Promise.reject(new Error(body.message || '请求失败'))
      }
      return body.data
    }
    return body
  },
  (error: AxiosError<{ code?: number; message?: string }>) => {
    const status = error.response?.status
    const message = error.response?.data?.message || '网络异常，请稍后重试'
    if (status === 401) {
      // 登录态失效：仅清理本地凭证，不强制跳转——由页面/守卫自行处理
      // （避免未登录访问管理接口时被重定向到不存在的 /login 而落入 404 页）
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    } else if (status !== 422) {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  },
)

export default http
