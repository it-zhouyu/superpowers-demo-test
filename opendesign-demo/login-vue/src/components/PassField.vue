<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '密码' },
  placeholder: { type: String, default: '请输入密码' },
})
const emit = defineEmits(['update:modelValue'])

const show = ref(false)
</script>

<template>
  <div class="pass-field">
    <label class="field-label">{{ label }}</label>
    <div class="pass-row">
      <input
        :type="show ? 'text' : 'password'"
        class="pass-input"
        :placeholder="placeholder"
        :value="modelValue"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button type="button" class="toggle-btn" @click="show = !show" :aria-label="show ? '隐藏密码' : '显示密码'">
        <!-- eye open -->
        <svg v-if="show" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        <!-- eye closed -->
        <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><path d="M14.12 14.12a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.pass-field { margin-bottom: var(--space-5); }
.field-label {
  display: block;
  font-size: var(--text-sm); font-weight: 600;
  color: var(--fg);
  margin-bottom: var(--space-2);
}
.pass-row { display: flex; position: relative; }
.pass-input {
  flex: 1; height: 48px;
  padding: 0 48px 0 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  transition: border-color var(--motion-fast);
}
.pass-input:focus { border-color: var(--accent); box-shadow: var(--focus-ring); }
.pass-input::placeholder { color: var(--meta); }
.toggle-btn {
  position: absolute; right: 0; top: 0;
  width: 44px; height: 48px;
  display: flex; align-items: center; justify-content: center;
  color: var(--meta);
  transition: color var(--motion-fast);
}
.toggle-btn:hover { color: var(--fg-2); }
</style>
