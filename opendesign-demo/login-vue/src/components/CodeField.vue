<script setup>
import { ref } from 'vue'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

const countdown = ref(0)
let timer = null

function sendCode() {
  if (countdown.value > 0) return
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) { clearInterval(timer); timer = null }
  }, 1000)
}
</script>

<template>
  <div class="code-field">
    <label class="field-label">验证码</label>
    <div class="code-row">
      <input
        type="text"
        class="code-input"
        placeholder="请输入验证码"
        maxlength="6"
        inputmode="numeric"
        :value="modelValue"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button
        type="button"
        class="send-btn"
        :class="{ counting: countdown > 0 }"
        :disabled="countdown > 0"
        @click="sendCode"
      >
        {{ countdown > 0 ? `${countdown}s 后重发` : '发送验证码' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.code-field { margin-bottom: var(--space-5); }
.field-label {
  display: block;
  font-size: var(--text-sm); font-weight: 600;
  color: var(--fg);
  margin-bottom: var(--space-2);
}
.code-row { display: flex; gap: var(--space-2); }
.code-input {
  flex: 1; height: 48px;
  padding: 0 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  transition: border-color var(--motion-fast);
}
.code-input:focus { border-color: var(--accent); box-shadow: var(--focus-ring); }
.code-input::placeholder { color: var(--meta); }
.send-btn {
  height: 48px; padding: 0 16px;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm); font-weight: 500;
  background: var(--bg); color: var(--accent);
  border: 1px solid var(--accent);
  white-space: nowrap;
  transition: all var(--motion-fast);
}
.send-btn:hover:not(:disabled) { background: var(--accent); color: var(--accent-on); }
.send-btn:active:not(:disabled) { background: var(--accent-active); }
.send-btn.counting { color: var(--muted); border-color: var(--border); cursor: default; }
</style>
