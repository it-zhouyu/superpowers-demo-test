<script setup>
import { ref } from 'vue'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

const countryCode = ref('+86')
const showPicker = ref(false)
const codes = ['+86', '+852', '+853', '+886', '+1', '+44', '+81', '+82', '+65', '+60', '+66', '+91']

function selectCode(c) { countryCode.value = c; showPicker.value = false }
</script>

<template>
  <div class="phone-field">
    <label class="field-label">手机号</label>
    <div class="phone-row">
      <button type="button" class="code-btn" @click="showPicker = !showPicker">
        {{ countryCode }}
        <svg width="10" height="6" viewBox="0 0 10 6" :class="{ flip: showPicker }"><path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
      </button>
      <input
        type="tel"
        class="phone-input"
        placeholder="请输入手机号"
        maxlength="15"
        :value="modelValue"
        @input="emit('update:modelValue', $event.target.value)"
      />
    </div>
    <div v-if="showPicker" class="code-picker">
      <button v-for="c in codes" :key="c" type="button" class="code-option" :class="{ picked: c === countryCode }" @click="selectCode(c)">{{ c }}</button>
    </div>
  </div>
</template>

<style scoped>
.phone-field { margin-bottom: var(--space-5); }
.field-label {
  display: block;
  font-size: var(--text-sm); font-weight: 600;
  color: var(--fg);
  margin-bottom: var(--space-2);
}
.phone-row { display: flex; gap: var(--space-2); }
.code-btn {
  display: flex; align-items: center; gap: 4px;
  height: 48px; padding: 0 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg);
  font-size: var(--text-sm); font-weight: 500;
  color: var(--fg);
  transition: border-color var(--motion-fast);
}
.code-btn:hover, .code-btn:focus-visible { border-color: var(--accent); }
.code-btn svg { transition: transform var(--motion-fast); }
.code-btn .flip { transform: rotate(180deg); }
.phone-input {
  flex: 1; height: 48px;
  padding: 0 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  transition: border-color var(--motion-fast);
}
.phone-input:focus { border-color: var(--accent); box-shadow: var(--focus-ring); }
.phone-input::placeholder { color: var(--meta); }
.code-picker {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
  margin-top: var(--space-2);
  padding: var(--space-3);
  background: var(--surface-warm);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-soft);
}
.code-option {
  padding: 8px 4px; border-radius: 6px;
  font-size: var(--text-sm); font-weight: 500;
  color: var(--fg-2);
  transition: all var(--motion-fast);
}
.code-option:hover { background: var(--bg); }
.code-option.picked { background: var(--accent); color: var(--accent-on); font-weight: 600; }
</style>
