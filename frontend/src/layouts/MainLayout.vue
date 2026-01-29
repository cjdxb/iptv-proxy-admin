<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <span class="logo-emoji">📺</span>
        <span class="logo-text">{{ siteStore.siteName }}</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/">
          <span class="menu-emoji">📊</span>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/channels">
          <span class="menu-emoji">📺</span>
          <span>频道管理</span>
        </el-menu-item>
        <el-menu-item index="/groups">
          <span class="menu-emoji">📁</span>
          <span>分组管理</span>
        </el-menu-item>
        <el-menu-item index="/subscription">
          <span class="menu-emoji">🔗</span>
          <span>订阅链接</span>
        </el-menu-item>
        <el-menu-item index="/proxy-status">
          <span class="menu-emoji">📡</span>
          <span>代理状态</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <span class="menu-emoji">⚙️</span>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <!-- 主题切换 -->
        <div class="theme-switcher">
          <el-dropdown trigger="click" @command="handleThemeChange">
            <div class="theme-btn">
              <span class="theme-emoji">{{ themeStore.theme === 'light' ? '☀️' : '🌙' }}</span>
              <span>{{ themeLabel }}</span>
            </div>
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
        
        <!-- 用户信息 -->
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <div class="user-avatar">
              {{ authStore.user?.username?.[0]?.toUpperCase() || 'U' }}
            </div>
            <span class="username">{{ authStore.user?.username }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">
                👋 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useSiteStore } from '@/stores/site'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const siteStore = useSiteStore()

const activeMenu = computed(() => route.path)

const themeLabel = computed(() => {
  switch (themeStore.mode) {
    case 'light': return '浅色'
    case 'dark': return '深色'
    case 'system': return '自动'
    default: return '主题'
  }
})

async function handleCommand(command) {
  if (command === 'logout') {
    await authStore.logout()
    router.push('/login')
  } else if (command === 'settings') {
    router.push('/settings')
  }
}

function handleThemeChange(mode) {
  themeStore.setMode(mode)
}

onMounted(() => {
  siteStore.fetchSettings()
})
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 220px;
  height: 100vh;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
  transition: background-color 0.3s ease, border-color 0.3s ease;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-bottom: 1px solid var(--border-color);
}

.logo-emoji {
  font-size: 24px;
}

.logo-text {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
}

.sidebar-menu {
  flex: 1;
  padding: 12px 10px;
  overflow-y: auto;
}

.sidebar-menu .el-menu-item {
  height: 44px;
  line-height: 44px;
  margin-bottom: 2px;
  padding: 0 14px !important;
  font-size: 14px;
}

.menu-emoji {
  font-size: 16px;
  margin-right: 10px;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.theme-switcher {
  width: 100%;
}

.theme-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
  transition: var(--transition);
  width: 100%;
  font-size: 14px;
}

.theme-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.theme-emoji {
  font-size: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 10px 12px;
  border-radius: var(--border-radius-sm);
  transition: var(--transition);
}

.user-info:hover {
  background: var(--bg-hover);
}

.user-avatar {
  width: 32px;
  height: 32px;
  background: var(--accent-gradient);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.username {
  color: var(--text-primary);
  font-weight: 500;
  font-size: 14px;
}

.main-content {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  height: 100vh;
  background: var(--bg-primary);
  transition: background-color 0.3s ease;
}

/* 下拉菜单选中样式 */
:deep(.el-dropdown-menu__item.active) {
  color: var(--accent-primary);
  font-weight: 500;
}
</style>
