<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ 'is-collapsed': isCollapsed }">
      <div class="logo">
        <span class="logo-emoji">📺</span>
        <span class="logo-text" v-show="!isCollapsed">{{ siteStore.siteName }}</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/" :title="isCollapsed ? '仪表盘' : ''">
          <span class="menu-emoji">📊</span>
          <span class="menu-text">仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/channels" :title="isCollapsed ? '频道管理' : ''">
          <span class="menu-emoji">📺</span>
          <span class="menu-text">频道管理</span>
        </el-menu-item>
        <el-menu-item index="/groups" :title="isCollapsed ? '分组管理' : ''">
          <span class="menu-emoji">📁</span>
          <span class="menu-text">分组管理</span>
        </el-menu-item>
        <el-menu-item index="/subscription" :title="isCollapsed ? '订阅链接' : ''">
          <span class="menu-emoji">🔗</span>
          <span class="menu-text">订阅链接</span>
        </el-menu-item>
        <el-menu-item index="/proxy-status" :title="isCollapsed ? '代理状态' : ''">
          <span class="menu-emoji">📡</span>
          <span class="menu-text">代理状态</span>
        </el-menu-item>
        <el-menu-item index="/settings" :title="isCollapsed ? '系统设置' : ''">
          <span class="menu-emoji">⚙️</span>
          <span class="menu-text">系统设置</span>
        </el-menu-item>
      </el-menu>

      <!-- 折叠按钮 -->
      <div class="collapse-btn-wrapper">
        <div class="collapse-btn" @click="toggleCollapse" :title="isCollapsed ? '展开侧边栏' : '折叠侧边栏'">
          <span class="collapse-icon">{{ isCollapsed ? '»' : '«' }}</span>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="content-wrapper">
      <!-- 顶部栏 -->
      <header class="top-bar">
        <div class="top-bar-right">
          <!-- 主题切换 -->
          <el-dropdown trigger="click" @command="handleThemeChange">
            <div class="header-btn" :title="themeLabel">
              <span class="btn-icon">{{ themeStore.theme === 'light' ? '☀️' : '🌙' }}</span>
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

          <!-- 用户信息 -->
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="header-btn user-btn" :title="authStore.user?.username">
              <div class="user-avatar">
                {{ authStore.user?.username?.[0]?.toUpperCase() || 'U' }}
              </div>
              <span class="username" v-show="authStore.user?.username">
                {{ authStore.user?.username }}
              </span>
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
      </header>

      <!-- 主内容 -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>

      <!-- 底部版权信息 -->
      <footer class="app-footer">
        <div class="footer-content">
          <div class="footer-left">
            <span class="copyright">© 2026 IPTV Proxy Admin</span>
            <span class="separator">•</span>
            <span class="version">v{{ appVersion }}</span>
          </div>
          <div class="footer-right">
            <a
              href="https://github.com/cjdxb/iptv-proxy-admin"
              target="_blank"
              rel="noopener noreferrer"
              class="footer-link"
              title="GitHub"
            >
              <span class="link-icon">🔗</span>
              <span>GitHub</span>
            </a>
            <span class="separator">•</span>
            <a
              href="https://github.com/cjdxb/iptv-proxy-admin/blob/main/LICENSE"
              target="_blank"
              rel="noopener noreferrer"
              class="footer-link license"
              title="AGPL v3 License"
            >
              <span class="link-icon">📜</span>
              <span>AGPL v3</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useSiteStore } from '@/stores/site'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const siteStore = useSiteStore()

// 应用版本号
const appVersion = __APP_VERSION__

// 侧边栏折叠状态
const isCollapsed = ref(false)

// 从 localStorage 读取折叠状态
const loadCollapsedState = () => {
  const saved = localStorage.getItem('sidebar-collapsed')
  if (saved !== null) {
    isCollapsed.value = saved === 'true'
  }
  // 窄屏自动折叠
  if (window.innerWidth < 768) {
    isCollapsed.value = true
  }
}

// 切换折叠状态
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebar-collapsed', isCollapsed.value.toString())
}

// 响应窗口大小变化
const handleResize = () => {
  if (window.innerWidth < 768) {
    isCollapsed.value = true
  }
}

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
  loadCollapsedState()
  window.addEventListener('resize', handleResize)
})

