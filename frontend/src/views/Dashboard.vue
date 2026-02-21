<template>
  <div class="dashboard">
    <div class="page-header">
      <h1>📊 仪表盘</h1>
      <p>系统概览与快速统计</p>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #14b8a6, #0ea5e9);">
          📺
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.channels?.total || 0 }}</div>
          <div class="stat-label">总频道数</div>
        </div>
        <div class="stat-badge">
          活跃: {{ stats.channels?.active || 0 }}
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f97316, #fb923c);">
          📁
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.groups?.total || 0 }}</div>
          <div class="stat-label">分组数量</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #22c55e, #4ade80);">
          ✅
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.channels?.healthy || 0 }}</div>
          <div class="stat-label">健康频道</div>
        </div>
        <div class="stat-badge success">
          {{ healthPercentage }}% 可用
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #8b5cf6, #a78bfa);">
          📡
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.proxy?.active_connections || 0 }}</div>
          <div class="stat-label">活跃连接</div>
        </div>
      </div>
    </div>
    
    <!-- 观看统计区块 -->
    <div class="info-section">
      <!-- 每日观看时长图表 -->
      <div class="section-card chart-card">
        <div class="section-header">
          <h3>📈 每日观看时长</h3>
          <div class="chart-controls">
            <el-radio-group v-model="chartDays" size="small" @change="fetchWatchStats">
              <el-radio-button :value="7">7天</el-radio-button>
              <el-radio-button :value="14">14天</el-radio-button>
              <el-radio-button :value="30">30天</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div class="chart-summary">
          <span>总计: <strong>{{ formatDuration(watchStats.total_duration) }}</strong></span>
        </div>
        <div class="chart-container" v-loading="chartLoading">
          <v-chart class="chart" :option="chartOption" autoresize />
        </div>
      </div>
      
      <!-- 热门频道 -->
      <div class="section-card">
        <div class="section-header">
          <h3>🏆 热门频道</h3>
          <div class="chart-controls">
            <el-radio-group v-model="rankingDays" size="small" @change="fetchChannelRanking">
              <el-radio-button :value="7">7天</el-radio-button>
              <el-radio-button :value="14">14天</el-radio-button>
              <el-radio-button :value="30">30天</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div v-if="channelRanking.length" class="ranking-list">
          <div 
            v-for="(item, index) in channelRanking" 
            :key="item.channel_id"
            class="ranking-item"
          >
            <span class="rank-badge" :class="{ 'top-3': index < 3 }">{{ index + 1 }}</span>
            <span class="channel-name">{{ item.channel_name }}</span>
            <span class="watch-duration">{{ formatDuration(item.total_duration) }}</span>
          </div>
        </div>
        <div v-else class="empty-state">
          <span class="empty-emoji">📺</span>
          <p>暂无观看记录</p>
        </div>
      </div>
    </div>
    
    <!-- 信息区块 -->
    <div class="info-section">
      <div class="section-card">
        <h3>📊 协议分布</h3>
        <div class="protocol-list">
          <div 
            v-for="(count, protocol) in stats.protocols" 
            :key="protocol"
            class="protocol-item"
          >
            <div class="protocol-name">{{ protocol.toUpperCase() }}</div>
            <div class="protocol-bar-container">
              <div 
                class="protocol-bar" 
                :style="{ width: getProtocolPercentage(count) + '%' }"
              ></div>
            </div>
            <div class="protocol-count">{{ count }}</div>
          </div>
          <div v-if="!stats.protocols || Object.keys(stats.protocols).length === 0" class="empty-hint">
            暂无数据
          </div>
        </div>
      </div>
      
      <div class="section-card">
        <div class="section-header">
          <h3>⚠️ 不可用频道</h3>
          <el-tag v-if="stats.channels?.unhealthy > 0" type="danger" size="small">
            {{ stats.channels.unhealthy }}
          </el-tag>
        </div>
        <div v-if="stats.unhealthy_channels?.length" class="unhealthy-list">
          <div 
            v-for="channel in stats.unhealthy_channels" 
            :key="channel.id"
            class="unhealthy-item"
          >
            <span class="channel-name">{{ channel.name }}</span>
            <span class="channel-group">{{ channel.group_name || '未分组' }}</span>
          </div>
        </div>
        <div v-else class="empty-state">
          <span class="empty-emoji">✨</span>
          <p>所有频道运行正常</p>
        </div>
      </div>
    </div>
    
    <!-- 快捷操作 -->
    <div class="quick-actions">
      <h3>⚡ 快捷操作</h3>
      <div class="action-grid">
        <router-link to="/channels" class="action-item">
          <span class="action-emoji">➕</span>
          <span>添加频道</span>
        </router-link>
        <router-link to="/subscription" class="action-item">
          <span class="action-emoji">🔗</span>
          <span>获取订阅</span>
        </router-link>
        <div class="action-item" :class="{ 'is-loading': healthCheckLoading }" @click="runHealthCheck">
          <span class="action-emoji" :class="{ 'rotating': healthCheckLoading }">🔄</span>
          <span>{{ healthCheckLoading ? '检测中...' : '健康检测' }}</span>
        </div>
        <router-link to="/settings" class="action-item">
          <span class="action-emoji">⚙️</span>
          <span>系统设置</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import api from '@/api'
