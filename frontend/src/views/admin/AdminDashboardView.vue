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
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import http from '@/api/http'
import {
  createBanner,
  createSensitiveWord,
  deleteBanner,
  deleteSensitiveWord,
  getStats,
  handleReport,
  listAdminBanners,
  listAdminPosts,
  listAudits,
  listReports,
  listSensitiveWords,
  listUsers,
  reviewAudit,
  reviewPost,
  togglePostEssence,
  togglePostPin,
  updateBanner,
  updateUserStatus,
  type AdminPost,
  type AdminReport,
  type AdminUser,
  type AuditRecordItem,
  type BannerItem,
  type BannerPayload,
  type SensitiveWordItem,
} from '@/api/admin'
import PagePlaceholder from '@/components/PagePlaceholder.vue'

/**
 * 管理后台（文档 4.7 / 6.2，需管理员角色）。
 * 已实现：仪表盘（真实统计）、站点配置、用户管理、内容管理、举报处理、敏感词、轮播图、AI 审核（人工复审）。
 * TODO：话题运营（/admin/topics 接口规划中）。
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

/* ---------- 仪表盘统计（对接 /admin/stats/overview） ---------- */
const stats = ref<{ label: string; value: string; trend: string }[]>([])
const statsLoading = ref(false)

async function loadStats() {
  statsLoading.value = true
  try {
    const data = await getStats()
    stats.value = [
      { label: '注册用户', value: String(data.users.total), trend: `+${data.users.today} 今日` },
      { label: '帖子总数', value: String(data.posts.total), trend: `+${data.posts.today} 今日` },
      { label: '评论总数', value: String(data.comments.total), trend: `+${data.comments.today} 今日` },
      { label: '待审内容', value: String(data.pending_audits), trend: `举报 ${data.pending_reports} 待处理` },
    ]
  } catch {
    // 未登录或接口失败：保留空态（http.ts 已提示）
    stats.value = []
  } finally {
    statsLoading.value = false
  }
}

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

onMounted(() => {
  loadConfig()
  loadStats()
  loadUsers()
  loadAdminPosts()
  loadReports()
  loadWords()
  loadBanners()
})

/* ---------- AI 审核（人工复审队列，文档 9.16 两级审核） ---------- */
const auditItems = ref<AuditRecordItem[]>([])
const auditTotal = ref(0)
const auditLoading = ref(false)
const auditPage = ref(1)
const AUDIT_PAGE_SIZE = 20

const auditFilters = ref<{ human_status: string; target_type: string; result: string }>({
  human_status: 'pending',
  target_type: '',
  result: '',
})

const reviewDialog = ref<{
  visible: boolean
  record: AuditRecordItem | null
  action: 'approved' | 'rejected'
  note: string
}>({ visible: false, record: null, action: 'approved', note: '' })
const reviewing = ref(false)

function typeLabel(t: string): string {
  return { post: '帖子', comment: '评论', image: '图片' }[t] ?? t
}

function resultLabel(r: string): string {
  return { pass: '通过', review: '转人工', reject: '拦截' }[r] ?? r
}

function humanLabel(h: string): string {
  return { pending: '待复审', approved: '已通过', rejected: '已驳回' }[h] ?? h
}

function resultTagType(r: string): 'success' | 'warning' | 'danger' | 'info' {
  return (
    { pass: 'success', review: 'warning', reject: 'danger' } as Record<
      string,
      'success' | 'warning' | 'danger' | 'info'
    >
  )[r] ?? 'info'
}

function humanTagType(h: string): 'success' | 'warning' | 'danger' | 'info' {
  return (
    { pending: 'warning', approved: 'success', rejected: 'danger' } as Record<
      string,
      'success' | 'warning' | 'danger' | 'info'
    >
  )[h] ?? 'info'
}

