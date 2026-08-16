<script setup lang="ts">
import { ref } from 'vue'

/**
 * 搜索（文档 4.4）。
 * TODO：接入 GET /posts/search?q=（全文检索）与热词 /search:hot 展示「大家都在搜」。
 */
const keyword = ref('')
</script>

<template>
  <div class="page">
    <h2>搜索</h2>
    <el-input v-model="keyword" placeholder="搜索帖子 / 用户 / 话题" clearable>
      <template #append>
        <el-button>搜索（待接入）</el-button>
      </template>
    </el-input>
  </div>
</template>
