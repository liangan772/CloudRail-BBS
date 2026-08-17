import http from './http'

/** 内容接口（帖子 / 评论 / 分类，文档 6.2）。 */

export interface Category {
  id: number
  name: string
  description?: string | null
  sort_order: number
}

export interface PostItem {
  id: number
  title: string
  content: string
  summary: string
  category_id: number
  category?: string | null
  author_id: number
  author?: string | null
  is_anonymous: boolean
  is_pinned: boolean
  is_essence: boolean
  view_count: number
  like_count: number
  comment_count: number
  created_at: string
}

export interface PostListData {
  items: PostItem[]
  next_cursor: number | null
}

export interface CommentItem {
  id: number
  post_id: number
  parent_id?: number | null
  content: string
  author?: string | null
  like_count: number
  created_at: string
}

export interface CaptchaPayload {
  captcha_id: string
  captcha_code: string
}

export function listCategories() {
  return http.get<unknown, Category[]>('/categories')
}

export function listPosts(params: { sort?: string; category_id?: number; cursor?: number; limit?: number }) {
  return http.get<unknown, PostListData>('/posts', { params })
}

export function listHotPosts(limit = 10) {
  return http.get<unknown, PostItem[]>('/posts/hot', { params: { limit } })
}

export function getPost(id: number | string) {
  return http.get<unknown, PostItem>(`/posts/${id}`)
}

export function createPost(
  payload: CaptchaPayload & { title: string; content: string; category_id: number; is_anonymous?: boolean },
) {
  return http.post<unknown, PostItem>('/posts', payload)
}

export function listComments(postId: number | string) {
  return http.get<unknown, CommentItem[]>(`/posts/${postId}/comments`)
}

export function createComment(postId: number | string, payload: CaptchaPayload & { content: string }) {
  return http.post<unknown, CommentItem>(`/posts/${postId}/comments`, payload)
}