async function loadAudits() {
  auditLoading.value = true
  try {
    const data = await listAudits({ ...auditFilters.value, page: auditPage.value, limit: AUDIT_PAGE_SIZE })
    auditItems.value = data.items
    auditTotal.value = data.total
  } catch {
    // http.ts 已统一错误提示
  } finally {
    auditLoading.value = false
  }
}

function openReview(record: AuditRecordItem, action: 'approved' | 'rejected') {
  reviewDialog.value = { visible: true, record, action, note: '' }
}

async function submitReview() {
  const { record, action, note } = reviewDialog.value
  if (!record) return
  reviewing.value = true
  try {
    await reviewAudit(record.id, action, note)
    ElMessage.success(action === 'approved' ? '已通过，内容恢复正常展示' : '已驳回，内容已下架隐藏')
    reviewDialog.value.visible = false
    await loadAudits()
  } catch {
    // http.ts 已统一错误提示
  } finally {
    reviewing.value = false
  }
}

watch(auditFilters, () => {
  auditPage.value = 1
  loadAudits()
})

/* ---------- 用户管理（对接 /admin/users） ---------- */
const userItems = ref<AdminUser[]>([])
const userTotal = ref(0)
const userLoading = ref(false)
const userPage = ref(1)
const userKeyword = ref('')
const userStatusFilter = ref<number | undefined>(undefined)

function userStatusLabel(s: number): string {
  return { 0: '正常', 1: '禁言', 2: '封禁' }[s] ?? String(s)
}

function userStatusTag(s: number): 'success' | 'warning' | 'danger' | 'info' {
  return ({ 0: 'success', 1: 'warning', 2: 'danger' } as Record<number, 'success' | 'warning' | 'danger' | 'info'>)[s] ?? 'info'
}

async function loadUsers() {
  userLoading.value = true
  try {
    const data = await listUsers({
      keyword: userKeyword.value || undefined,
      status: userStatusFilter.value,
      page: userPage.value,
      limit: 20,
    })
    userItems.value = data.items
    userTotal.value = data.total
  } catch {
    // 已提示
  } finally {
    userLoading.value = false
  }
}

async function changeUserStatus(row: AdminUser, status: number) {
  try {
    await updateUserStatus(row.id, status)
    ElMessage.success(`已${userStatusLabel(status)}用户 ${row.username}`)
    await loadUsers()
  } catch {
    // 已提示
  }
}

function searchUsers() {
  userPage.value = 1
  loadUsers()
}

/* ---------- 内容管理（对接 /admin/posts） ---------- */
const postItems = ref<AdminPost[]>([])
const postTotal = ref(0)
const postLoading = ref(false)
const postPage = ref(1)
const postStatusFilter = ref<number | undefined>(undefined)
const postKeyword = ref('')

function postStatusLabel(s: number): string {
  return { 0: '正常', 1: '待审核', 2: '锁定', 3: '已删除' }[s] ?? String(s)
}

function postStatusTag(s: number): 'success' | 'warning' | 'danger' | 'info' {
  return (
    { 0: 'success', 1: 'warning', 2: 'danger', 3: 'info' } as Record<number, 'success' | 'warning' | 'danger' | 'info'>
  )[s] ?? 'info'
}

async function loadAdminPosts() {
  postLoading.value = true
  try {
    const data = await listAdminPosts({
      status: postStatusFilter.value,
      keyword: postKeyword.value || undefined,
      page: postPage.value,
      limit: 20,
    })
    postItems.value = data.items
    postTotal.value = data.total
  } catch {
    // 已提示
  } finally {
    postLoading.value = false
  }
}

async function changePostStatus(row: AdminPost, status: number) {
  try {
    await reviewPost(row.id, status)
    ElMessage.success(`帖子「${row.title}」已${postStatusLabel(status)}`)
    await loadAdminPosts()
  } catch {
    // 已提示
  }
}

