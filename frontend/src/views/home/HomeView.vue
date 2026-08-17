<script setup lang="ts">
import { Bell, Calendar, Rank, TrendCharts } from '@element-plus/icons-vue'
import { onMounted, ref, watch } from 'vue'

import { listHotPosts, listPosts, type PostItem } from '@/api/content'
import BannerCarousel, { type Banner } from '@/components/BannerCarousel.vue'
import PostCard, { type PostCardData } from '@/components/PostCard.vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

/**
 * 首页：轮播图 + 分类 Tab + 帖子信息流 + 桌面端侧栏（热榜 / 公告 / 签到）。
 * 帖子列表/热榜已接入真实接口；接口不可用时降级为演示数据。
 * TODO：接入 GET /banners、GET /posts/recommend。
 */

// 拉取站点配置（帖子图片展示开关，失败降级默认）
const { load } = useSiteConfig()
void load()

const banners = ref<Banner[]>([
  { id: 1, title: 'CloudRail 论坛正式开版', subtitle: '欢迎入驻，首个中文社区交流平台', link_type: 'announcement', link_value: '1' },
  { id: 2, title: '「技术交流」版块征文活动', subtitle: '分享你的开发经验，赢取社区积分', link_type: 'post', link_value: '1001' },
  { id: 3, title: '社区规范 v1.0 发布', subtitle: '共建友善、专业的讨论氛围', link_type: 'announcement', link_value: '2' },
])

const tabs = [
  { key: 'recommend', label: '推荐' },
  { key: 'latest', label: '最新' },
  { key: 'hot', label: '热门' },
  { key: 'essence', label: '精华' },
]
const activeTab = ref('recommend')

const posts = ref<PostCardData[]>([])
const demoPosts: PostCardData[] = [
  {
    id: 1,
    title: '欢迎使用 CloudRail 论坛',
    summary: '这里是论坛的占位示例数据。正式接入 GET /posts 接口后，将展示真实帖子列表、分类与互动数据。',
    cover: '/images/cover-1.svg',
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    view_count: 1284,
    comment_count: 36,
    like_count: 89,
    is_pinned: true,
    category: '站务公告',
    author: { id: 1, nickname: 'CloudRail' },
  },
  {
    id: 2,
    title: '开发文档 v1.3 已更新：AI 自动审核上线',
    summary: '新增 AI 内容安全审核（OpenAI 兼容协议）、Docker 合并镜像构建说明，详见 docs/开发文档.md。',
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    view_count: 860,
    comment_count: 22,
    like_count: 47,
    is_essence: true,
    category: '技术交流',
    author: { id: 2, nickname: '管理员' },
  },
  {
    id: 3,
    title: '【投票】你希望论坛优先支持哪些功能？',
    summary: '投票帖示例：话题广场、私信、深色模式、图片墙……欢迎投票并留下你的建议。',
    created_at: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    view_count: 523,
    comment_count: 64,
    like_count: 18,
    category: '生活闲聊',
    author: { id: 3, nickname: '热心网友' },
  },
  {
    id: 4,
    title: 'FastAPI 异步 SQLAlchemy 2.0 实践笔记',
    summary: '分享项目中用到的异步会话管理、迁移流程与常见踩坑，欢迎交流指正。',
    cover: '/images/cover-3.svg',
    created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    view_count: 2010,
    comment_count: 58,
    like_count: 132,
    is_essence: true,
    category: '技术交流',
    author: { id: 4, nickname: '代码搬运工' },
  },
  {
    id: 5,
    title: '匿名树洞：最近工作压力好大',
    summary: '匿名的意义在于可以放心倾诉，评论区欢迎理性交流。',
    created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    view_count: 340,
    comment_count: 41,
    like_count: 9,
    is_anonymous: true,
    category: '生活闲聊',
  },
  {
    id: 6,
    title: 'PostgreSQL 全文检索 + 中文分词方案对比',
    summary: 'pg_jieba / zhparser / 迁移 Elasticsearch 的取舍，附查询示例。',
    cover: '/images/cover-2.svg',
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    view_count: 1567,
    comment_count: 33,
    like_count: 96,
    category: '技术交流',
    author: { id: 5, nickname: '数据库老司机' },
  },
]

const hotPosts = ref([
  { id: 101, rank: 1, title: 'FastAPI 异步 SQLAlchemy 2.0 实践笔记' },
  { id: 102, rank: 2, title: '【投票】你希望论坛优先支持哪些功能？' },
  { id: 103, rank: 3, title: 'PostgreSQL 全文检索 + 中文分词方案对比' },
  { id: 104, rank: 4, title: '开发文档 v1.3 已更新：AI 自动审核上线' },
  { id: 105, rank: 5, title: '新人报到：大家好，我是刚注册的' },
])

const announcements = [
  { id: 1, title: '社区规范 v1.0 发布，请各位遵守', date: '08-16' },
  { id: 2, title: '「技术交流」版块征文活动进行中', date: '08-15' },
]

/* ---------- 真实接口接入（失败降级演示数据） ---------- */

const SORT_MAP: Record<string, string> = {
  recommend: 'latest',
  latest: 'latest',
  hot: 'hot',
  essence: 'essence',
}

