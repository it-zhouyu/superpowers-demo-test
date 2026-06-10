<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <nav class="nav">
    <div class="nav-inner">
      <router-link to="/" class="nav-brand">
        <span class="dot">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="none" stroke="white" stroke-width="2"/><path d="M12 6v6l4 2" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>
        </span>
        流
      </router-link>
      <div class="nav-links">
        <router-link to="/login" :class="{ active: route.path === '/login' }">登录</router-link>
        <router-link to="/register" :class="{ active: route.path === '/register' }">注册</router-link>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.nav {
  background: rgba(255,255,255,0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--border-soft);
  position: sticky; top: 0; z-index: 100;
}
.nav-inner {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 0 var(--container-gutter-desktop);
  height: 52px;
  display: flex; align-items: center; justify-content: space-between;
}
.nav-brand {
  font-family: var(--font-display);
  font-size: 18px; font-weight: 600;
  color: var(--fg); letter-spacing: -0.01em;
  display: flex; align-items: center; gap: 10px;
  text-decoration: none;
}
.nav-brand:hover { color: var(--fg); }
.dot {
  width: 28px; height: 28px;
  background: var(--accent);
  border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
}
.dot svg { width: 16px; height: 16px; }
.nav-links { display: flex; gap: var(--space-6); }
.nav-links a {
  font-size: 14px; color: var(--fg-2); text-decoration: none;
  font-weight: 500; transition: color var(--motion-fast) var(--ease-standard);
}
.nav-links a:hover, .nav-links a.active { color: var(--accent); }
@media (max-width: 480px) {
  .nav-inner { padding: 0 var(--container-gutter-phone); }
  .nav-links { gap: 16px; }
}
</style>
