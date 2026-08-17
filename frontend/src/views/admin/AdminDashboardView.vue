<script setup lang="ts">
import {
  Bell,
  ChatDotRound,
  Collection,
  DataAnalysis,
  Document,
  Picture,
  Setting,
  User,
  Warning,
} from '@element-plus/icons-vue'
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import http from '@/api/http'
import PagePlaceholder from '@/components/PagePlaceholder.vue'

/**
 * 管理后台（文档 4.7 / 6.2，需管理员角色）。
 * 已实现：仪表盘（统计占位）、站点配置（post_image_enabled 等开关，对接 /admin/config/site）。
 * TODO：用户/内容/举报/轮播图/话题/AI 审核/敏感词管理，接入 /admin/* 系列接口。
 */

type MenuKey =
  | 'dashboard'
  | 'config'
  | 'users'
  | 'posts'
  | 'reports'
  | 'banners'
  | 'topics'
  | 'audits'
  | 'sensitive'

const activeMenu = ref<MenuKey>('dashboard')

const menus: { key: MenuKey; label: string; icon: unknown }[] = [
  { key: 'dashboard', label: '仪表盘', icon: DataAnalysis },
  { key: 'config', label: '站点配置', icon: Setting },
  { key: 'users', label: '用户管理', icon: User },
  { key: 'posts', label: '内容管理', icon: Document },
  { key: 'reports', label: '举报处理', icon: Warning },
  { key: 'banners', label: '轮播图', icon: Picture },
  { key: 'topics', label: '话题运营', icon: ChatDotRound },
  { key: 'audits', label: 'AI 审核', icon: Collection },
  { key: 'sensitive', label: '敏感词', icon: Bell },
]

/* ---------- 仪表盘统计（演示数据，TODO 接入 /admin/stats/overview） ---------- */
const stats = [
  { label: '注册用户', value: '1,024', trend: '+12 今日' },
  { label: '帖子总数', value: '3,618', trend: '+28 今日' },
  { label: '评论总数', value: '15,902', trend: '+136 今日' },
  { label: '待审内容', value: '7', trend: '需处理' },
]

/* ---------- 站点配置 ---------- */
interface ConfigItem {
  key: string
  value: string
  description: string
}

const configItems = ref<ConfigItem[]>([
  { key: 'post_image_enabled', value: 'true', description: '帖子是否允许展示图片（帖子卡片封面与详情图片）' },
  { key: 'site_name', value: 'CloudRail 论坛', description: '站点名称（展示于页头与标题）' },
])

const configStatus = ref<'ok' | 'unauthorized' | 'error' | 'loading'>('loading')
const saving = ref(false)

const postImageEnabled = computed({
  get: () => configItems.value.find((c) => c.key === 'post_image_enabled')?.value !== 'false',
  set: (v: boolean) => {
    const item = configItems.value.find((c) => c.key === 'post_image_enabled')
    if (item) item.value = String(v)
  },
})

const siteName = computed({
  get: () => configItems.value.find((c) => c.key === 'site_name')?.value ?? '',
  set: (v: string) => {
    const item = configItems.value.find((c) => c.key === 'site_name')
    if (item) item.value = v
  },
})

async function loadConfig() {
  configStatus.value = 'loading'
  try {
    const data = await http.get<unknown, Record<string, { value: string; description: string }>>(
      '/admin/config/site',
    )
    configItems.value = Object.entries(data).map(([key, item]) => ({
      key,
      value: item.value,
      description: item.description,
    }))
    configStatus.value = 'ok'
  } catch (error) {
    const status = (error as { response?: { status?: number } }).response?.status
    configStatus.value = status === 401 ? 'unauthorized' : 'error'
    // 保留演示数据，便于预览面板
  }
}

