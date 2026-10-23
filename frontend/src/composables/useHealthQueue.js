import { ref, onMounted, onBeforeUnmount } from 'vue'
import api from '@/api'

// 这里只刷新队列进度和已保存的状态，检测任务由服务端 worker 执行。
export function useHealthQueue(refresh) {
  const pendingChecks = ref(0)
  let timer
  let disposed = false

  async function refreshHealthQueue() {
    clearTimeout(timer)
    try {
      const { data } = await api.health.getStatus()
      if (disposed) return
      const wasPending = pendingChecks.value > 0
      pendingChecks.value = data.pending || 0
      if (wasPending || pendingChecks.value > 0) await refresh()
    } catch {
      // 页面原有错误提示负责连接状态；队列仍由 worker 继续执行。
    } finally {
      if (!disposed && pendingChecks.value > 0) {
        timer = setTimeout(refreshHealthQueue, 15000)
      }
    }
  }

  onMounted(refreshHealthQueue)
  onBeforeUnmount(() => {
    disposed = true
    clearTimeout(timer)
  })
  return { pendingChecks, refreshHealthQueue }
}
