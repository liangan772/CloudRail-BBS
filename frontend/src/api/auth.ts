import http from './http'

/** 认证接口封装（对应文档 6.2 认证模块）。 */
export interface LoginPayload {
  username: string
  password: string
  captcha?: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
}

export function login(payload: LoginPayload) {
  return http.post<unknown, { code: number; data: TokenPair }>('/auth/login', payload)
}

export function register(payload: LoginPayload & { email?: string }) {
  return http.post<unknown, { code: number; data: unknown }>('/auth/register', payload)
}

export function refreshToken(refreshToken: string) {
  return http.post<unknown, { code: number; data: TokenPair }>('/auth/refresh', {
    refresh_token: refreshToken,
  })
}
