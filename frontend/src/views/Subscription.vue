<template>
  <div class="subscription-page">
    <div class="page-header">
      <h1>🔗 订阅链接</h1>
      <p>获取您的 IPTV 订阅链接</p>
    </div>
    
    <div class="subscription-container" v-loading="loading">
      <!-- M3U 订阅卡片 -->
      <el-card class="subscription-card">
        <template #header>
          <div class="card-header">
            <span>📺 M3U 订阅</span>
          </div>
        </template>
        <div class="link-section">
          <div class="link-box">
            <code>{{ urls.m3u_url || '加载中...' }}</code>
          </div>
          <div class="button-group">
            <el-button type="primary" @click="copyLink(urls.m3u_url)">
              <el-icon><CopyDocument /></el-icon>
              复制链接
            </el-button>
          </div>
        </div>
        <div class="subscribe-buttons">
          <span class="subscribe-label">📲 一键订阅到：</span>
          <div class="player-buttons">
            <el-button size="small" @click="openInPlayer('vlc', urls.m3u_url)">
              🎬 VLC
            </el-button>
            <el-button size="small" @click="openInPlayer('potplayer', urls.m3u_url)">
              🎥 PotPlayer
            </el-button>
            <el-button size="small" @click="openInPlayer('iina', urls.m3u_url)">
              🍎 IINA
            </el-button>
            <el-button size="small" @click="openInPlayer('nplayer', urls.m3u_url)">
              📱 nPlayer
            </el-button>
          </div>
        </div>
        <div class="link-tip">
          适用于大多数 IPTV 播放器，如 VLC、IPTV Pro、TiviMate 等
        </div>
      </el-card>
      
      <!-- TXT 订阅卡片 -->
      <el-card class="subscription-card">
        <template #header>
          <div class="card-header">
            <span>📄 TXT 订阅</span>
          </div>
        </template>
        <div class="link-section">
          <div class="link-box">
            <code>{{ urls.txt_url || '加载中...' }}</code>
          </div>
          <div class="button-group">
            <el-button type="primary" @click="copyLink(urls.txt_url)">
              <el-icon><CopyDocument /></el-icon>
              复制链接
            </el-button>
          </div>
        </div>
        <div class="subscribe-buttons">
          <span class="subscribe-label">📲 一键订阅到：</span>
          <div class="player-buttons">
            <el-button size="small" @click="openInPlayer('diyp', urls.txt_url)">
              📺 Diyp
            </el-button>
            <el-button size="small" @click="openInPlayer('mbox', urls.txt_url)">
              📦 影视仓
            </el-button>
          </div>
        </div>
        <div class="link-tip">
          适用于 Diyp、超级直播、影视仓等播放器
        </div>
      </el-card>
      
      <!-- Token 管理 -->
      <el-card class="subscription-card token-card">
        <template #header>
          <div class="card-header">
            <span>🔑 Token 管理</span>
          </div>
        </template>
        <div class="token-section">
          <div class="token-info">
            <span class="token-label">当前 Token</span>
            <code class="token-value">{{ urls.token || '***' }}</code>
          </div>
          <el-button type="warning" @click="resetToken" :loading="resetting">
            <el-icon><Refresh /></el-icon>
            重置 Token
          </el-button>
        </div>
        <el-alert
          type="warning"
          :closable="false"
          show-icon
        >
          重置 Token 后，旧的订阅链接将失效，需要重新配置播放器。
        </el-alert>
      </el-card>
      
      <!-- 使用说明 -->
      <el-card class="subscription-card">
        <template #header>
          <div class="card-header">
            <span>❓ 使用说明</span>
          </div>
        </template>
        <div class="instructions">
          <div class="instruction-item">
            <div class="step-number">1</div>
            <div class="step-content">
              <h4>复制订阅链接</h4>
              <p>点击上方复制按钮获取订阅链接</p>
            </div>
          </div>
          <div class="instruction-item">
            <div class="step-number">2</div>
            <div class="step-content">
              <h4>打开 IPTV 播放器</h4>
              <p>使用支持 M3U/TXT 的 IPTV 播放器</p>
            </div>
          </div>
          <div class="instruction-item">
            <div class="step-number">3</div>
            <div class="step-content">
              <h4>添加订阅源</h4>
              <p>将复制的链接粘贴到播放器的订阅设置中</p>
            </div>
          </div>
          <div class="instruction-item">
            <div class="step-number">4</div>
            <div class="step-content">
              <h4>刷新频道列表</h4>
              <p>播放器将自动获取频道列表</p>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const authStore = useAuthStore()

const loading = ref(false)
const resetting = ref(false)

const urls = reactive({
  m3u_url: '',
  txt_url: '',
  token: ''
})

async function fetchUrls() {
  loading.value = true
  try {
    const response = await api.subscription.getUrls()
    Object.assign(urls, response.data)
  } catch (error) {
    ElMessage.error('获取订阅链接失败')
  } finally {
    loading.value = false
  }
}

function copyLink(link) {
  if (!link) return
  navigator.clipboard.writeText(link)
  ElMessage.success('链接已复制到剪贴板')
}

async function resetToken() {
  try {
    await ElMessageBox.confirm(
      '重置 Token 后，当前订阅链接将失效，确定要继续吗？',
      '确认重置',
      { type: 'warning' }
    )
    resetting.value = true
    await authStore.resetToken()
    ElMessage.success('Token 已重置')
    fetchUrls()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重置失败')
    }
  } finally {
    resetting.value = false
  }
}

function openInPlayer(player, url) {
  if (!url) return
  
  let schemeUrl = ''
  
  switch (player) {
    case 'vlc':
      schemeUrl = `vlc://${url}`
      break
    case 'potplayer':
      schemeUrl = `potplayer://${url}`
      break
    case 'iina':
      schemeUrl = `iina://weblink?url=${url}`
      break
    case 'nplayer':
      const protocol = url.startsWith('https') ? 'nplayer-https' : 'nplayer-http'
      schemeUrl = url.replace(/^https?/, protocol)
      break
    case 'diyp':
    case 'mbox':
      copyLink(url)
      ElMessage.success('链接已复制，请在播放器中配置')
      return
  }
  
  if (schemeUrl) {
    window.location.href = schemeUrl
    ElMessage.success('正在尝试唤起播放器...')
  }
}

onMounted(fetchUrls)
</script>

<style scoped>
.subscription-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 6px;
}

.page-header p {
  color: var(--text-muted);
}

.subscription-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.subscription-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.link-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.link-box {
  flex: 1;
  background: var(--bg-secondary);
  padding: 12px;
  border-radius: 6px;
  font-family: monospace;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow-x: auto;
  overflow-y: hidden;
  cursor: text;
  /* 隐藏滚动条 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}

/* 隐藏 WebKit 浏览器的滚动条 */
.link-box::-webkit-scrollbar {
  display: none;
}

.link-box code {
  white-space: nowrap;
}

.subscribe-buttons {
  margin-bottom: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-color);
}

.subscribe-label {
  display: block;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.player-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.link-tip {
  font-size: 13px;
  color: var(--text-muted);
}



.token-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.token-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.token-label {
  color: var(--text-muted);
  font-size: 13px;
}

.token-value {
  color: var(--accent-primary);
  font-family: monospace;
  font-size: 14px;
}

.instructions {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.instruction-item {
  display: flex;
  gap: 16px;
}

.step-number {
  width: 32px;
  height: 32px;
  background: var(--accent-gradient);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.step-content h4 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}

.step-content p {
  color: var(--text-muted);
  font-size: 14px;
}
</style>
