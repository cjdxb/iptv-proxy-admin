<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <div class="logo-emoji">📺</div>
        <h1>{{ siteStore.siteName }}</h1>
        <p>请登录以继续</p>
      </div>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            :prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '🚀 登录' }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 主题切换按钮 -->
    <div class="theme-toggle">
      <el-dropdown trigger="click" @command="handleThemeChange">
        <el-button circle>
          <span style="font-size: 16px;">{{ themeStore.theme === 'light' ? '☀️' : '🌙' }}</span>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="light" :class="{ active: themeStore.mode === 'light' }">
              ☀️ 浅色
            </el-dropdown-item>
            <el-dropdown-item command="dark" :class="{ active: themeStore.mode === 'dark' }">
              🌙 深色
            </el-dropdown-item>
            <el-dropdown-item command="system" :class="{ active: themeStore.mode === 'system' }">
              💻 跟随系统
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="decoration-blob blob-1"></div>
      <div class="decoration-blob blob-2"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useSiteStore } from '@/stores/site'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const siteStore = useSiteStore()

const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    
    try {
      await authStore.login(form.username, form.password)
      if (authStore.mustChangePassword) {
        ElMessage.warning('首次登录请先修改密码')
        router.push('/account')
      } else {
        ElMessage.success('登录成功 🎉')
        router.push('/')
      }
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '登录失败')
    } finally {
      loading.value = false
    }
  })
}

function handleThemeChange(mode) {
  themeStore.setMode(mode)
}

onMounted(() => {
  siteStore.fetchSettings()
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
  transition: background-color 0.3s ease;
}

.login-container {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  background: var(--bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
  position: relative;
  z-index: 10;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.theme-toggle {
  position: absolute;
  top: 24px;
  right: 24px;
  z-index: 20;
}

.theme-toggle .el-button {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
}

.theme-toggle .el-button:hover {
  border-color: var(--accent-primary);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-emoji {
  font-size: 56px;
  margin-bottom: 16px;
}

.login-header h1 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.login-header p {
  color: var(--text-muted);
  font-size: 14px;
}

.login-form .el-form-item {
  margin-bottom: 20px;
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 600;
  border-radius: var(--border-radius);
}

/* 背景装饰 */
.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.decoration-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.15;
}

.blob-1 {
  width: 500px;
  height: 500px;
  background: var(--accent-primary);
  top: -150px;
  right: -100px;
}

.blob-2 {
  width: 400px;
  height: 400px;
  background: var(--accent-secondary);
  bottom: -100px;
  left: -100px;
}

/* 下拉菜单选中样式 */
:deep(.el-dropdown-menu__item.active) {
  color: var(--accent-primary);
  font-weight: 500;
}
</style>
