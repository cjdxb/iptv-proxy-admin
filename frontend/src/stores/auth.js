import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
    const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
    const accessToken = ref(localStorage.getItem('access_token') || '')
    const refreshToken = ref(localStorage.getItem('refresh_token') || '')
    const initialized = ref(false)

    const isAuthenticated = computed(() => !!accessToken.value)
    const mustChangePassword = computed(() => !!user.value?.must_change_password)

    function persistAuthState() {
        if (user.value) {
            localStorage.setItem('user', JSON.stringify(user.value))
        } else {
            localStorage.removeItem('user')
        }

        if (accessToken.value) {
            localStorage.setItem('access_token', accessToken.value)
        } else {
            localStorage.removeItem('access_token')
        }

        if (refreshToken.value) {
            localStorage.setItem('refresh_token', refreshToken.value)
        } else {
            localStorage.removeItem('refresh_token')
        }
    }

    function setAuthData({ user: userData, accessToken: newAccessToken, refreshToken: newRefreshToken }) {
        if (userData !== undefined) {
            user.value = userData
        }
        if (newAccessToken !== undefined) {
            accessToken.value = newAccessToken || ''
        }
        if (newRefreshToken !== undefined) {
            refreshToken.value = newRefreshToken || ''
        }
        persistAuthState()
    }

    function clearAuthState() {
        user.value = null
        accessToken.value = ''
        refreshToken.value = ''
        persistAuthState()
    }

    async function login(username, password) {
        const response = await api.auth.login(username, password)
        const data = response.data || {}
        setAuthData({
            user: data.user || null,
            accessToken: data.access_token || '',
            refreshToken: data.refresh_token || ''
        })

        return response.data
    }

    async function logout() {
        const currentRefreshToken = refreshToken.value
        try {
            await api.auth.logout(currentRefreshToken)
        } catch (error) {
            // 忽略登出请求失败
        }
        clearAuthState()
    }

    async function fetchUser() {
        try {
            const response = await api.auth.me()
            user.value = response.data
            persistAuthState()
        } catch (error) {
            clearAuthState()
            throw error
        }
    }

    async function refreshSession() {
        if (!refreshToken.value) {
            throw new Error('缺少刷新令牌')
        }

        const response = await api.auth.refresh(refreshToken.value)
        const data = response.data || {}

        setAuthData({
            user: data.user || user.value,
            accessToken: data.access_token || '',
            refreshToken: data.refresh_token || ''
        })

        return data
    }

    async function initializeAuth() {
        if (initialized.value) {
            return
        }

        if (!accessToken.value && refreshToken.value) {
            try {
                await refreshSession()
            } catch (error) {
                clearAuthState()
                initialized.value = true
                return
            }
        }

        if (accessToken.value) {
            try {
                await fetchUser()
            } catch (error) {
                // fetchUser 失败时会清理登录态
            }
        } else if (!refreshToken.value) {
            clearAuthState()
        }

        initialized.value = true
    }

    function updateCurrentUsername(username) {
        if (!user.value) {
            return
        }
        user.value.username = username
        persistAuthState()
    }

    async function resetToken() {
        const response = await api.auth.resetToken()
        if (user.value) {
            user.value.token = response.data.token
            persistAuthState()
        }
        return response.data
    }

    return {
        user,
        accessToken,
        refreshToken,
        initialized,
        isAuthenticated,
        mustChangePassword,
        setAuthData,
        clearAuthState,
        updateCurrentUsername,
        login,
        logout,
        fetchUser,
        refreshSession,
        initializeAuth,
        resetToken
    }
})
