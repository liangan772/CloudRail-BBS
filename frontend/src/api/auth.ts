import http from './http'

/** 认证接口（文档 6.2 认证模块；注册/登录需图形验证码）。 */
export interface CaptchaPayload {
  captcha_id: string
  captcha_code: string
}

export interface UserOut {
  id: number
  username: string
  email?: string | null
  avatar_url?: string | null
  role: number
  points: number
  level: number
  created_at?: string | null
}

export interface AuthData {
  user: UserOut
  tokens: { access_token: string; refresh_token: string }
}

export function login(payload: CaptchaPayload & { username: string; password: string }) {
  return http.post<unknown, AuthData>('/auth/login', payload)
}

export function register(payload: CaptchaPayload & { username: string; password: string; email?: string }) {
  return http.post<unknown, AuthData>('/auth/register', payload)
}

export function refreshToken(refreshToken: string) {
  return http.post<unknown, AuthData>('/auth/refresh', { refresh_token: refreshToken })
}

export function logout() {
  return http.post<unknown, null>('/auth/logout')
}
