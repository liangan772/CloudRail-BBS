import http from './http'

/**
 * 管理后台 API 封装：运营看板 / 用户管理 / 内容管理 / 举报 / 敏感词 / 轮播图 / AI 审核。
 */

/* ---------- 运营看板 ---------- */

export interface StatsOverview {
  users: { total: number; today: number }
  posts: { total: number; today: number }
  comments: { total: number; today: number }
  pending_audits: number
  pending_reports: number
}

export function getStats() {
  return http.get<unknown, StatsOverview>('/admin/stats/overview')
}

/* ---------- 用户管理 ---------- */

export interface AdminUser {
  id: number
  username: string
  email: string | null
  role: number
  status: number
  points: number
  level: number
  created_at: string | null
}

export function listUsers(params: { keyword?: string; status?: number; page?: number; limit?: number } = {}) {
  return http.get<unknown, { total: number; items: AdminUser[] }>('/admin/users', { params })
}

export function updateUserStatus(id: number, status: number) {
  return http.put<unknown, { id: number; status: number }>(`/admin/users/${id}/status`, { status })
}

/* ---------- 内容管理 ---------- */

export interface AdminPost {
  id: number
  title: string
  content: string
  author_id: number
  author: string | null
  category: string | null
  status: number
  is_pinned: boolean
  is_essence: boolean
  view_count: number
  comment_count: number
  created_at: string | null
}

export function listAdminPosts(params: { status?: number; keyword?: string; page?: number; limit?: number } = {}) {
  return http.get<unknown, { total: number; items: AdminPost[] }>('/admin/posts', { params })
}

export function reviewPost(id: number, status: number) {
  return http.put<unknown, { id: number; status: number }>(`/admin/posts/${id}/review`, { status })
}

export function togglePostPin(id: number, value: boolean) {
  return http.put<unknown, { id: number; is_pinned: boolean }>(`/admin/posts/${id}/pin`, { value })
}

export function togglePostEssence(id: number, value: boolean) {
  return http.put<unknown, { id: number; is_essence: boolean }>(`/admin/posts/${id}/essence`, { value })
}

/* ---------- 举报处理 ---------- */

export interface AdminReport {
  id: number
  reporter_id: number
  reporter: string | null
  target_type: 'post' | 'comment' | 'user'
  target_id: number
  target_summary: string
  reason: string
  status: number
  handled_at: string | null
  handle_note: string
  created_at: string
}

export function listReports(params: { status?: number; page?: number; limit?: number } = {}) {
  return http.get<unknown, { total: number; items: AdminReport[] }>('/admin/reports', { params })
}

export function handleReport(id: number, action: 'ignore' | 'remove' | 'ban_user', note = '') {
  return http.put<unknown, { id: number; status: number; action: string }>(`/admin/reports/${id}`, {
    action,
    note,
  })
}

/* ---------- 敏感词管理 ---------- */

export interface SensitiveWordItem {
  id: number
  word: string
  created_at: string | null
}

export function listSensitiveWords() {
  return http.get<unknown, { total: number; items: SensitiveWordItem[] }>('/admin/sensitive-words')
}

export function createSensitiveWord(word: string) {
  return http.post<unknown, SensitiveWordItem>('/admin/sensitive-words', { word })
}

export function deleteSensitiveWord(id: number) {
  return http.delete<unknown, { deleted: boolean }>(`/admin/sensitive-words/${id}`)
}

/* ---------- 轮播图管理 ---------- */

export interface BannerItem {
  id: number
  title: string
  image_url: string
  link_url: string
  sort_order: number
  is_active: boolean
  start_at: string | null
  end_at: string | null
  created_at: string | null
}

export interface BannerPayload {
  title: string
  image_url: string
  link_url: string
  sort_order: number
  is_active: boolean
  start_at: string | null
  end_at: string | null
}

export function listAdminBanners() {
  return http.get<unknown, { total: number; items: BannerItem[] }>('/admin/banners')
}

export function createBanner(payload: BannerPayload) {
  return http.post<unknown, BannerItem>('/admin/banners', payload)
}

export function updateBanner(id: number, payload: BannerPayload) {
  return http.put<unknown, BannerItem>(`/admin/banners/${id}`, payload)
}

export function deleteBanner(id: number) {
  return http.delete<unknown, { deleted: boolean }>(`/admin/banners/${id}`)
}

/* ---------- AI 审核（人工复审队列） ---------- */

export type AuditTargetType = 'post' | 'comment' | 'image'
export type AuditResult = 'pass' | 'review' | 'reject'
export type AuditHumanStatus = 'pending' | 'approved' | 'rejected'

export interface AuditRecordItem {
  id: number
  target_type: AuditTargetType
  target_id: number | null
  content: string
  media_url: string | null
  result: AuditResult
  score: number
  categories: string[]
  reason: string
  model: string
  human_status: AuditHumanStatus
  reviewed_by: number | null
  reviewed_at: string | null
  review_note: string
  created_at: string
}

export function listAudits(params: { human_status?: string; target_type?: string; result?: string; page?: number; limit?: number } = {}) {
  return http.get<unknown, { total: number; page: number; limit: number; items: AuditRecordItem[] }>(
    '/admin/audits',
    { params },
  )
}

export function reviewAudit(id: number, action: 'approved' | 'rejected', note = '') {
  return http.put<unknown, { id: number; human_status: AuditHumanStatus }>(`/admin/audits/${id}/review`, {
    action,
    note,
  })
}