async function saveConfig() {
  saving.value = true
  try {
    for (const item of configItems.value) {
      await http.put(`/admin/config/site/${item.key}`, { value: item.value })
    }
    ElMessage.success('站点配置已保存')
  } catch {
    ElMessage.error('保存失败：需要管理员登录且数据库可用')
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)

/* ---------- 占位页描述 ---------- */
const placeholders: Record<Exclude<MenuKey, 'dashboard' | 'config'>, { desc: string; icon: string }> = {
  users: { desc: '用户列表、禁言/封禁/解封', icon: '👥' },
  posts: { desc: '帖子/评论审核、置顶、加精', icon: '📑' },
  reports: { desc: '举报队列与处理', icon: '🚩' },
  banners: { desc: '轮播图增删改、排序、时段', icon: '🖼️' },
  topics: { desc: '话题运营、合并', icon: '🏷️' },
  audits: { desc: 'AI 审核记录与人工复核', icon: '🤖' },
  sensitive: { desc: '敏感词库维护', icon: '🔤' },
}
</script>

<template>
  <div class="admin-page">
    <!-- 侧边菜单 -->
    <aside class="admin-sidebar">
      <div class="admin-brand">管理后台</div>
      <nav class="admin-menus">
        <button
          v-for="menu in menus"
          :key="menu.key"
          class="admin-menu-item"
          :class="{ active: activeMenu === menu.key }"
          @click="activeMenu = menu.key"
        >
          <el-icon :size="16"><component :is="menu.icon" /></el-icon>
          <span>{{ menu.label }}</span>
        </button>
      </nav>
    </aside>

    <!-- 内容区 -->
    <main class="admin-content">
      <!-- 仪表盘 -->
      <template v-if="activeMenu === 'dashboard'">
        <div class="page-header">
          <h2>仪表盘</h2>
          <p class="page-header-desc">社区运营概览（接入 /admin/stats/overview 后展示真实数据）</p>
        </div>
        <div class="stat-grid">
          <div v-for="stat in stats" :key="stat.label" class="card card-pad stat-card">
            <div class="stat-label">{{ stat.label }}</div>
            <div class="stat-value num">{{ stat.value }}</div>
            <div class="stat-trend">{{ stat.trend }}</div>
          </div>
        </div>
        <div class="card empty-state chart-placeholder">
          <div class="empty-icon" aria-hidden="true">📈</div>
          <p>活跃趋势图占位（ECharts 接入后展示）</p>
        </div>
      </template>

      <!-- 站点配置 -->
      <template v-else-if="activeMenu === 'config'">
        <div class="page-header">
          <h2>站点配置</h2>
          <p class="page-header-desc">站点级开关与基础信息（存储于 site_configs 表）</p>
        </div>

        <div class="config-status">
          <el-tag
            :type="configStatus === 'ok' ? 'success' : configStatus === 'unauthorized' ? 'warning' : 'danger'"
            size="small"
          >
            {{ configStatus === 'ok' ? '已连接' : configStatus === 'unauthorized' ? '未登录（需管理员）' : '数据库不可用' }}
          </el-tag>
          <el-button v-if="configStatus !== 'ok'" size="small" text @click="loadConfig">重试</el-button>
        </div>

        <div class="card card-pad config-card">
          <div class="config-row">
            <div class="config-info">
              <div class="config-name">帖子图片展示</div>
              <div class="config-desc">
                {{ configItems.find((c) => c.key === 'post_image_enabled')?.description }}
              </div>
            </div>
            <el-switch v-model="postImageEnabled" />
          </div>

          <el-divider />

          <div class="config-row config-row--column">
            <div class="config-info">
              <div class="config-name">站点名称</div>
              <div class="config-desc">{{ configItems.find((c) => c.key === 'site_name')?.description }}</div>
            </div>
            <el-input v-model="siteName" maxlength="32" style="max-width: 320px" />
          </div>

          <div class="config-actions">
            <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
            <el-button @click="loadConfig">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 其他功能占位 -->
      <PagePlaceholder
        v-else
        :title="menus.find((m) => m.key === activeMenu)?.label ?? ''"
        :desc="placeholders[activeMenu as Exclude<MenuKey, 'dashboard' | 'config'>].desc"
        :icon="placeholders[activeMenu as Exclude<MenuKey, 'dashboard' | 'config'>].icon"
      >
        待接入 /admin/* 系列接口
      </PagePlaceholder>
    </main>
  </div>
</template>

<style scoped>
.admin-page {
  display: flex;
  min-height: calc(100vh - var(--header-height));
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--space-4);
  gap: var(--space-4);
  align-items: flex-start;
}

/* ---- 侧边菜单 ---- */
.admin-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--color-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-3);
  position: sticky;
  top: calc(var(--header-height) + var(--space-4));
}

.admin-brand {
  padding: var(--space-2) var(--space-3) var(--space-3);
  font-size: var(--font-size-lg);
  font-weight: 700;
  border-bottom: 1px solid var(--color-border-light);
  margin-bottom: var(--space-2);
}

.admin-menus {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.admin-menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: 9px var(--space-3);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  font-size: var(--font-size-base);
  color: var(--color-text-2);
  cursor: pointer;
  text-align: left;
  transition:
    color 0.15s ease,
    background 0.15s ease;
}

.admin-menu-item:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.admin-menu-item.active {
  color: var(--color-primary);
  background: var(--color-primary-light);
  font-weight: 600;
}

/* ---- 内容区 ---- */
.admin-content {
  flex: 1;
  min-width: 0;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-3);
}

.stat-value {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  line-height: 1.2;
}

.stat-trend {
  font-size: var(--font-size-xs);
  color: var(--color-success);
}

.chart-placeholder {
  min-height: 280px;
}

/* ---- 站点配置 ---- */
.config-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.config-card {
  max-width: 640px;
}

.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-2) 0;
}

.config-row--column {
  flex-direction: column;
  align-items: flex-start;
}

.config-name {
  font-size: var(--font-size-md);
  font-weight: 600;
  margin-bottom: 2px;
}

.config-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}

.config-actions {
  margin-top: var(--space-5);
  display: flex;
  gap: var(--space-3);
}

/* ---- 响应式 ---- */
@media (max-width: 1023px) {
  .admin-page {
    flex-direction: column;
  }

  .admin-sidebar {
    width: 100%;
    position: static;
  }

  .admin-menus {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .admin-menu-item {
    width: auto;
  }

  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
