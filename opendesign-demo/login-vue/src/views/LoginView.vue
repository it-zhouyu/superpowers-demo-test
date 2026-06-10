<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast.js'
import PhoneField from '../components/PhoneField.vue'
import CodeField from '../components/CodeField.vue'

const router = useRouter()
const toast = useToast()

const form = reactive({ phone: '', code: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.phone || form.phone.length < 11) { toast.show('请输入正确的手机号'); return }
  if (!form.code || form.code.length < 4) { toast.show('请输入验证码'); return }
  loading.value = true
  await new Promise(r => setTimeout(r, 1200))
  loading.value = false
  toast.show('登录成功')
}
</script>

<template>
  <main class="login-page">
    <div class="form-shell">
      <div class="card-auth">
        <div class="header">
          <h2>登录</h2>
          <p>使用手机号 + 验证码快速登录</p>
        </div>

        <PhoneField v-model="form.phone" />
        <CodeField v-model="form.code" />

        <button
          class="btn-primary"
          :class="{ loading: loading }"
          :disabled="loading"
          @click="handleLogin"
        >
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '登录中…' : '登录' }}
        </button>

        <div class="divider"><span>或</span></div>

        <!-- Social login -->
        <div class="social">
          <button class="social-btn" @click="toast.show('Apple 登录开发中')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
            Apple 登录
          </button>
          <button class="social-btn" @click="toast.show('Google 登录开发中')">
            <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Google 登录
          </button>
        </div>

        <div class="footer-links">
          <router-link to="/register">注册账号</router-link>
          <router-link to="/forgot">忘记密码？</router-link>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.login-page { padding: 60px 0; }
.header { text-align: center; margin-bottom: var(--space-8); }
.header h2 {
  font-family: var(--font-display); font-size: var(--text-2xl); font-weight: 600;
  color: var(--fg); letter-spacing: -0.01em; margin-bottom: var(--space-2);
}
.header p { font-size: var(--text-sm); color: var(--muted); }

.btn-primary {
  width: 100%; height: 50px;
  border-radius: var(--radius-pill);
  background: var(--accent); color: var(--accent-on);
  font-size: var(--text-base); font-weight: 600;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: background var(--motion-fast);
  margin-bottom: var(--space-6);
}
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:active:not(:disabled) { background: var(--accent-active); }
.btn-primary:disabled { opacity: 0.6; cursor: default; }
.spinner {
  width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white; border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.divider {
  display: flex; align-items: center; gap: var(--space-4);
  margin-bottom: var(--space-5); color: var(--muted); font-size: var(--text-sm);
}
.divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: var(--border-soft); }
.social { display: flex; flex-direction: column; gap: var(--space-3); margin-bottom: var(--space-6); }
.social-btn {
  width: 100%; height: 48px;
  border-radius: var(--radius-pill); border: 1px solid var(--border);
  background: var(--bg);
  font-size: var(--text-sm); font-weight: 500; color: var(--fg);
  display: flex; align-items: center; justify-content: center; gap: 10px;
  transition: background var(--motion-fast);
}
.social-btn:hover { background: var(--surface-warm); }
.footer-links { display: flex; justify-content: center; gap: var(--space-6); }
.footer-links a { font-size: var(--text-sm); color: var(--accent); font-weight: 500; }

@media (max-width: 480px) {
  .login-page { padding: 32px 0; }
  .header { margin-bottom: var(--space-6); }
}
</style>
