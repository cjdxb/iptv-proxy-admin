<template>
  <div class="account-page">
    <div class="page-header">
      <h1>👤 账户设置</h1>
      <p>管理当前登录账户的信息</p>
    </div>

    <el-card class="account-card">
      <el-form label-width="140px" label-position="left">
        <el-alert
          v-if="authStore.mustChangePassword"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        >
          首次登录请先修改密码，修改完成后才能访问其它功能。
        </el-alert>

        <div class="sub-section-title">用户名</div>

        <el-form-item label="当前用户">
          <div class="form-item-content">
            <el-input
              v-model="usernameForm.username"
              :placeholder="authStore.user?.username"
              :disabled="authStore.mustChangePassword"
            />
            <div class="form-item-tip">当前用户名：{{ authStore.user?.username }}，用户名长度不能少于3位</div>
          </div>
        </el-form-item>

        <el-form-item label=" ">
          <el-button
            type="primary"
            @click="changeUsername"
            :loading="changingUsername"
            :disabled="authStore.mustChangePassword"
          >
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const router = useRouter()
const authStore = useAuthStore()

const changingPassword = ref(false)
const changingUsername = ref(false)

const usernameForm = reactive({
  username: ''
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

async function changeUsername() {
  if (authStore.mustChangePassword) {
    ElMessage.warning('请先修改密码')
    return
  }

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
    authStore.updateCurrentUsername(response.data.username)
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '修改失败')
  } finally {
    changingUsername.value = false
  }
}

async function changePassword() {
  const wasForceChangePassword = authStore.mustChangePassword

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
    const response = await api.auth.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    const data = response.data || {}
    if (data.access_token && data.refresh_token) {
      authStore.setAuthData({
        user: data.user || authStore.user,
        accessToken: data.access_token,
        refreshToken: data.refresh_token
      })
    }
    ElMessage.success('密码修改成功')
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''

    if (wasForceChangePassword && !authStore.mustChangePassword) {
      router.push('/')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '密码修改失败')
  } finally {
    changingPassword.value = false
  }
}

onMounted(() => {
  usernameForm.username = authStore.user?.username || ''
})
</script>

<style scoped>
.account-page {
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

.account-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
}

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

.form-item-content {
  width: 100%;
}

.form-item-tip {
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 6px;
  line-height: 1.5;
}

:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}
</style>
