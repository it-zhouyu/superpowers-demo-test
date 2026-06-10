import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/',         name: 'home',    component: () => import('../views/HomeView.vue') },
  { path: '/login',    name: 'login',   component: () => import('../views/LoginView.vue') },
  { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue') },
  { path: '/forgot',   name: 'forgot',  component: () => import('../views/ForgotView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
