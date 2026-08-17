import { computed, ref } from 'vue'

import { getSiteConfig, type SiteConfig } from '@/api/site'

/**
 * 站点配置（模块级单例缓存，全应用共享一次拉取）：
 * - postImageEnabled：帖子是否允许展示图片（后台开关，文档 v1.4）
 * - 拉取失败时降级为默认值（允许展示图片），保证离线/后端未启动时 UI 正常
 */
const config = ref<SiteConfig>({ post_image_enabled: true })
let loaded = false
let loading: Promise<void> | null = null

async function load() {
  if (loading) return loading
  loading = (async () => {
    try {
      config.value = await getSiteConfig()
    } catch {
      // 保持默认值
    } finally {
      loaded = true
    }
  })()
  return loading
}

export function useSiteConfig() {
  // 骨架阶段不自动拉取（避免每个组件触发）；由根组件/首页调用一次
  const postImageEnabled = computed(() => config.value.post_image_enabled !== false)

  return { config, postImageEnabled, loaded, load }
}