import { formatDate } from '@/utils/datetime'

// 注册 ECharts 组件
use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const stats = ref({})
const loading = ref(false)
const chartLoading = ref(false)
const healthCheckLoading = ref(false)
const chartDays = ref(7)
const rankingDays = ref(7)
const watchStats = ref({ stats: [], total_duration: 0 })
const channelRanking = ref([])

const healthPercentage = computed(() => {
  if (!stats.value.channels?.active) return 0
  return Math.round((stats.value.channels.healthy / stats.value.channels.active) * 100)
})

// 图表配置
const chartOption = computed(() => {
  const data = watchStats.value.stats || []
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const item = params[0]
        return `${item.name}<br/>观看时长: ${formatDuration(item.value)}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10px',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map(item => formatDate(item.date, 'M/D')),
      axisLine: { lineStyle: { color: '#64748b' } },
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      min: 0,
      minInterval: 60,
      axisLine: { show: false },
      axisLabel: {
        color: '#64748b',
        formatter: (value) => {
          if (value === 0) return '0'
          return formatDuration(value, true)
        }
      },
      splitLine: { lineStyle: { color: 'rgba(100, 116, 139, 0.2)' } }
    },
    series: [{
      name: '观看时长',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: data.map(item => item.duration),
      lineStyle: { color: '#14b8a6', width: 3 },
      itemStyle: { color: '#14b8a6' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(20, 184, 166, 0.3)' },
            { offset: 1, color: 'rgba(20, 184, 166, 0.05)' }
          ]
        }
      }
    }]
  }
})

function formatDuration(seconds, short = false) {
  if (!seconds || seconds <= 0) return short ? '0' : '0 分钟'
  if (seconds < 60) return short ? '1m' : '1 分钟'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (short) {
    if (hours > 0) return `${hours}h`
    return `${minutes}m`
  }
  if (hours > 0) {
    return `${hours} 小时 ${minutes} 分钟`
  }
  return `${minutes} 分钟`
}

function getProtocolPercentage(count) {
  const total = stats.value.channels?.total || 1
  return Math.round((count / total) * 100)
}

async function fetchDashboard() {
  loading.value = true
  try {
    const response = await api.dashboard.get()
    stats.value = response.data
  } catch (error) {
    ElMessage.error('获取仪表盘数据失败')
  } finally {
    loading.value = false
  }
}

async function fetchWatchStats() {
  chartLoading.value = true
  try {
    const response = await api.dashboard.getWatchStats(chartDays.value)
    watchStats.value = response.data
  } catch (error) {
    console.error('获取观看统计失败', error)
  } finally {
    chartLoading.value = false
  }
}

async function fetchChannelRanking() {
  try {
    const response = await api.dashboard.getChannelRanking(rankingDays.value, 10)
    channelRanking.value = response.data.ranking || []
  } catch (error) {
    console.error('获取频道排名失败', error)
  }
}

async function runHealthCheck() {
  if (healthCheckLoading.value) {
    ElMessage.warning('健康检测正在进行中，请稍候...')
    return
  }

  healthCheckLoading.value = true
  try {
    ElMessage.info('正在进行健康检测...')
    const result = await api.health.checkAll()
    const data = result.data
    ElMessage.success(`检测完成：正常 ${data.healthy} 个，异常 ${data.unhealthy} 个`)
    fetchDashboard()
  } catch (error) {
    ElMessage.error('健康检测失败')
  } finally {
    healthCheckLoading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
  fetchWatchStats()
  fetchChannelRanking()
})
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
}

.page-header h1 {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 6px;
}

.page-header p {
  color: var(--text-muted);
  font-size: 14px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 28px;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  background: var(--bg-card);
  border-radius: var(--border-radius);
  padding: 20px;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  color: var(--text-muted);
  font-size: 13px;
  margin-top: 2px;
}

.stat-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 3px 8px;
  border-radius: 4px;
}

.stat-badge.success {
  color: var(--success);
  background: rgba(34, 197, 94, 0.1);
}

/* 图表区域 */
.chart-section {
  margin-bottom: 28px;
}

.chart-card {
  min-height: 320px;
}

.chart-controls {
  display: flex;
  gap: 8px;
}

.chart-summary {
  margin-bottom: 16px;
  color: var(--text-secondary);
  font-size: 14px;
}

.chart-summary strong {
  color: var(--accent-primary);
}

.chart-container {
  height: 220px;
}

.chart {
  width: 100%;
  height: 100%;
}

/* 信息区块 */
.info-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 28px;
}

@media (max-width: 768px) {
  .info-section {
    grid-template-columns: 1fr;
  }
}

.section-card {
  background: var(--bg-card);
  border-radius: var(--border-radius);
  padding: 20px;
  border: 1px solid var(--border-color);
}

.section-card h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h3 {
  margin-bottom: 0;
}

/* 协议分布 */
.protocol-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.protocol-item:last-child {
  margin-bottom: 0;
}

.protocol-name {
  width: 50px;
  font-weight: 600;
  font-size: 12px;
  color: var(--text-secondary);
}

.protocol-bar-container {
  flex: 1;
  height: 6px;
  background: var(--bg-secondary);
  border-radius: 3px;
  overflow: hidden;
}

.protocol-bar {
  height: 100%;
  background: var(--accent-gradient);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.protocol-count {
  width: 32px;
  text-align: right;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
}

.empty-hint {
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

/* 不健康频道列表 */
.unhealthy-list {
  max-height: 180px;
  overflow-y: auto;
}

.unhealthy-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 6px;
}

.unhealthy-item:last-child {
  margin-bottom: 0;
}

.channel-name {
  font-weight: 500;
  font-size: 13px;
}

.channel-group {
  color: var(--text-muted);
  font-size: 12px;
}

.empty-state {
  text-align: center;
  padding: 28px;
}

.empty-emoji {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}

.empty-state p {
  color: var(--text-muted);
  font-size: 13px;
}

/* 快捷操作 */
.quick-actions h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 16px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

@media (max-width: 768px) {
  .action-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.action-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  background: var(--bg-card);
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: var(--transition);
  text-decoration: none;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
}

.action-item:hover {
  background: var(--bg-hover);
  border-color: var(--accent-primary);
  transform: translateY(-1px);
}

.action-emoji {
  font-size: 18px;
}

.action-item.is-loading {
  opacity: 0.7;
  cursor: not-allowed;
  pointer-events: none;
}

.action-item.is-loading:hover {
  transform: none;
}

.rotating {
  display: inline-block;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 频道排名 */
.ranking-list {
  max-height: 240px;
  overflow-y: auto;
}

.ranking-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 6px;
}

.ranking-item:last-child {
  margin-bottom: 0;
}

.rank-badge {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  flex-shrink: 0;
}

.rank-badge.top-3 {
  background: var(--accent-gradient);
  color: white;
}

.ranking-item .channel-name {
  flex: 1;
  font-weight: 500;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.watch-duration {
  color: var(--accent-primary);
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
}
</style>
