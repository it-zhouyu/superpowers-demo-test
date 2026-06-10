<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast.js'
import PhoneField from '../components/PhoneField.vue'
import CodeField from '../components/CodeField.vue'

const router = useRouter()
const toast = useToast()

const step = ref(1)
const loading = ref(false)
const agreed = ref(false)
const form = reactive({ phone: '', code: '', nickname: '' })

function next() {
  if (step.value === 1) {
    if (!form.phone || form.phone.length < 11) { toast.show('请输入正确的手机号'); return }
    step.value = 2
  } else if (step.value === 2) {
    if (!form.code || form.code.length < 4) { toast.show('请输入验证码'); return }
    step.value = 3
  }
}

async function finishRegister() {
  if (!form.nickname.trim()) { toast.show('请输入昵称'); return }
  if (!agreed.value) { toast.show('请同意服务条款'); return }
  loading.value = true
  await new Promise(r => setTimeout(r, 1200))
  loading.value = false
  toast.show('注册成功')
  router.push('/login')
}

const steps = [
  { num: 1, title: '验证手机', desc: '输入手机号' },
  { num: 2, title: '验证码', desc: '输入短信验证码' },
  { num: 3, title: '完成', desc: '设置昵称并同意条款' },
]
</script>

<template>
  <main class="reg-page">
    <div class="form-shell">
      <div class="card-auth">
        <div class="header">
          <h2>注册账号</h2>
          <!-- Step progress -->
          <div class="steps">
            <div v-for="s in steps" :key="s.num" class="step" :class="{ done: step > s.num, active: step === s.num }">
              <div class="step-num">{{ step > s.num ? '✓' : s.num }}</div>
              <span class="step-label">{{ s.title }}</span>
            </div>
          </div>
        </div>

        <!-- Step 1: Phone -->
        <div v-if="step === 1">
          <PhoneField v-model="form.phone" />
          <button class="btn-primary" @click="next">下一步</button>
        </div>

        <!-- Step 2: Code -->
        <div v-else-if="step === 2">
          <CodeField v-model="form.code" />
          <button class="btn-primary" @click="next">下一步</button>
          <button class="btn-back" @click="step = 1">← 返回修改手机号</button>
        </div>

        <!-- Step 3: Nickname + Agree -->
        <div v-else>
          <div class="field">
            <label class="field-label">昵称</label>
            <input
              v-model="form.nickname"
              type="text"
              class="text-input"
              placeholder="请输入您的昵称"
              maxlength="20"
            />
          </div>

          <label class="agree-row">
            <input type="checkbox" v-model="agreed" class="checkbox" />
            <span>我已阅读并同意 <a href="#" @click.prevent="toast.show('服务条款页面开发中')">服务条款</a> 和 <a href="#" @click.prevent="toast.show('隐私政策页面开发中')">隐私政策</a></span>
          </label>

          <button
            class="btn-primary"
            :class="{ loading: loading }"
            :disabled="loading"
            @click="finishRegister"
          >
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '注册中…' : '完成注册' }}
          </button>
        </div>

        <div class="bottom-link">
          <span>已有账号？</span>
          <router-link to="/login">立即登录</router-link>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.reg-page { padding: 60px 0; }
.header { text-align: center; margin-bottom: var(--space-8); }
.header h2 {
  font-family: var(--font-display); font-size: var(--text-2xl); font-weight: 600;
  color: var(--fg); letter-spacing: -0.01em; margin-bottom: var(--space-6);
}

/* Steps */
.steps { display: flex; justify-content: center; gap: var(--space-2); }
.step { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.step-num {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-sm); font-weight: 600;
  background: var(--surface-warm); color: var(--meta);
  border: 2px solid var(--border-soft);
  transition: all var(--motion-fast);
}
.step.active .step-num { background: var(--accent); color: var(--accent-on); border-color: var(--accent); }
.step.done .step-num { background: var(--success); color: white; border-color: var(--success); }
.step-label { font-size: 12px; color: var(--muted); font-weight: 500; }

/* Form */
.field { margin-bottom: var(--space-5); }
.field-label { display: block; font-size: var(--text-sm); font-weight: 600; color: var(--fg); margin-bottom: var(--space-2); }
.text-input {
  width: 100%; height: 48px; padding: 0 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  font-size: var(--text-base); color: var(--fg);
  transition: border-color var(--motion-fast);
}
.text-input:focus { border-color: var(--accent); box-shadow: var(--focus-ring); outline: none; }
.text-input::placeholder { color: var(--meta); }

.agree-row {
  display: flex; align-items: flex-start; gap: 10px;
  font-size: var(--text-sm); color: var(--muted); line-height: 1.6;
  margin-bottom: var(--space-5);
  cursor: pointer;
}
.checkbox { width: 18px; height: 18px; margin-top: 2px; accent-color: var(--accent); flex-shrink: 0; }
.agree-row a { font-weight: 500; }

.btn-primary {
  width: 100%; height: 50px;
  border-radius: var(--radius-pill);
  background: var(--accent); color: var(--accent-on);
  font-size: var(--text-base); font-weight: 600;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: background var(--motion-fast);
  margin-bottom: var(--space-4);
}
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:active:not(:disabled) { background: var(--accent-active); }
.btn-primary:disabled { opacity: 0.6; cursor: default; }
.spinner {
  width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white; border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.btn-back {
  width: 100%; height: 48px; border-radius: var(--radius-pill);
  font-size: var(--text-sm); color: var(--accent); font-weight: 500;
  transition: background var(--motion-fast);
}
.btn-back:hover { background: color-mix(in oklab, var(--accent), transparent 92%); }

.bottom-link { text-align: center; font-size: var(--text-sm); color: var(--muted); margin-top: var(--space-6); }
.bottom-link a { margin-left: 4px; font-weight: 500; }

@media (max-width: 480px) {
  .reg-page { padding: 32px 0; }
  .header { margin-bottom: var(--space-6); }
}
</style>
