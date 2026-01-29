import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
    // 主题模式: 'light', 'dark', 'system'
    const mode = ref(localStorage.getItem('theme-mode') || 'system')

    // 当前实际主题
    const theme = ref('dark')

    // 系统主题媒体查询
    const systemDarkQuery = window.matchMedia('(prefers-color-scheme: dark)')

    // 获取系统主题
    function getSystemTheme() {
        return systemDarkQuery.matches ? 'dark' : 'light'
    }

    // 应用主题
    function applyTheme(newTheme) {
        theme.value = newTheme
        document.documentElement.setAttribute('data-theme', newTheme)

        // 更新 Element Plus 的主题
        if (newTheme === 'dark') {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
    }

    // 更新主题
    function updateTheme() {
        if (mode.value === 'system') {
            applyTheme(getSystemTheme())
        } else {
            applyTheme(mode.value)
        }
    }

    // 设置主题模式
    function setMode(newMode) {
        mode.value = newMode
        localStorage.setItem('theme-mode', newMode)
        updateTheme()
    }

    // 切换主题（在 light 和 dark 之间切换）
    function toggleTheme() {
        if (mode.value === 'system') {
            setMode(getSystemTheme() === 'dark' ? 'light' : 'dark')
        } else {
            setMode(mode.value === 'dark' ? 'light' : 'dark')
        }
    }

    // 监听系统主题变化
    systemDarkQuery.addEventListener('change', () => {
        if (mode.value === 'system') {
            updateTheme()
        }
    })

    // 初始化
    updateTheme()

    return {
        mode,
        theme,
        setMode,
        toggleTheme,
        updateTheme
    }
})
