<script setup>
import { useToast } from '../composables/useToast.js'
const toast = useToast()
</script>

<template>
  <main class="container">
    <!-- Hero -->
    <section class="hero">
      <h1>简洁的<span class="hl">登录体验</span></h1>
      <p>手机号 + 验证码一键登录，支持 Apple / Google 社交账号，完整覆盖登录、注册、找回密码流程。</p>
    </section>

    <!-- Screen cards -->
    <div class="screens">
      <router-link to="/login" class="screen-card">
        <div class="card-preview">
          <div class="mock">
            <div class="mock-line s"></div><div class="mock-line m"></div><div class="mock-line l"></div>
            <div class="mock-line m"></div><div class="mock-line l"></div>
            <div class="mock-btn"></div>
          </div>
        </div>
        <div class="card-body">
          <span class="card-badge">手机号 + 验证码</span>
          <h3>登录</h3>
          <p>使用手机号接收验证码快速登录，也支持 Apple 和 Google 社交账号登录。</p>
        </div>
      </router-link>

      <router-link to="/register" class="screen-card">
        <div class="card-preview">
          <div class="mock">
            <div class="mock-line s"></div><div class="mock-line m"></div><div class="mock-line l"></div>
            <div class="mock-line l"></div><div class="mock-line m"></div>
            <div class="mock-btn"></div>
          </div>
        </div>
        <div class="card-body">
          <span class="card-badge">创建账号</span>
          <h3>注册</h3>
          <p>输入手机号获取验证码，设置昵称，同意服务条款即可完成注册。</p>
        </div>
      </router-link>

      <router-link to="/forgot" class="screen-card">
        <div class="card-preview">
          <div class="mock">
            <div class="mock-line s"></div><div class="mock-line s"></div><div class="mock-line s"></div>
            <div class="mock-line m"></div><div class="mock-line l"></div>
            <div class="mock-btn"></div>
          </div>
        </div>
        <div class="card-body">
          <span class="card-badge">三步重置</span>
          <h3>忘记密码</h3>
          <p>通过手机验证码验证身份，三步完成密码重置：验证 → 设置新密码 → 完成。</p>
        </div>
      </router-link>
    </div>

    <footer class="footer">
      <span>流 登录系统 · Apple Design System · 响应式网页</span>
    </footer>
  </main>
</template>

<style scoped>
.container { max-width: var(--container-max); margin: 0 auto; padding: 0 var(--container-gutter-desktop); }
.hero { text-align: center; padding: 80px 0 48px; }
.hero h1 {
  font-family: var(--font-display); font-size: 48px; font-weight: 600;
  color: var(--fg); letter-spacing: -0.02em; line-height: 1.08; margin-bottom: 12px;
}
.hl { color: var(--accent); }
.hero p { font-size: 19px; color: var(--muted); line-height: 1.47; max-width: 480px; margin: 0 auto; }
.screens { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-6); padding-bottom: 80px; }
.screen-card {
  background: var(--bg); border-radius: var(--radius-lg); overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.03);
  transition: box-shadow var(--motion-base) var(--ease-standard), transform var(--motion-base) var(--ease-standard);
  text-decoration: none; color: inherit; display: block;
}
.screen-card:hover { box-shadow: 0 12px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04); transform: translateY(-2px); }
.screen-card:active { transform: translateY(0); }
.card-preview {
  height: 200px; background: var(--surface-warm);
  display: flex; align-items: center; justify-content: center;
  border-bottom: 1px solid var(--border-soft);
}
.mock {
  width: 240px; height: 160px; background: var(--bg);
  border-radius: var(--radius-md); box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px;
}
.mock-line { height: 8px; background: var(--border-soft); border-radius: 4px; }
.mock-line.s { width: 80px; } .mock-line.m { width: 140px; } .mock-line.l { width: 180px; }
.mock-btn { width: 160px; height: 32px; background: var(--accent); border-radius: var(--radius-pill); margin-top: 4px; }
.card-body { padding: var(--space-6); }
.card-body h3 { font-family: var(--font-display); font-size: 19px; font-weight: 600; letter-spacing: -0.01em; margin-bottom: 6px; }
.card-body p { font-size: 14px; color: var(--muted); line-height: 1.47; }
.card-badge {
  display: inline-block; font-size: 12px; font-weight: 600;
  padding: 3px 10px; border-radius: var(--radius-pill);
  background: color-mix(in oklab, var(--accent), transparent 92%); color: var(--accent);
  margin-bottom: 10px;
}
.footer { text-align: center; padding: 32px 0; border-top: 1px solid var(--border-soft); font-size: 13px; color: var(--meta); }
@media (max-width: 800px) {
  .screens { grid-template-columns: 1fr; max-width: 420px; margin: 0 auto; }
  .hero { padding: 48px 0 32px; } .hero h1 { font-size: 36px; } .hero p { font-size: 17px; }
}
@media (max-width: 480px) {
  .hero h1 { font-size: 28px; }
  .container { padding: 0 var(--container-gutter-phone); }
}
</style>
