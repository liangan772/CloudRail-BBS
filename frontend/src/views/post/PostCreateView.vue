<script setup lang="ts">
import { ref } from 'vue'

/**
 * 发帖（文档 4.2 / 4.11）：标题 + 富文本正文 + 分类/标签 + 投票 + 匿名 + 草稿自动保存。
 * TODO：接入 POST /posts（支持 draft_id）、POST /drafts（10s 防抖自动保存）、投票组件。
 */
const title = ref('')
const content = ref('')
const isAnonymous = ref(false)
</script>

<template>
  <div class="page">
    <h2>发帖</h2>
    <el-form label-position="top">
      <el-form-item label="标题">
        <el-input v-model="title" placeholder="请输入标题" maxlength="128" show-word-limit />
      </el-form-item>
      <el-form-item label="正文">
        <el-input v-model="content" type="textarea" :rows="8" placeholder="正文（富文本/Markdown 待接入）" />
      </el-form-item>
      <el-form-item>
        <el-switch v-model="isAnonymous" active-text="匿名发帖" />
      </el-form-item>
      <el-button type="primary">发布（待接入）</el-button>
      <el-button>存草稿（待接入）</el-button>
    </el-form>
  </div>
</template>
