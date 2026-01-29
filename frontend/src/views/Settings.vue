<template>
  <div class="settings-page">
    <div class="page-header">
      <h1>⚙️ 系统设置</h1>
      <p>配置 IPTV 系统参数</p>
    </div>
    
    <div class="settings-container" v-loading="loading">
      <!-- EPG 设置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>📅 EPG 设置</span>
          </div>
        </template>
        <el-form label-width="120px">
          <el-form-item label="EPG URL">
            <el-input
              v-model="settings.epg_url"
              placeholder="EPG XML 地址"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSetting('epg_url')" :loading="saving">
              保存
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- 网站设置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>🌍 网站设置</span>
          </div>
        </template>
        <el-form label-width="120px">
          <el-form-item label="网站名称">
            <el-input
              v-model="settings.site_name"
              placeholder="自定义网站名称"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSiteName" :loading="savingSiteName">
              保存
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 账户设置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>👤 账户设置</span>
          </div>
        </template>
        <el-form label-width="120px">
          <el-form-item label="当前用户">
            <div class="user-row">
              <el-input v-model="usernameForm.username" :placeholder="authStore.user?.username" />
              <el-button @click="changeUsername" :loading="changingUsername">修改用户名</el-button>
            </div>
          </el-form-item>
          <el-divider />
          <el-form-item label="原密码">
            <el-input v-model="passwordForm.oldPassword" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="passwordForm.newPassword" type="password" show-password />
          </el-form-item>
          <el-form-item label="确认密码">
            <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="changePassword" :loading="changingPassword">
              修改密码
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 观看历史设置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <span>📊 观看历史管理</span>
          </div>
        </template>
        <el-form label-width="120px">
          <el-form-item label="数据保留时长">
            <el-radio-group v-model="settings.watch_history_retention_days">
              <el-radio :label="7">保留 7 天</el-radio>
              <el-radio :label="14">保留 14 天</el-radio>
              <el-radio :label="30">保留 30 天</el-radio>
            </el-radio-group>
            <div style="color: var(--text-muted); font-size: 12px; margin-top: 8px;">
              此设置用于自动清理策略（如需启用自动清理，请在环境变量中配置）
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveRetentionDays" :loading="savingRetention">
              保存设置
            </el-button>
          </el-form-item>
          <el-divider />
          <el-form-item label="数据统计">
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
            <el-button type="danger" @click="confirmCleanupAll" :loading="cleaning">
              清空全部数据
            </el-button>
            <el-button @click="fetchHistoryStats" :loading="loadingStats">
              刷新统计
            </el-button>
          </el-form-item>
          <el-alert
            type="error"
            :closable="false"
            show-icon
            style="margin-top: 12px"
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

const authStore = useAuthStore()
const siteStore = useSiteStore()

const loading = ref(false)
const saving = ref(false)
const savingSiteName = ref(false)
const changingPassword = ref(false)
const changingUsername = ref(false)
const savingRetention = ref(false)
const cleaning = ref(false)
const loadingStats = ref(false)

const settings = reactive({
  epg_url: '',
  site_name: '',
  watch_history_retention_days: 30
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
    usernameForm.username = authStore.user?.username || ''
    // 同时获取历史统计
    await fetchHistoryStats()
  } catch (error) {
    ElMessage.error('获取设置失败')
  } finally {
    loading.value = false
  }
}

async function saveSetting(key) {
  saving.value = true
  try {
    await api.settings.updateOne(key, settings[key])
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function saveSiteName() {
  if (!settings.site_name) {
    ElMessage.warning('网站名称不能为空')
    return
  }
  
  savingSiteName.value = true
  try {
    await siteStore.updateSiteName(settings.site_name)
    ElMessage.success('网站名称已更新')
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    savingSiteName.value = false
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

// 格式化日期时间（精确到秒）
function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

onMounted(fetchSettings)
</script>

<style scoped>
.settings-page {
  max-width: 800px;
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

.user-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.user-row .el-input {
  flex: 1;
}

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
</style>
