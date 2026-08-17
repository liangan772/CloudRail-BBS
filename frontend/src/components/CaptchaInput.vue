<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import { onMounted, ref, watch } from 'vue'

import { getCaptcha, type CaptchaData } from '@/api/captcha'

/**
 * 图形验证码组件（注册/登录/发帖/评论前置，文档 4.1）。
 * v-model 输出 captcha_id + captcha_code；点击图片可刷新。
 */
const props = defineProps<{ modelValue?: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void; (e: 'captcha-ready', v: CaptchaData): void }>()

const captcha = ref<CaptchaData | null>(null)
const code = ref('')

async function refresh() {
  try {
    captcha.value = await getCaptcha()
    code.value = ''
    emit('update:modelValue', '')
    emit('captcha-ready', captcha.value)
  } catch {
    // 后端未启动时保持占位
  }
}

watch(
  () => props.modelValue,
  (v) => {
    if (v !== undefined) code.value = v
  },
)

onMounted(refresh)

// 暴露刷新方法（登录/注册失败时由父组件调用）
defineExpose({ refresh })
</script>

<template>
  <div class="captcha-row">
    <el-input v-model="code" placeholder="验证码" maxlength="4" class="captcha-input" @input="emit('update:modelValue', code)" />
    <button type="button" class="captcha-img" :title="'点击刷新'" @click="refresh">
      <img v-if="captcha" :src="captcha.image" alt="验证码" />
      <span v-else class="captcha-loading">加载中…</span>
    </button>
    <el-tooltip content="刷新验证码" placement="top">
      <el-button :icon="Refresh" circle size="small" @click="refresh" />
    </el-tooltip>
  </div>
</template>

<style scoped>
.captcha-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
}

.captcha-input {
  flex: 1;
}

.captcha-img {
  width: 110px;
  height: 36px;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-card);
  cursor: pointer;
  flex-shrink: 0;
}

.captcha-img img {
  display: block;
  width: 100%;
  height: 100%;
}

.captcha-loading {
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}
</style>
