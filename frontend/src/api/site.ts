import http from './http'

/** 站点公开配置（管理后台可配置，见 /admin/config/site）。 */
export interface SiteConfig {
  site_name?: string
  post_image_enabled?: boolean
}

export function getSiteConfig() {
  return http.get<unknown, SiteConfig>('/site-config')
}