// 清理监听器
import { onUnmounted } from 'vue'
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* 侧边栏样式 */
.sidebar {
  width: 220px;
  height: 100vh;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
  transition: width 0.3s ease, background-color 0.3s ease, border-color 0.3s ease;
  flex-shrink: 0;
}

.sidebar.is-collapsed {
  width: 64px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-bottom: 1px solid var(--border-color);
  transition: padding 0.3s ease;
}

.sidebar.is-collapsed .logo {
  justify-content: center;
  padding: 20px 0;
}

.logo-emoji {
  font-size: 24px;
}

.logo-text {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
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
  display: flex;
  align-items: center;
}

.menu-emoji {
  font-size: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  margin-right: 10px;
}

.menu-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
}

/* 折叠状态下的菜单项样式 */
.sidebar.is-collapsed .sidebar-menu .el-menu-item {
  padding: 0 !important;
  justify-content: center;
}

.sidebar.is-collapsed .menu-emoji {
  margin-right: 0;
  font-size: 20px;
}

.sidebar.is-collapsed .menu-text {
  display: none;
}

/* 折叠按钮容器 */
.collapse-btn-wrapper {
  padding: 16px;
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.collapse-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  background: transparent;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.collapse-btn:hover {
  background: rgba(100, 116, 139, 0.08);
  transform: translateX(2px);
}

.collapse-btn:active {
  transform: translateX(0);
}

.collapse-icon {
  font-size: 16px;
  font-weight: bold;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.collapse-btn:hover .collapse-icon {
  color: #3b82f6;
}

/* 内容包装器 */
.content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-primary);
}

/* 顶部栏 */
.top-bar {
  height: 60px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 24px;
  flex-shrink: 0;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 顶部栏按钮样式 */
.header-btn {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border-radius: 8px;
  cursor: pointer;
  background: rgba(100, 116, 139, 0.06);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.header-btn:hover {
  background: rgba(100, 116, 139, 0.12);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.header-btn:active {
  transform: translateY(0);
}

.btn-icon {
  font-size: 18px;
  transition: all 0.2s ease;
}

.header-btn:hover .btn-icon {
  filter: brightness(1.1);
}

/* 用户按钮样式 */
.user-btn {
  padding: 4px 12px 4px 4px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 14px;
  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.25);
  transition: all 0.25s ease;
  flex-shrink: 0;
}

.header-btn:hover .user-avatar {
  box-shadow: 0 3px 10px rgba(102, 126, 234, 0.35);
  transform: scale(1.05);
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
}

/* 主内容区 */
.main-content {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  background: var(--bg-primary);
  transition: background-color 0.3s ease;
}

/* 下拉菜单选中样式 */
:deep(.el-dropdown-menu__item.active) {
  color: var(--accent-primary);
  font-weight: 500;
}

/* 响应式：窄屏适配 */
@media (max-width: 768px) {
  .sidebar {
    width: 64px;
  }

  .logo-text {
    display: none !important;
  }

  .logo {
    justify-content: center;
    padding: 20px 0;
  }

  .top-bar {
    padding: 0 16px;
  }

  .username {
    display: none;
  }

  .user-btn {
    padding: 4px;
  }

  .main-content {
    padding: 16px;
  }

  .app-footer {
    padding: 12px 16px;
  }

  .footer-content {
    flex-direction: column;
    gap: 8px;
    align-items: center;
  }

  .footer-left,
  .footer-right {
    justify-content: center;
  }
}

/* 底部版权信息 */
.app-footer {
  padding: 16px 32px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
  width: 100%;
}

.footer-left,
.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.copyright {
  font-weight: 500;
}

.version {
  color: var(--text-muted);
  font-size: 11px;
  padding: 2px 6px;
  background: rgba(100, 116, 139, 0.1);
  border-radius: 4px;
}

.separator {
  color: var(--border-color);
  margin: 0 2px;
}

.footer-link {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  text-decoration: none;
  transition: all 0.2s ease;
  padding: 2px 6px;
  border-radius: 4px;
}

.footer-link:hover {
  color: var(--accent-primary);
  background: rgba(100, 116, 139, 0.08);
  transform: translateY(-1px);
}

.footer-link.license:hover {
  color: var(--success);
}

.link-icon {
  font-size: 13px;
}
</style>
