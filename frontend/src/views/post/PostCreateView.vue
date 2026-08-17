<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { createPost, listCategories, type Category } from '@/api/content'
import CaptchaInput from '@/components/CaptchaInput.vue'

/**
 * 发帖（文档 4.2 / 4.11）：分类 + 标题 + 正文 + 匿名 + 验证码（需登录，路由守卫强制）。
 * TODO：富文本/Markdown 编辑器、草稿自动保存（POST /drafts）、投票。
 */
const router = useRouter()

const categories = ref<Category[]>([])
const form = ref({
  title: '',
  content: '',
  category_id: 0,
  is_anonymous: false,
  captcha_id: '',
  captcha_code: '',
})
const submitting = ref(false)

function onCaptchaReady(data: { captcha_id: string }) {
  form.value.captcha_id = data.captcha_id
}

async function submit() {
  if (!form.value.title.trim()) return ElMessage.warning('请输入标题')
  if (!form.value.category_id) return ElMessage.warning('请选择分类')
  if (!form.value.content.trim()) return ElMessage.warning('请输入正文')
  if (!form.value.captcha_code) return ElMessage.warning('请输入验证码')

  submitting.value = true
  try {
    const post = await createPost({
      title: form.value.title.trim(),
      content: form.value.content.trim(),
      category_id: form.value.category_id,
      is_anonymous: form.value.is_anonymous,
      captcha_id: form.value.captcha_id,
      captcha_code: form.value.captcha_code,
    })
    ElMessage.success('发布成功')
    router.push(`/post/${post.id}`)
  } catch {
    // 错误提示已由 http 拦截器处理；验证码错误时刷新
    form.value.captcha_code = ''
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    categories.value = await listCategories()
    form.value.category_id = categories.value[0]?.id ?? 0
  } catch {
    // 后端不可用时保持空分类
  }
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>发帖</h2>
      <p class="page-header-desc">分享你的观点与经验（需登录 + 验证码）</p>
    </div>

    <div class="card card-pad editor-card">
      <el-form label-position="top">
        <el-form-item label="分类">
          <el-select v-model="form.category_id" placeholder="请选择分类" style="width: 240px">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="请输入标题" maxlength="128" show-word-limit size="large" />
        </el-form-item>
        <el-form-item label="正文">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            maxlength="50000"
            placeholder="正文内容（富文本 / Markdown 编辑器待接入）"
          />
        </el-form-item>
        <el-form-item>
          <el-switch v-model="form.is_anonymous" active-text="匿名发帖" />
        </el-form-item>
        <el-form-item label="验证码">
          <CaptchaInput v-model="form.captcha_code" @captcha-ready="onCaptchaReady" />
        </el-form-item>
        <div class="editor-actions">
          <el-button type="primary" size="large" :loading="submitting" @click="submit">发布</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.editor-card {
  max-width: 720px;
}

.editor-actions {
  display: flex;
  gap: var(--space-3);
}
</style>
