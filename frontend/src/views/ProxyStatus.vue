<template>
  <div class="proxy-status-page">
    <div class="page-header">
      <div class="header-left">
        <h1>📡 代理状态</h1>
        <p>查看当前 IPTV 代理/转发状态</p>
      </div>
      <div class="header-actions">
        <el-button @click="fetchStatus" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>
    
    <!-- 状态概览 -->
    <div class="status-overview">
      <div class="status-card">
        <div class="status-icon">
          📡
        </div>
        <div class="status-info">
          <div class="status-value">{{ status.active_connections || 0 }}</div>
          <div class="status-label">活跃连接</div>
        </div>
      </div>
    </div>
    
    <!-- 连接列表 -->
    <el-card class="connections-card">
      <template #header>
        <div class="card-header">
          <span>🔗 活跃连接列表</span>
          <el-tag type="info" size="small">
            {{ status.connections?.length || 0 }} 个连接
          </el-tag>
        </div>
      </template>
      
      <el-table
        v-loading="loading"
        :data="status.connections || []"
        empty-text="当前没有活跃连接"
      >
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="channel_name" label="频道" min-width="200" />
        <el-table-column label="开始时间" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column label="持续时间" width="120">
          <template #default="{ row }">
            {{ getDuration(row.start_time) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 自动刷新提示 -->
    <div class="auto-refresh-tip">
      <el-icon><InfoFilled /></el-icon>
      <span>页面每 10 秒自动刷新一次</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const status = reactive({
  active_connections: 0,
  connections: []
})

let refreshTimer = null

async function fetchStatus() {
  loading.value = true
  try {
    const response = await api.proxy.getStatus()
    Object.assign(status, response.data)
  } catch (error) {
    ElMessage.error('获取代理状态失败')
  } finally {
    loading.value = false
  }
}

function formatTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

function getDuration(startTime) {
  if (!startTime) return '-'
  const start = new Date(startTime)
  const now = new Date()
  const diff = Math.floor((now - start) / 1000)
  
  if (diff < 60) return `${diff} 秒`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟`
  return `${Math.floor(diff / 3600)} 小时 ${Math.floor((diff % 3600) / 60)} 分钟`
}

onMounted(() => {
  fetchStatus()
  // 自动刷新
  refreshTimer = setInterval(fetchStatus, 10000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.proxy-status-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.page-header p {
  color: var(--text-muted);
}

.status-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.status-card {
  background: var(--bg-card);
  border-radius: var(--border-radius);
  padding: 24px;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #43e97b, #38f9d7);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.status-value {
  font-size: 36px;
  font-weight: 700;
}

.status-label {
  color: var(--text-muted);
  font-size: 14px;
}

.connections-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.auto-refresh-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
