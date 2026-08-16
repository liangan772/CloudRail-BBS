import { createRouter, createWebHistory } from 'vue-router'

/**
 * 路由表（页面与文档 4.12 底部导航栏对应）：
 * meta.tab 标记所属 Tab（home/topic/post/notify/me），TabBar 仅在标记页面显示；
 * 帖子详情、发帖编辑等二级页面不标记，自动隐藏 TabBar。
 */
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/home' },
    {
      path: '/home',
      name: 'home',
      component: () => import('@/views/home/HomeView.vue'),
      meta: { tab: 'home', title: '首页' },
    },
    {
      path: '/topic',
      name: 'topic',
      component: () => import('@/views/topic/TopicView.vue'),
      meta: { tab: 'topic', title: '话题' },
    },
    {
      path: '/post/create',
      name: 'post-create',
      component: () => import('@/views/post/PostCreateView.vue'),
      meta: { title: '发帖' },
    },
    {
      path: '/post/:id',
      name: 'post-detail',
      component: () => import('@/views/post/PostDetailView.vue'),
      meta: { title: '帖子详情' },
    },
    {
      path: '/notify',
      name: 'notify',
      component: () => import('@/views/notify/NotifyView.vue'),
      meta: { tab: 'notify', title: '消息' },
    },
    {
      path: '/me',
      name: 'me',
      component: () => import('@/views/user/UserCenterView.vue'),
      meta: { tab: 'me', title: '我的' },
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/search/SearchView.vue'),
      meta: { title: '搜索' },
    },
    {
      path: '/announcements',
      name: 'announcements',
      component: () => import('@/views/announcement/AnnouncementView.vue'),
      meta: { title: '公告' },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/admin/AdminDashboardView.vue'),
      meta: { title: '管理后台', requiresRole: 2 },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/home/HomeView.vue'),
      meta: { title: '页面不存在' },
    },
  ],
})

// 路由守卫：登录态与角色校验（TODO：接入 stores/user 后完善）
router.beforeEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - CloudRail 论坛` : 'CloudRail 论坛'
  if (to.meta.requiresRole) {
    // 骨架阶段直接放行；实现后校验用户角色并跳转登录
    return true
  }
  return true
})

export default router
