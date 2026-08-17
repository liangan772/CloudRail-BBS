<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import PagePlaceholder from '@/components/PagePlaceholder.vue'

/**
 * 搜索（文档 4.4）。
 * TODO：接入 GET /posts/search?q=（全文检索）与热词 /search:hot 展示「大家都在搜」。
 */
const route = useRoute()
const router = useRouter()
const keyword = ref(typeof route.query.q === 'string' ? route.query.q : '')

watch(
  () => route.query.q,
  (q) => {
    keyword.value = typeof q === 'string' ? q : ''
  },
)

function onSearch() {
  const q = keyword.value.trim()
  if (q) router.push({ path: '/search', query: { q } })
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>搜索</h2>
      <p class="page-header-desc">搜索帖子、用户与话题</p>
    </div>

    <div class="search-box">
      <el-input
        v-model="keyword"
        placeholder="输入关键词，回车搜索"
        size="large"
        clearable
        @keyup.enter="onSearch"
      >
        <template #append>
          <el-button :disabled="!keyword.trim()" @click="onSearch">搜索</el-button>
        </template>
      </el-input>
    </div>

    <PagePlaceholder title="搜索结果" desc="全文检索待接入" icon="🔍">
      <template #default>接入 GET /posts/search?q= 后展示结果与「大家都在搜」热词</template>
    </PagePlaceholder>
  </div>
</template>

<style scoped>
.search-box {
  max-width: 640px;
  margin-bottom: var(--space-5);
}
</style>
