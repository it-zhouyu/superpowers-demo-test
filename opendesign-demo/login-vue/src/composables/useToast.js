import { ref, readonly } from 'vue'

const msg = ref('')
const visible = ref(false)
let timer = null

export function useToast() {
  function show(text, ms = 3000) {
    clearTimeout(timer)
    msg.value = text
    visible.value = true
    timer = setTimeout(() => { visible.value = false }, ms)
  }

  return { msg: readonly(msg), visible: readonly(visible), show }
}
