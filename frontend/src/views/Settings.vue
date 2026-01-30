<template>
  <div class="settings-page">
    <div class="page-header">
      <h1>⚙️ 系统设置</h1>
      <p>配置 IPTV 系统参数</p>
    </div>

    <div class="settings-container" v-loading="loading">
      <!-- 网站设置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>🌍 网站设置</span>
          </div>
        </template>
        <el-form label-width="140px" label-position="left">
          <el-form-item label="网站名称">
            <div class="form-item-content">
              <el-input
                v-model="settings.site_name"
                placeholder="自定义网站名称"
              />
              <div class="form-item-tip">在网站标题栏显示的名称</div>
            </div>
          </el-form-item>

          <el-form-item label="EPG URL">
            <div class="form-item-content">
              <el-input
                v-model="settings.epg_url"
                placeholder="EPG 节目单 XML 地址"
              />
              <div class="form-item-tip">EPG 节目单数据源地址</div>
            </div>
          </el-form-item>

          <el-form-item label=" ">
            <el-button type="primary" @click="saveBasicSettings" :loading="savingBasic">
              保存设置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 流媒体配置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>📺 流媒体配置</span>
          </div>
        </template>
        <el-form label-width="140px" label-position="left">
          <div class="sub-section-title">UDPxy 组播转换</div>

          <el-form-item label="启用 UDPxy">
            <div class="form-item-content">
              <el-switch v-model="settings.udpxy_enabled" />
              <div class="form-item-tip">启用后可将组播流（RTP/UDP）转换为 HTTP 流</div>
            </div>
          </el-form-item>

          <el-form-item label="UDPxy 服务地址">
            <div class="form-item-content">
              <div class="input-with-button">
                <el-input
                  v-model="settings.udpxy_url"
                  placeholder="http://localhost:3680"
                  :disabled="!settings.udpxy_enabled"
                />
                <el-button
                  @click="testUdpxyConnection"
                  :loading="testingUdpxy"
                  :disabled="!settings.udpxy_enabled || !settings.udpxy_url"
                >
                  检测连接
                </el-button>
              </div>
              <div class="form-item-tip">UDPxy 代理服务器地址，例如：http://192.168.1.1:4022</div>
            </div>
          </el-form-item>

          <div class="sub-section-title">代理缓冲配置</div>

          <el-form-item label="缓冲区大小">
            <div class="form-item-content">
              <div class="input-with-unit">
                <el-input-number
                  v-model="settings.proxy_buffer_size"
                  :min="1024"
                  :max="65536"
                  :step="1024"
                />
                <span class="unit-text">字节</span>
              </div>
              <div class="form-item-tip">推荐值：4096-16384，值越大吞吐量越高但延迟也越大</div>
            </div>
          </el-form-item>

          <el-form-item label=" ">
            <el-button type="primary" @click="saveStreamingConfig" :loading="savingStreaming">
              保存并应用
            </el-button>
          </el-form-item>

          <el-alert
            type="info"
            :closable="false"
            show-icon
          >
            <template #title>
              💡 修改后立即生效，无需重启服务
            </template>
          </el-alert>
        </el-form>
      </el-card>

      <!-- 健康检测配置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>💚 健康检测配置</span>
          </div>
        </template>
        <el-form label-width="140px" label-position="left">
          <el-form-item label="检测超时">
            <div class="form-item-content">
              <div class="input-with-unit">
                <el-input-number
                  v-model="settings.health_check_timeout"
                  :min="1"
                  :max="60"
                  :step="1"
                />
                <span class="unit-text">秒</span>
              </div>
              <div class="form-item-tip">单个频道健康检测超时时间，推荐值：5-30秒</div>
            </div>
          </el-form-item>

          <el-form-item label="失败重试次数">
            <div class="form-item-content">
              <div class="input-with-unit">
                <el-input-number
                  v-model="settings.health_check_max_retries"
                  :min="0"
                  :max="5"
                  :step="1"
                />
                <span class="unit-text">次</span>
              </div>
              <div class="form-item-tip">检测失败后重试次数，0表示不重试，推荐值：1-2次</div>
            </div>
          </el-form-item>

          <el-form-item label="检测线程数">
            <div class="form-item-content">
              <div class="input-with-unit">
                <el-input-number
                  v-model="settings.health_check_threads"
                  :min="1"
                  :max="5"
                  :step="1"
                />
                <span class="unit-text">线程</span>
              </div>
              <div class="form-item-tip">并发检测的线程数，值越大检测速度越快，推荐值：3-5线程</div>
            </div>
          </el-form-item>

          <el-form-item label=" ">
            <el-button type="primary" @click="saveHealthCheckConfig" :loading="savingHealthCheck">
              保存并应用
            </el-button>
          </el-form-item>

          <el-alert
            type="info"
            :closable="false"
            show-icon
          >
            <template #title>
              💡 修改后立即应用到新的健康检测任务
            </template>
          </el-alert>
        </el-form>
      </el-card>

      <!-- 账户设置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>👤 账户设置</span>
          </div>
        </template>
        <el-form label-width="140px" label-position="left">
          <div class="sub-section-title">用户名</div>

          <el-form-item label="当前用户">
            <div class="form-item-content">
              <el-input v-model="usernameForm.username" :placeholder="authStore.user?.username" />
              <div class="form-item-tip">当前用户名：{{ authStore.user?.username }}，用户名长度不能少于3位</div>
            </div>
          </el-form-item>

          <el-form-item label=" ">
            <el-button type="primary" @click="changeUsername" :loading="changingUsername">
              修改用户名
            </el-button>
          </el-form-item>

          <div class="sub-section-title">密码</div>

          <el-form-item label="原密码">
            <el-input v-model="passwordForm.oldPassword" type="password" show-password />
          </el-form-item>

          <el-form-item label="新密码">
            <el-input v-model="passwordForm.newPassword" type="password" show-password />
          </el-form-item>

          <el-form-item label="确认密码">
            <div class="form-item-content">
              <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
              <div class="form-item-tip">新密码长度不能少于6位</div>
            </div>
          </el-form-item>

          <el-form-item label=" ">
            <el-button type="primary" @click="changePassword" :loading="changingPassword">
              修改密码
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 数据管理 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>📊 数据管理</span>
          </div>
        </template>
        <el-form label-width="140px" label-position="left">
          <div class="sub-section-title">观看历史</div>

          <el-form-item label="数据保留时长">
            <div class="form-item-content">
              <el-radio-group v-model="settings.watch_history_retention_days">
                <el-radio :label="7">保留 7 天</el-radio>
                <el-radio :label="14">保留 14 天</el-radio>
                <el-radio :label="30">保留 30 天</el-radio>
              </el-radio-group>
              <div class="form-item-tip">
                此设置用于自动清理策略（如需启用自动清理，请在环境变量中配置）
              </div>
            </div>
          </el-form-item>

          <el-form-item label=" ">
            <el-button type="primary" @click="saveRetentionDays" :loading="savingRetention">
              保存设置
            </el-button>
          </el-form-item>

          <div class="sub-section-title">数据统计</div>

          <el-form-item label="历史记录统计">
            <div class="history-stats" v-if="historyStats">
              <div class="stat-item">
                <span class="stat-label">总记录数：</span>
                <span class="stat-value">{{ historyStats.total_count }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最早记录：</span>
                <span class="stat-value">{{ formatDate(historyStats.earliest_date) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最新记录：</span>
                <span class="stat-value">{{ formatDate(historyStats.latest_date) }}</span>
              </div>
            </div>
          </el-form-item>

          <el-form-item label="数据清理">
            <div class="form-item-content">
              <div class="button-group">
                <el-button type="danger" @click="confirmCleanupAll" :loading="cleaning">
                  清空全部数据
                </el-button>
                <el-button @click="fetchHistoryStats" :loading="loadingStats">
                  刷新统计
                </el-button>
              </div>
            </div>
          </el-form-item>

          <el-alert
            type="error"
            :closable="false"
            show-icon
          >
            <template #title>
              ⚠️ 清空操作将删除所有观看历史记录，此操作不可恢复！请谨慎操作！
            </template>
          </el-alert>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useSiteStore } from '@/stores/site'
import api from '@/api'
import { formatDate } from '@/utils/datetime'

const authStore = useAuthStore()
const siteStore = useSiteStore()

const loading = ref(false)
const savingBasic = ref(false)
const savingStreaming = ref(false)
const savingHealthCheck = ref(false)
const changingPassword = ref(false)
const changingUsername = ref(false)
const savingRetention = ref(false)
const cleaning = ref(false)
const loadingStats = ref(false)
const testingUdpxy = ref(false)

const settings = reactive({
  epg_url: '',
  site_name: '',
  watch_history_retention_days: 30,
  proxy_buffer_size: 8192,
  health_check_timeout: 10,
  health_check_max_retries: 1,
  health_check_threads: 3,
  udpxy_enabled: false,
  udpxy_url: 'http://localhost:3680'
})

const historyStats = ref(null)

const usernameForm = reactive({
  username: ''
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

async function fetchSettings() {
  loading.value = true
  try {
    const response = await api.settings.getAll()
    Object.assign(settings, response.data)
    if (!settings.site_name) {
      settings.site_name = siteStore.siteName
    }
    // 设置保留天数默认值
    if (settings.watch_history_retention_days) {
      settings.watch_history_retention_days = parseInt(settings.watch_history_retention_days)
    } else {
      settings.watch_history_retention_days = 30
    }
    // 设置代理缓冲区默认值
    if (settings.proxy_buffer_size) {
      settings.proxy_buffer_size = parseInt(settings.proxy_buffer_size)
    } else {
      settings.proxy_buffer_size = 8192
    }
    // 设置健康检测超时默认值
    if (settings.health_check_timeout) {
      settings.health_check_timeout = parseInt(settings.health_check_timeout)
    } else {
      settings.health_check_timeout = 10
    }
    // 设置健康检测重试次数默认值
    if (settings.health_check_max_retries !== undefined) {
      settings.health_check_max_retries = parseInt(settings.health_check_max_retries)
    } else {
      settings.health_check_max_retries = 1
    }
    // 设置健康检测线程数默认值
    if (settings.health_check_threads) {
      settings.health_check_threads = parseInt(settings.health_check_threads)
    } else {
      settings.health_check_threads = 3
    }
    // 设置 UDPxy 启用状态默认值
    if (settings.udpxy_enabled !== undefined) {
      settings.udpxy_enabled = settings.udpxy_enabled === 'true' || settings.udpxy_enabled === true
    } else {
      settings.udpxy_enabled = false
    }
    // 设置 UDPxy URL 默认值
    if (!settings.udpxy_url) {
      settings.udpxy_url = 'http://localhost:3680'
    }
    usernameForm.username = authStore.user?.username || ''
    // 同时获取历史统计
    await fetchHistoryStats()
  } catch (error) {
    ElMessage.error('获取设置失败')
  } finally {
    loading.value = false
  }
}

// 保存基础设置（网站名称 + EPG）
async function saveBasicSettings() {
  if (!settings.site_name) {
    ElMessage.warning('网站名称不能为空')
    return
  }

  savingBasic.value = true
  try {
    await siteStore.updateSiteName(settings.site_name)
    await api.settings.updateOne('epg_url', settings.epg_url)
    ElMessage.success('网站设置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingBasic.value = false
  }
}

// 保存流媒体配置（UDPxy + 代理）
async function saveStreamingConfig() {
  if (settings.udpxy_enabled && !settings.udpxy_url) {
    ElMessage.warning('请输入 UDPxy 服务地址')
    return
  }

  if (!settings.proxy_buffer_size || settings.proxy_buffer_size < 1024 || settings.proxy_buffer_size > 65536) {
    ElMessage.warning('缓冲区大小必须在 1024-65536 字节之间')
    return
  }

  savingStreaming.value = true
  try {
    await api.settings.updateOne('udpxy_enabled', settings.udpxy_enabled.toString())
    await api.settings.updateOne('udpxy_url', settings.udpxy_url)
    await api.settings.updateOne('proxy_buffer_size', settings.proxy_buffer_size)
    // 重载配置使其立即生效
    await api.settings.reload()
    ElMessage.success('流媒体配置已保存并应用')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingStreaming.value = false
  }
}

// 检测 UDPxy 连接
async function testUdpxyConnection() {
  if (!settings.udpxy_url) {
    ElMessage.warning('请输入 UDPxy 服务地址')
    return
  }

  testingUdpxy.value = true
  try {
    const response = await api.settings.testUdpxy(settings.udpxy_url)
    if (response.data.success) {
      ElMessage.success('UDPxy 服务器连接成功！')
    } else {
      ElMessage.error(response.data.message || '连接失败')
    }
  } catch (error) {
    const errorMsg = error.response?.data?.message || '连接测试失败'
    ElMessage.error(errorMsg)
  } finally {
    testingUdpxy.value = false
  }
}

// 保存健康检测配置
async function saveHealthCheckConfig() {
  if (!settings.health_check_timeout || settings.health_check_timeout < 1 || settings.health_check_timeout > 60) {
    ElMessage.warning('检测超时必须在 1-60 秒之间')
    return
  }

  if (settings.health_check_max_retries < 0 || settings.health_check_max_retries > 5) {
    ElMessage.warning('重试次数必须在 0-5 次之间')
    return
  }

  if (!settings.health_check_threads || settings.health_check_threads < 1 || settings.health_check_threads > 5) {
    ElMessage.warning('检测线程数必须在 1-5 之间')
    return
  }

  savingHealthCheck.value = true
  try {
    await api.settings.updateOne('health_check_timeout', settings.health_check_timeout)
    await api.settings.updateOne('health_check_max_retries', settings.health_check_max_retries)
    await api.settings.updateOne('health_check_threads', settings.health_check_threads)
    // 重载配置使其立即生效
    await api.settings.reload()
    ElMessage.success('健康检测配置已保存并应用')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingHealthCheck.value = false
  }
}

async function changeUsername() {
  const newUsername = usernameForm.username
  if (!newUsername) {
    ElMessage.warning('用户名不能为空')
    return
  }

  if (newUsername.length < 3) {
    ElMessage.warning('用户名长度不能少于3位')
    return
  }

  if (newUsername === authStore.user?.username) {
    ElMessage.info('用户名未变更')
    return
  }

  changingUsername.value = true
  try {
    const response = await api.auth.changeUsername(newUsername)
    ElMessage.success('用户名修改成功')
    authStore.user.username = response.data.username
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '修改失败')
  } finally {
    changingUsername.value = false
  }
}

async function changePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword) {
    ElMessage.warning('请填写原密码和新密码')
    return
  }

  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  if (passwordForm.newPassword.length < 6) {
    ElMessage.warning('新密码长度不能少于6位')
    return
  }

  changingPassword.value = true
  try {
    await api.auth.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    ElMessage.success('密码修改成功')
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '密码修改失败')
  } finally {
    changingPassword.value = false
  }
}

// 保存观看历史保留天数
async function saveRetentionDays() {
  savingRetention.value = true
  try {
    await api.settings.updateOne('watch_history_retention_days', settings.watch_history_retention_days)
    ElMessage.success('保存成功')
    await fetchHistoryStats()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingRetention.value = false
  }
}

// 获取观看历史统计
async function fetchHistoryStats() {
  loadingStats.value = true
  try {
    const response = await api.history.getStats()
    historyStats.value = response.data
  } catch (error) {
    console.error('获取历史统计失败', error)
  } finally {
    loadingStats.value = false
  }
}

// 确认清空全部数据
async function confirmCleanupAll() {
  if (!historyStats.value || historyStats.value.total_count === 0) {
    ElMessage.info('没有观看历史数据')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要清空全部 ${historyStats.value.total_count} 条观看历史记录吗？此操作不可恢复！`,
      '⚠️ 危险操作确认',
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'error',
        confirmButtonClass: 'el-button--danger'
      }
    )
    await cleanupAllHistory()
  } catch {
    // 用户取消
  }
}

// 清空全部观看历史
async function cleanupAllHistory() {
  cleaning.value = true
  try {
    const response = await api.history.cleanup()
    ElMessage.success(response.data.message)
    await fetchHistoryStats()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '清空失败')
  } finally {
    cleaning.value = false
  }
}

// 注意：formatDate 函数已从 @/utils/datetime 导入

onMounted(fetchSettings)
</script>

<style scoped>
.settings-page {
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

.settings-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

/* 子分组标题 */
.sub-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 24px 0 16px 0;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary);
}

.sub-section-title:first-child {
  margin-top: 0;
}

/* 表单项内容容器 */
.form-item-content {
  width: 100%;
}

/* 表单项提示文字 */
.form-item-tip {
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 6px;
  line-height: 1.5;
}

/* 输入框和单位组合 */
.input-with-unit {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unit-text {
  color: var(--text-secondary);
  font-size: 14px;
  white-space: nowrap;
}

/* 输入框和按钮组合 */
.input-with-button {
  display: flex;
  align-items: center;
  gap: 12px;
}

.input-with-button .el-input {
  flex: 1;
}

/* 按钮组 */
.button-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 历史统计 */
.history-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  color: var(--text-muted);
  font-size: 14px;
}

.stat-value {
  font-weight: 600;
  font-size: 14px;
}

/* Element Plus 表单样式调整 */
:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-alert) {
  margin-top: 16px;
}
</style>
