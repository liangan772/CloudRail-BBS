<script setup lang="ts">
import { ChatDotRound, Collection, Star, View } from '@element-plus/icons-vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { createComment, getPost, listComments, type CommentItem, type PostItem } from '@/api/content'
import CaptchaInput from '@/components/CaptchaInput.vue'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { formatCount, formatRelativeTime } from '@/utils/format'

/**
 * 帖子详情（文档 4.2 / 6.2）：正文 + 图片画廊 + 互动 + 评论区（发评论需登录 + 验证码）。
 * TODO：点赞/收藏/投票（文档 6.2）。
 */
const route = useRoute()
const router = useRouter()
const postId = String(route.params.id)

const { postImageEnabled } = useSiteConfig()
const showImages = computed(() => postImageEnabled.value)

const post = ref<PostItem | null>(null)
const comments = ref<CommentItem[]>([])
const commentForm = ref({ content: '', captcha_id: '', captcha_code: '' })
const submitting = ref(false)

// 图片占位（真实帖子无图时展示示例图；接入上传后替换）
const images = ['/images/cover-3.svg', '/images/cover-1.svg', '/images/cover-2.svg']

function onCaptchaReady(data: { captcha_id: string }) {
  commentForm.value.captcha_id = data.captcha_id
}

async function loadDetail() {
  try {
    post.value = await getPost(postId)
    comments.value = await listComments(postId)
  } catch {
    ElMessage.error('帖子加载失败')
  }
}

async function submitComment() {
  const content = commentForm.value.content.trim()
  if (!content) return ElMessage.warning('请输入评论内容')
  if (!commentForm.value.captcha_code) return ElMessage.warning('请输入验证码')
  if (!localStorage.getItem('access_token')) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }

  submitting.value = true
  try {
    await createComment(postId, {
      content,
      captcha_id: commentForm.value.captcha_id,
      captcha_code: commentForm.value.captcha_code,
    })
    commentForm.value = { content: '', captcha_id: '', captcha_code: '' }
    ElMessage.success('评论成功')
    comments.value = await listComments(postId)
  } catch {
    commentForm.value.captcha_code = ''
  } finally {
    submitting.value = false
  }
}

onMounted(loadDetail)
</script>

<template>
  <div class="page post-page">
    <article v-if="post" class="card post-detail">
      <div class="post-head">
        <div class="post-title-row">
          <span v-if="post.is_pinned" class="badge badge-pinned">置顶</span>
          <span v-if="post.is_essence" class="badge badge-essence">精华</span>
          <span v-if="post.category" class="post-category">{{ post.category }}</span>
        </div>
        <h1 class="post-title">{{ post.title }}</h1>
        <div class="post-meta">
          <span class="meta-author">
            <span class="avatar avatar--fallback">
              {{ (post.is_anonymous ? '匿' : post.author?.[0] || 'U') }}
            </span>
            {{ post.is_anonymous ? '匿名用户' : post.author || '未知用户' }}
          </span>
          <span class="meta-dot">·</span>
          <span>{{ formatRelativeTime(post.created_at) }}</span>
          <span class="meta-dot">·</span>
          <span class="meta-stat">
            <el-icon :size="14"><View /></el-icon>
            <span class="num">{{ formatCount(post.view_count) }}</span>
          </span>
          <span class="meta-stat">
            <el-icon :size="14"><ChatDotRound /></el-icon>
            <span class="num">{{ formatCount(post.comment_count) }}</span>
          </span>
        </div>
      </div>

      <!-- 正文 -->
      <div class="post-content">
        <p v-for="(line, i) in post.content.split('\n')" :key="i" :class="{ 'content-empty': !line }">
          {{ line }}
        </p>
      </div>

      <!-- 图片画廊（受后台开关控制；当前为示例图） -->
      <div v-if="showImages && images.length" class="post-images">
        <img v-for="(img, i) in images" :key="i" :src="img" :alt="`帖子图片 ${i + 1}`" class="post-image" loading="lazy" />
      </div>

      <!-- 互动条 -->
      <div class="post-actions">
        <button class="action-btn">
          <el-icon :size="16"><Star /></el-icon>
          <span class="num">{{ formatCount(post.like_count) }}</span>
        </button>
        <button class="action-btn">
          <el-icon :size="16"><Collection /></el-icon>
          收藏
        </button>
      </div>
    </article>

    <!-- 评论区 -->
    <section class="card comment-section">
      <h2 class="comment-title">评论 <span class="num">{{ comments.length }}</span></h2>

      <div class="comment-input">
        <el-input v-model="commentForm.content" type="textarea" :rows="3" maxlength="2000" placeholder="友善评论，理性交流（需登录 + 验证码）" />
        <div class="comment-captcha">
          <CaptchaInput v-model="commentForm.captcha_code" @captcha-ready="onCaptchaReady" />
        </div>
        <div class="comment-submit">
          <el-button type="primary" :loading="submitting" @click="submitComment">发表评论</el-button>
        </div>
      </div>

      <ul class="comment-list">
        <li v-for="c in comments" :key="c.id" class="comment-item">
          <span class="avatar avatar--fallback">{{ c.author?.[0] || 'U' }}</span>
          <div class="comment-body">
            <div class="comment-head">
              <span class="comment-author">{{ c.author || '未知用户' }}</span>
              <span class="comment-time">{{ formatRelativeTime(c.created_at) }}</span>
            </div>
            <p class="comment-text">{{ c.content }}</p>
            <span class="comment-like num">赞 {{ c.like_count }}</span>
          </div>
        </li>
        <li v-if="!comments.length" class="comment-empty">暂无评论，来抢沙发～</li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.post-page {
  max-width: 860px;
}

.post-detail {
  padding: var(--space-6);
}

.post-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.post-category {
  padding: 1px 10px;
  border-radius: 999px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
}

.post-title {
  margin: var(--space-3) 0;
  font-size: var(--font-size-3xl);
  font-weight: 700;
  line-height: 1.4;
}

.post-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.meta-author {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-2);
}

.avatar--fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
}

.meta-dot {
  color: var(--color-border);
}

.meta-stat {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.post-content {
  padding: var(--space-5) 0;
  font-size: var(--font-size-md);
  line-height: 1.8;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.content-empty {
  height: var(--space-3);
  margin: 0;
}

.post-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-3);
  padding-bottom: var(--space-5);
}

.post-image {
  width: 100%;
  border-radius: var(--radius-lg);
  object-fit: cover;
  aspect-ratio: 3 / 2;
  background: var(--color-bg);
}

.post-actions {
  display: flex;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-light);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 6px 16px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-card);
  color: var(--color-text-2);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease,
    background 0.15s ease;
}

.action-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.comment-section {
  margin-top: var(--space-4);
  padding: var(--space-5);
}

.comment-title {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.comment-captcha {
  max-width: 320px;
  margin-top: var(--space-2);
}

.comment-submit {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-2);
}

.comment-list {
  list-style: none;
  margin: var(--space-4) 0 0;
  padding: 0;
}

.comment-item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-top: 1px solid var(--color-border-light);
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.comment-head {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.comment-author {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.comment-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}

.comment-text {
  margin: var(--space-1) 0;
  font-size: var(--font-size-sm);
  line-height: 1.7;
  color: var(--color-text-2);
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-like {
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
  cursor: pointer;
}

.comment-empty {
  padding: var(--space-6) 0;
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-3);
  border-top: 1px solid var(--color-border-light);
}
</style>
