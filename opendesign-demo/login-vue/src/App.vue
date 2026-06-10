<script setup>
import AppNav from './components/AppNav.vue'
import ToastMsg from './components/ToastMsg.vue'
</script>

<template>
  <AppNav />
  <router-view />
  <ToastMsg />
</template>