async function togglePostFlag(row: AdminPost, flag: 'pin' | 'essence') {
  try {
    if (flag === 'pin') {
      await togglePostPin(row.id, !row.is_pinned)
      ElMessage.success(row.is_pinned ? '已取消置顶' : '已置顶')
    } else {
      await togglePostEssence(row.id, !row.is_essence)
      ElMessage.success(row.is_essence ? '已取消加精' : '已加精')
    }
    await loadAdminPosts()
  } catch {
    // 已提示
  }
}

function searchPosts() {
  postPage.value = 1
  loadAdminPosts()
}

/* ---------- 举报处理（对接 /admin/reports） ---------- */
const reportItems = ref<AdminReport[]>([])
const reportTotal = ref(0)
const reportLoading = ref(false)
const reportPage = ref(1)
const reportStatusFilter = ref(0)
const reportHandling = ref<number | null>(null)

function reportStatusLabel(s: number): string {
  return { 0: '待处理', 1: '已处理', 2: '已忽略' }[s] ?? String(s)
}

function reportTargetLabel(t: string): string {
  return { post: '帖子', comment: '评论', user: '用户' }[t] ?? t
}

async function loadReports() {
  reportLoading.value = true
  try {
    const data = await listReports({ status: reportStatusFilter.value, page: reportPage.value, limit: 20 })
    reportItems.value = data.items
    reportTotal.value = data.total
  } catch {
    // 已提示
  } finally {
    reportLoading.value = false
  }
}

async function handleReportItem(row: AdminReport, action: 'ignore' | 'remove' | 'ban_user') {
  reportHandling.value = row.id
  try {
    const labels = { ignore: '已忽略', remove: '已删除内容', ban_user: '已封禁用户' }
    await handleReport(row.id, action)
    ElMessage.success(`举报 #${row.id} ${labels[action]}`)
    await loadReports()
  } catch {
    // 已提示
  } finally {
    reportHandling.value = null
  }
}

/* ---------- 敏感词管理（对接 /admin/sensitive-words） ---------- */
const wordItems = ref<SensitiveWordItem[]>([])
const wordLoading = ref(false)
const newWord = ref('')
const wordAdding = ref(false)

async function loadWords() {
  wordLoading.value = true
  try {
    const data = await listSensitiveWords()
    wordItems.value = data.items
  } catch {
    // 已提示
  } finally {
    wordLoading.value = false
  }
}

async function addWord() {
  const word = newWord.value.trim()
  if (!word) return
  wordAdding.value = true
  try {
    await createSensitiveWord(word)
    ElMessage.success(`已添加敏感词「${word}」`)
    newWord.value = ''
    await loadWords()
  } catch {
    // 已提示（含重复词 400）
  } finally {
    wordAdding.value = false
  }
}

async function removeWord(row: SensitiveWordItem) {
  try {
    await deleteSensitiveWord(row.id)
    ElMessage.success(`已删除敏感词「${row.word}」`)
    await loadWords()
  } catch {
    // 已提示
  }
}

/* ---------- 轮播图管理（对接 /admin/banners） ---------- */
const bannerItems = ref<BannerItem[]>([])
const bannerLoading = ref(false)
const bannerDialog = ref<{ visible: boolean; editing: BannerItem | null; form: BannerPayload }>({
  visible: false,
  editing: null,
  form: { title: '', image_url: '', link_url: '', sort_order: 0, is_active: true, start_at: null, end_at: null },
})
const bannerSaving = ref(false)

async function loadBanners() {
  bannerLoading.value = true
  try {
    const data = await listAdminBanners()
    bannerItems.value = data.items
  } catch {
    // 已提示
  } finally {
    bannerLoading.value = false
  }
}

function openBannerDialog(editing: BannerItem | null = null) {
  bannerDialog.value = {
    visible: true,
    editing,
    form: editing
      ? {
          title: editing.title,
          image_url: editing.image_url,
          link_url: editing.link_url,
          sort_order: editing.sort_order,
          is_active: editing.is_active,
          start_at: editing.start_at,
          end_at: editing.end_at,
        }
      : { title: '', image_url: '', link_url: '', sort_order: 0, is_active: true, start_at: null, end_at: null },
  }
}

