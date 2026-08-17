import http from './http'

/** 图形验证码（文档 4.1：注册/登录/发帖/评论前置）。 */
export interface CaptchaData {
  captcha_id: string
  image: string
}

export function getCaptcha() {
  return http.get<unknown, CaptchaData>('/auth/captcha')
}
