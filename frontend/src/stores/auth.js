import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
    const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

    const isAuthenticated = computed(() => !!user.value)

    async function login(username, password) {
        const response = await api.auth.login(username, password)
        user.value = response.data.user

        localStorage.setItem('user', JSON.stringify(user.value))

        return response.data
    }

    async function logout() {
        try {
            await api.auth.logout()
        } catch (error) {
            // 忽略登出请求失败
        }
        user.value = null
        localStorage.removeItem('user')
    }

    async function fetchUser() {
        try {
            const response = await api.auth.me()
            user.value = response.data
            localStorage.setItem('user', JSON.stringify(user.value))
        } catch (error) {
            logout()
            throw error
        }
    }

    async function resetToken() {
        const response = await api.auth.resetToken()
        if (user.value) {
            user.value.token = response.data.token
            localStorage.setItem('user', JSON.stringify(user.value))
        }
        return response.data
    }

    return {
        user,
        isAuthenticated,
        login,
        logout,
        fetchUser,
        resetToken
    }
})