async function saveBanner() {
  const { editing, form } = bannerDialog.value
  if (!form.title.trim() || !form.image_url.trim()) {
    ElMessage.warning('标题与图片地址必填')
    return
  }
  bannerSaving.value = true
  try {
    if (editing) {
      await updateBanner(editing.id, form)
      ElMessage.success('轮播图已更新')
    } else {
      await createBanner(form)
      ElMessage.success('轮播图已创建')
    }
    bannerDialog.value.visible = false
    await loadBanners()
  } catch {
    // 已提示
  } finally {
    bannerSaving.value = false
  }
}

async function removeBanner(row: BannerItem) {
  try {
    await deleteBanner(row.id)
    ElMessage.success(`已删除轮播图「${row.title}」`)
    await loadBanners()
  } catch {
    // 已提示
  }
}

/* ---------- 占位页描述（仅话题运营） ---------- */
const placeholders: Record<Exclude<MenuKey, 'dashboard' | 'config' | 'audits' | 'users' | 'posts' | 'reports' | 'sensitive' | 'banners'>, { desc: string; icon: string }> = {
  topics: { desc: '话题运营、合并（/admin/topics 接口规划中）', icon: '🏷️' },
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

      <!-- AI 审核（人工复审队列） -->
      <template v-else-if="activeMenu === 'audits'">
        <div class="page-header">
          <h2>AI 审核</h2>
          <p class="page-header-desc">
            AI 初审结论进入此队列，需管理员人工复审终审；驳回将自动下架对应内容
          </p>
        </div>

        <div class="audit-filters">
          <el-select v-model="auditFilters.human_status" style="width: 130px">
            <el-option label="待复审" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="全部" value="all" />
          </el-select>
          <el-select v-model="auditFilters.target_type" style="width: 120px">
            <el-option label="全部类型" value="" />
            <el-option label="帖子" value="post" />
            <el-option label="评论" value="comment" />
            <el-option label="图片" value="image" />
          </el-select>
          <el-select v-model="auditFilters.result" style="width: 130px">
            <el-option label="全部 AI 结论" value="" />
            <el-option label="AI 通过" value="pass" />
            <el-option label="AI 转人工" value="review" />
            <el-option label="AI 拦截" value="reject" />
          </el-select>
          <el-button :loading="auditLoading" @click="loadAudits">刷新</el-button>
        </div>

        <div class="card">
          <el-table v-loading="auditLoading" :data="auditItems" style="width: 100%" empty-text="暂无审核记录">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="类型" width="76">
              <template #default="{ row }">
                <el-tag size="small">{{ typeLabel(row.target_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="内容 / 图片" min-width="240">
              <template #default="{ row }">
                <div class="audit-content-cell">
                  <el-image
                    v-if="row.media_url"
                    :src="row.media_url"
                    :preview-src-list="[row.media_url]"
                    preview-teleported
                    fit="cover"
                    class="audit-thumb"
                  />
                  <span class="audit-content-text">{{ row.content || '（无文本内容）' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="AI 结论" width="150">
              <template #default="{ row }">
                <el-tag size="small" :type="resultTagType(row.result)">{{ resultLabel(row.result) }}</el-tag>
                <div class="audit-score">违规分 {{ row.score }} · {{ row.model }}</div>
                <div v-if="row.categories.length" class="audit-cats">{{ row.categories.join('、') }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="AI 判定理由" min-width="140" show-overflow-tooltip />
            <el-table-column label="复审状态" width="92">
              <template #default="{ row }">
                <el-tag size="small" :type="humanTagType(row.human_status)">
                  {{ humanLabel(row.human_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作 / 备注" width="170" fixed="right">
              <template #default="{ row }">
                <template v-if="row.human_status === 'pending'">
                  <el-button size="small" type="success" @click="openReview(row, 'approved')">通过</el-button>
                  <el-button size="small" type="danger" @click="openReview(row, 'rejected')">驳回</el-button>
                </template>
                <span v-else class="audit-note" :title="row.review_note">
                  {{ row.review_note || (row.human_status === 'approved' ? '已通过' : '已驳回') }}
                </span>
              </template>
            </el-table-column>
          </el-table>
          <div class="audit-pagination">
            <el-pagination
              v-model:current-page="auditPage"
              :page-size="AUDIT_PAGE_SIZE"
              :total="auditTotal"
              layout="total, prev, pager, next"
              @current-change="loadAudits"
            />
          </div>
        </div>

        <el-dialog
          v-model="reviewDialog.visible"
          :title="reviewDialog.action === 'approved' ? '复审通过' : '复审驳回'"
          width="440px"
        >
          <p class="review-dialog-tip">
            目标：{{ reviewDialog.record ? typeLabel(reviewDialog.record.target_type) : '' }} #{{ reviewDialog.record?.id }}
            ｜ AI 结论：{{ reviewDialog.record ? resultLabel(reviewDialog.record.result) : '' }}
          </p>
          <el-input
            v-model="reviewDialog.note"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            placeholder="复审备注（驳回时建议填写原因）"
          />
          <template #footer>
            <el-button @click="reviewDialog.visible = false">取消</el-button>
            <el-button type="primary" :loading="reviewing" @click="submitReview">
              确认{{ reviewDialog.action === 'approved' ? '通过' : '驳回' }}
            </el-button>
          </template>
        </el-dialog>
      </template>

      <!-- 用户管理（对接 /admin/users） -->
      <template v-else-if="activeMenu === 'users'">
        <div class="page-header">
          <h2>用户管理</h2>
          <p class="page-header-desc">搜索、禁言、封禁与解封用户</p>
        </div>
        <div class="audit-filters">
          <el-input v-model="userKeyword" placeholder="搜索用户名" style="width: 200px" clearable @keyup.enter="searchUsers" />
          <el-select v-model="userStatusFilter" style="width: 120px" clearable placeholder="全部状态" @change="searchUsers">
            <el-option label="正常" :value="0" />
            <el-option label="禁言" :value="1" />
            <el-option label="封禁" :value="2" />
          </el-select>
          <el-button type="primary" @click="searchUsers">查询</el-button>
        </div>
        <div class="card">
          <el-table v-loading="userLoading" :data="userItems" style="width: 100%" empty-text="暂无用户">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="username" label="用户名" min-width="140" />
            <el-table-column prop="email" label="邮箱" min-width="160">
              <template #default="{ row }">{{ row.email || '—' }}</template>
            </el-table-column>
            <el-table-column label="角色" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.role === 2 ? 'danger' : row.role === 1 ? 'warning' : 'info'">
                  {{ { 0: '普通', 1: '版主', 2: '管理员' }[row.role as number] ?? row.role }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="userStatusTag(row.status)">{{ userStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="level" label="等级" width="70" />
            <el-table-column prop="points" label="积分" width="80" />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status !== 1">
                  <el-button size="small" @click="changeUserStatus(row, 1)">禁言</el-button>
                </template>
                <template v-if="row.status !== 2">
                  <el-button size="small" type="danger" @click="changeUserStatus(row, 2)">封禁</el-button>
                </template>
                <template v-if="row.status !== 0">
                  <el-button size="small" type="success" @click="changeUserStatus(row, 0)">解封</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
          <div class="audit-pagination">
            <el-pagination v-model:current-page="userPage" :page-size="20" :total="userTotal" layout="total, prev, pager, next" @current-change="loadUsers" />
          </div>
        </div>
      </template>

      <!-- 内容管理（对接 /admin/posts） -->
      <template v-else-if="activeMenu === 'posts'">
        <div class="page-header">
          <h2>内容管理</h2>
          <p class="page-header-desc">帖子审核（通过/下架）、置顶与加精</p>
        </div>
        <div class="audit-filters">
          <el-input v-model="postKeyword" placeholder="搜索标题" style="width: 200px" clearable @keyup.enter="searchPosts" />
          <el-select v-model="postStatusFilter" style="width: 130px" clearable placeholder="全部状态" @change="searchPosts">
            <el-option label="正常" :value="0" />
            <el-option label="待审核" :value="1" />
            <el-option label="锁定" :value="2" />
            <el-option label="已删除" :value="3" />
          </el-select>
          <el-button type="primary" @click="searchPosts">查询</el-button>
        </div>
        <div class="card">
          <el-table v-loading="postLoading" :data="postItems" style="width: 100%" empty-text="暂无帖子">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="标题" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span>{{ row.title }}</span>
                <el-tag v-if="row.is_pinned" size="small" type="danger" style="margin-left: 6px">顶</el-tag>
                <el-tag v-if="row.is_essence" size="small" type="warning" style="margin-left: 4px">精</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="author" label="作者" width="110">
              <template #default="{ row }">{{ row.author || '匿名' }}</template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="postStatusTag(row.status)">{{ postStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数据" width="110">
              <template #default="{ row }">浏览 {{ row.view_count }} · 评论 {{ row.comment_count }}</template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status !== 1">
                  <el-button size="small" @click="changePostStatus(row, 1)">下架</el-button>
                </template>
                <template v-if="row.status !== 0">
                  <el-button size="small" type="success" @click="changePostStatus(row, 0)">通过</el-button>
                </template>
                <el-button size="small" :type="row.is_pinned ? 'default' : 'danger'" @click="togglePostFlag(row, 'pin')">
                  {{ row.is_pinned ? '取消置顶' : '置顶' }}
                </el-button>
                <el-button size="small" :type="row.is_essence ? 'default' : 'warning'" @click="togglePostFlag(row, 'essence')">
                  {{ row.is_essence ? '取消加精' : '加精' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="audit-pagination">
            <el-pagination v-model:current-page="postPage" :page-size="20" :total="postTotal" layout="total, prev, pager, next" @current-change="loadAdminPosts" />
          </div>
        </div>
      </template>

      <!-- 举报处理（对接 /admin/reports） -->
      <template v-else-if="activeMenu === 'reports'">
        <div class="page-header">
          <h2>举报处理</h2>
          <p class="page-header-desc">用户举报队列：忽略 / 删除内容 / 封禁用户</p>
        </div>
        <div class="audit-filters">
          <el-select v-model="reportStatusFilter" style="width: 130px" @change="loadReports">
            <el-option label="待处理" :value="0" />
            <el-option label="已处理" :value="1" />
            <el-option label="已忽略" :value="2" />
          </el-select>
        </div>
        <div class="card">
          <el-table v-loading="reportLoading" :data="reportItems" style="width: 100%" empty-text="暂无举报">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="目标" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <el-tag size="small">{{ reportTargetLabel(row.target_type) }}</el-tag>
                <span style="margin-left: 6px">{{ row.target_summary }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="reporter" label="举报人" width="110" />
            <el-table-column prop="reason" label="举报理由" min-width="140" show-overflow-tooltip />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 0 ? 'danger' : 'info'">{{ reportStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status === 0">
                  <el-button size="small" :loading="reportHandling === row.id" @click="handleReportItem(row, 'ignore')">忽略</el-button>
                  <el-button size="small" type="warning" :loading="reportHandling === row.id" @click="handleReportItem(row, 'remove')">删内容</el-button>
                  <el-button size="small" type="danger" :loading="reportHandling === row.id" @click="handleReportItem(row, 'ban_user')">封用户</el-button>
                </template>
                <span v-else class="audit-note">{{ row.handle_note || '—' }}</span>
              </template>
            </el-table-column>
          </el-table>
          <div class="audit-pagination">
            <el-pagination v-model:current-page="reportPage" :page-size="20" :total="reportTotal" layout="total, prev, pager, next" @current-change="loadReports" />
          </div>
        </div>
      </template>

      <!-- 敏感词管理（对接 /admin/sensitive-words） -->
      <template v-else-if="activeMenu === 'sensitive'">
        <div class="page-header">
          <h2>敏感词管理</h2>
          <p class="page-header-desc">维护 DFA 敏感词库，增删即时生效（发帖/评论拦截）</p>
        </div>
        <div class="card">
          <div class="audit-filters">
            <el-input v-model="newWord" placeholder="输入新敏感词" style="width: 220px" maxlength="64" clearable @keyup.enter="addWord" />
            <el-button type="primary" :loading="wordAdding" @click="addWord">添加</el-button>
          </div>
          <el-table v-loading="wordLoading" :data="wordItems" style="width: 100%" empty-text="词库为空">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="word" label="敏感词" min-width="160" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" type="danger" @click="removeWord(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>

      <!-- 轮播图管理（对接 /admin/banners） -->
      <template v-else-if="activeMenu === 'banners'">
        <div class="page-header">
          <h2>轮播图管理</h2>
          <p class="page-header-desc">首页轮播位：图片、跳转链接、排序与启停</p>
          <el-button type="primary" @click="openBannerDialog()">新增轮播图</el-button>
        </div>
        <div class="card">
          <el-table v-loading="bannerLoading" :data="bannerItems" style="width: 100%" empty-text="暂无轮播图">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="图片" width="120">
              <template #default="{ row }">
                <el-image :src="row.image_url" fit="cover" class="banner-thumb" :preview-src-list="[row.image_url]" preview-teleported />
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="140" />
            <el-table-column prop="link_url" label="跳转链接" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.link_url || '—' }}</template>
            </el-table-column>
            <el-table-column prop="sort_order" label="排序" width="70" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openBannerDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="removeBanner(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-dialog v-model="bannerDialog.visible" :title="bannerDialog.editing ? '编辑轮播图' : '新增轮播图'" width="460px">
          <el-form label-width="90px">
            <el-form-item label="标题"><el-input v-model="bannerDialog.form.title" maxlength="64" /></el-form-item>
            <el-form-item label="图片地址"><el-input v-model="bannerDialog.form.image_url" placeholder="https://..." /></el-form-item>
            <el-form-item label="跳转链接"><el-input v-model="bannerDialog.form.link_url" placeholder="可选" /></el-form-item>
            <el-form-item label="排序"><el-input-number v-model="bannerDialog.form.sort_order" :min="0" /></el-form-item>
            <el-form-item label="启用"><el-switch v-model="bannerDialog.form.is_active" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="bannerDialog.visible = false">取消</el-button>
            <el-button type="primary" :loading="bannerSaving" @click="saveBanner">保存</el-button>
          </template>
        </el-dialog>
      </template>

      <!-- 其他功能占位 -->
      <PagePlaceholder
        v-else
        :title="menus.find((m) => m.key === activeMenu)?.label ?? ''"
        :desc="placeholders[activeMenu as Exclude<MenuKey, 'dashboard' | 'config' | 'audits' | 'users' | 'posts' | 'reports' | 'sensitive' | 'banners'>].desc"
        :icon="placeholders[activeMenu as Exclude<MenuKey, 'dashboard' | 'config' | 'audits' | 'users' | 'posts' | 'reports' | 'sensitive' | 'banners'>].icon"
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

/* ---- AI 审核 ---- */
.audit-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.audit-content-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.audit-thumb {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.audit-content-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.audit-score {
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
  margin-top: 2px;
}

.audit-cats {
  font-size: var(--font-size-xs);
  color: var(--color-danger);
}

.audit-note {
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  max-width: 150px;
}

.audit-pagination {
  margin-top: var(--space-3);
  display: flex;
  justify-content: flex-end;
}

.review-dialog-tip {
  font-size: var(--font-size-sm);
  color: var(--color-text-2);
  margin-bottom: var(--space-3);
}

.banner-thumb {
  width: 72px;
  height: 40px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
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
