<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { register } from '@/api/auth'
import CaptchaInput from '@/components/CaptchaInput.vue'
import { useUserStore } from '@/stores/user'

/**
 * 注册页：账号密码 + 图形验证码（文档 4.1 / 4.8）。
 * 所有字段必填校验（el-form rules）；注册失败自动刷新验证码。
 * 首个注册用户自动成为管理员（便于初始化后台）。
 */
const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const captchaRef = ref<InstanceType<typeof CaptchaInput>>()

const form = ref({ username: '', password: '', email: '', captcha_id: '', captcha_code: '' })
const loading = ref(false)

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 32, message: '用户名长度 2-32 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度需为 6-64 位', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (!value) return callback()
        if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
          callback(new Error('密码需同时包含字母和数字'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'input' }],
}

function onCaptchaReady(data: { captcha_id: string }) {
  form.value.captcha_id = data.captcha_id
}

async function onSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const data = await register(form.value)
    // 注册即登录
    userStore.setTokens(data.tokens.access_token, data.tokens.refresh_token)
    userStore.userInfo = { id: data.user.id, username: data.user.username, role: data.user.role }
    ElMessage.success('注册成功')
    router.push('/home')
  } catch {
    // 注册失败（用户名冲突或验证码错误）：刷新验证码并清空输入
    form.value.captcha_code = ''
    captchaRef.value?.refresh()
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="card login-card">
      <div class="login-brand">
        <span class="brand-logo">C</span>
        <span class="brand-name">CloudRail 论坛</span>
      </div>
      <h2 class="login-title">注册</h2>
      <p class="login-desc">首个注册用户自动成为管理员</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="2-32 位用户名" size="large" maxlength="32" />
        </el-form-item>
        <el-form-item label="邮箱（可选）" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" size="large" maxlength="128" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="6-64 位，需包含字母和数字"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item label="验证码" prop="captcha_code">
          <CaptchaInput
            ref="captchaRef"
            v-model="form.captcha_code"
            @captcha-ready="onCaptchaReady"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="login-submit" :loading="loading" @click="onSubmit">
          注册
        </el-button>
      </el-form>

      <div class="login-links">
        已有账号？<RouterLink to="/login">去登录</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: var(--space-10) var(--space-4);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: var(--space-8);
}

.login-brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  justify-content: center;
  margin-bottom: var(--space-5);
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: var(--font-size-xl);
  font-weight: 700;
}

.brand-name {
  font-size: var(--font-size-xl);
  font-weight: 700;
}

.login-title {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-2xl);
}

.login-desc {
  margin: var(--space-1) 0 var(--space-6);
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}

.login-submit {
  width: 100%;
  margin-top: var(--space-2);
}

.login-links {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  font-size: var(--font-size-sm);
}
</style>
