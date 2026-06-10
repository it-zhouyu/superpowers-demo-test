<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast.js'
import PhoneField from '../components/PhoneField.vue'
import CodeField from '../components/CodeField.vue'
import PassField from '../components/PassField.vue'

const router = useRouter()
const toast = useToast()

const step = ref(1)
const loading = ref(false)
const form = reactive({ phone: '', code: '', password: '', confirm: '' })

function next() {
  if (step.value === 1) {
    if (!form.phone || form.phone.length < 11) { toast.show('请输入正确的手机号'); return }
    if (!form.code || form.code.length < 4) { toast.show('请输入验证码'); return }
    step.value = 2
  }
}

async function finishReset() {
  if (!form.password || form.password.length < 6) { toast.show('密码至少 6 位'); return }
  if (form.password !== form.confirm) { toast.show('两次输入的密码不一致'); return }
  loading.value = true
  await new Promise(r => setTimeout(r, 1200))
  loading.value = false
  toast.show('密码重置成功')
  router.push('/login')
}

const steps = [
  { num: 1, title: '验证身份', desc: '手机号 + 验证码' },
  { num: 2, title: '设置密码', desc: '新密码' },
  { num: 3, title: '完成', desc: '重置成功' },
]
</script>

<template>
  <main class="forgot-page">
    <div class="form-shell">
      <div class="card-auth">
        <div class="header">
          <h2>忘记密码</h2>
          <div class="steps">
            <div v-for="s in steps" :key="s.num" class="step" :class="{ done: step > s.num, active: step === s.num }">
              <div class="step-num">{{ step > s.num ? '✓' : s.num }}</div>
              <span class="step-label">{{ s.title }}</span>
            </div>
          </div>
        </div>

        <!-- Step 1: Verify -->
        <div v-if="step === 1">
          <PhoneField v-model="form.phone" />
          <CodeField v-model="form.code" />
          <button class="btn-primary" @click="next">下一步</button>
        </div>

        <!-- Step 2: Set password -->
        <div v-else-if="step === 2">
          <PassField v-model="form.password" label="新密码" placeholder="至少 6 位" />
          <PassField v-model="form.confirm" label="确认密码" placeholder="再次输入新密码" />

          <button
            class="btn-primary"
            :class="{ loading: loading }"
            :disabled="loading"
            @click="finishReset"
          >
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '重置中…' : '重置密码' }}
          </button>
          <button class="btn-back" @click="step = 1">← 返回上一步</button>
        </div>

        <!-- Step 3: Done -->
        <div v-else class="done-state">
          <div class="done-icon">✓</div>
          <h3>密码重置成功</h3>
          <p>使用新密码登录即可</p>
          <router-link to="/login" class="btn-primary done-btn">返回登录</router-link>
        </div>

        <div class="bottom-link">
          <router-link to="/login">← 返回登录</router-link>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.forgot-page { padding: 60px 0; }
.header { text-align: center; margin-bottom: var(--space-8); }
.header h2 {
  font-family: var(--font-display); font-size: var(--text-2xl); font-weight: 600;
  color: var(--fg); letter-spacing: -0.01em; margin-bottom: var(--space-6);
}

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

.btn-primary {
  width: 100%; height: 50px;
  border-radius: var(--radius-pill);
  background: var(--accent); color: var(--accent-on);
  font-size: var(--text-base); font-weight: 600;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: background var(--motion-fast);
  margin-bottom: var(--space-4);
  text-decoration: none;
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

/* Done state */
.done-state { text-align: center; padding: var(--space-6) 0; }
.done-icon {
  width: 64px; height: 64px; border-radius: 50%;
  background: var(--success); color: white;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: 700;
  margin-bottom: var(--space-5);
}
.done-state h3 {
  font-family: var(--font-display); font-size: var(--text-xl); font-weight: 600;
  color: var(--fg); margin-bottom: var(--space-2);
}
.done-state p { font-size: var(--text-sm); color: var(--muted); margin-bottom: var(--space-8); }
.done-btn { display: inline-flex; width: auto; padding: 0 32px; }

.bottom-link { text-align: center; font-size: var(--text-sm); margin-top: var(--space-6); }
.bottom-link a { font-weight: 500; }

@media (max-width: 480px) {
  .forgot-page { padding: 32px 0; }
  .header { margin-bottom: var(--space-6); }
}
</style>