function toCard(p: PostItem): PostCardData {
  return {
    id: p.id,
    title: p.title,
    summary: p.summary,
    created_at: p.created_at,
    view_count: p.view_count,
    comment_count: p.comment_count,
    like_count: p.like_count,
    is_pinned: p.is_pinned,
    is_essence: p.is_essence,
    is_anonymous: p.is_anonymous,
    category: p.category ?? undefined,
    author: p.author ? { id: p.author_id, nickname: p.author } : undefined,
  }
}

async function loadPosts() {
  try {
    const data = await listPosts({ sort: SORT_MAP[activeTab.value] ?? 'latest', limit: 20 })
    posts.value = data.items.map(toCard)
  } catch {
    posts.value = demoPosts
  }
}

async function loadHot() {
  try {
    const items = await listHotPosts(5)
    hotPosts.value = items.map((p, i) => ({ id: p.id, rank: i + 1, title: p.title }))
  } catch {
    // 保留演示热榜
  }
}

watch(activeTab, loadPosts)

onMounted(() => {
  void load()
  void loadPosts()
  void loadHot()
})
</script>

<template>
  <div class="page page-home">
    <!-- 主栏 -->
    <div class="home-main">
      <BannerCarousel :banners="banners" />

      <div class="card home-feed">
        <div class="feed-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="feed-tab"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <PostCard v-for="post in posts" :key="post.id" :post="post" />
      </div>
    </div>

    <!-- 桌面端侧栏 -->
    <aside class="home-sidebar">
      <section class="card card-pad sidebar-section">
        <h3 class="sidebar-title">
          <el-icon><TrendCharts /></el-icon>
          今日热榜
        </h3>
        <ol class="hot-list">
          <li v-for="item in hotPosts" :key="item.id" class="hot-item">
            <span class="hot-rank" :class="{ 'hot-rank--top': item.rank <= 3 }">{{ item.rank }}</span>
            <span class="hot-title">{{ item.title }}</span>
          </li>
        </ol>
      </section>

      <section class="card card-pad sidebar-section">
        <h3 class="sidebar-title">
          <el-icon><Bell /></el-icon>
          社区公告
        </h3>
        <ul class="notice-list">
          <li v-for="item in announcements" :key="item.id" class="notice-item">
            <span class="notice-title">{{ item.title }}</span>
            <span class="notice-date">{{ item.date }}</span>
          </li>
        </ul>
      </section>

      <section class="card signin-card">
        <div class="signin-info">
          <div class="signin-label">
            <el-icon><Calendar /></el-icon>
            每日签到
          </div>
          <div class="signin-streak">
            <span class="num">3</span> 天连续 · 积分 <span class="num">128</span>
          </div>
        </div>
        <el-button type="primary" round class="signin-btn">签到</el-button>
      </section>

      <section class="card card-pad sidebar-section">
        <h3 class="sidebar-title">
          <el-icon><Rank /></el-icon>
          版块导航
        </h3>
        <div class="cate-list">
          <span class="cate-chip">技术交流</span>
          <span class="cate-chip">生活闲聊</span>
          <span class="cate-chip">站务公告</span>
          <span class="cate-chip">资源分享</span>
          <span class="cate-chip">新人报到</span>
        </div>
      </section>
    </aside>
  </div>
</template>

<style scoped>
.page-home {
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--sidebar-width);
  gap: var(--space-4);
  align-items: start;
}

.home-main {
  min-width: 0;
}

/* ---- 信息流 ---- */
.home-feed {
  padding: var(--space-2) var(--space-4) var(--space-4);
}

.feed-tabs {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  margin-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border-light);
}

.feed-tab {
  padding: 6px 14px;
  border: none;
  border-radius: 999px;
  background: transparent;
  font-size: var(--font-size-md);
  color: var(--color-text-2);
  cursor: pointer;
  transition:
    color 0.15s ease,
    background 0.15s ease;
}

.feed-tab:hover {
  color: var(--color-primary);
}

.feed-tab.active {
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: 600;
}

/* ---- 侧栏 ---- */
.home-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  position: sticky;
  top: calc(var(--header-height) + var(--space-4));
}

.sidebar-section {
  padding: var(--space-4);
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-3);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.sidebar-title .el-icon {
  color: var(--color-primary);
}

.hot-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.hot-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 0;
  cursor: pointer;
}

.hot-item:hover .hot-title {
  color: var(--color-primary);
}

.hot-rank {
  width: 18px;
  flex-shrink: 0;
  text-align: center;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-3);
  font-variant-numeric: tabular-nums;
}

.hot-rank--top {
  color: var(--color-danger);
}

.hot-title {
  font-size: var(--font-size-sm);
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.15s ease;
}

.notice-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.notice-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 0;
  cursor: pointer;
}

.notice-item:hover .notice-title {
  color: var(--color-primary);
}

.notice-title {
  font-size: var(--font-size-sm);
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.15s ease;
}

.notice-date {
  flex-shrink: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
  font-variant-numeric: tabular-nums;
}

.signin-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
}

.signin-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.signin-streak {
  margin-top: 2px;
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}

.signin-btn {
  flex-shrink: 0;
}

.cate-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.cate-chip {
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--color-bg);
  color: var(--color-text-2);
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.cate-chip:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

/* ---- 响应式：<1024px 隐藏侧栏 ---- */
@media (max-width: 1023px) {
  .page-home {
    grid-template-columns: 1fr;
  }

  .home-sidebar {
    display: none;
  }
}
</style>
