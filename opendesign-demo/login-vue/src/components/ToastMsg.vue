<script setup>
import { useToast } from '../composables/useToast.js'
const { msg, visible } = useToast()
</script>

<template>
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="visible" class="toast">{{ msg }}</div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.toast {
  position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
  background: var(--fg); color: var(--bg);
  font-size: var(--text-sm); font-weight: 500;
  padding: 10px 24px; border-radius: var(--radius-pill);
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
  z-index: 9999; pointer-events: none;
}
.toast-enter-active { transition: all var(--motion-base) var(--ease-standard); }
.toast-leave-active { transition: all var(--motion-fast) var(--ease-standard); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(-8px); }
</style>
