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
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
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

const settings = reactive({
  epg_url: '',
  site_name: ''
})

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
    usernameForm.username = authStore.user?.username || ''
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
</style>
