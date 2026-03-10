import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// 创建 axios 实例
const http = axios.create({
    baseURL: '/api',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 刷新令牌专用客户端（不走业务拦截器，避免递归）
const refreshClient = axios.create({
    baseURL: '/api',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json'
    }
})

let refreshPromise = null

function redirectToLoginIfNeeded() {
    if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
    }
}

function redirectToAccountIfNeeded() {
    if (router.currentRoute.value.path !== '/account') {
        router.push('/account')
    }
}

function shouldSkipRefresh(url = '') {
    return url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/logout')
}

function isBusinessUnauthorized(status, url = '', errorData = {}) {
    if (status !== 401) {
        return false
    }

    // 修改密码时“原密码错误”属于业务校验，不应触发登录态清理
    if (url.includes('/auth/change-password')) {
        return errorData.code === 'invalid_old_password' || errorData.error === '原密码错误'
    }

    return false
}

// 请求拦截器（自动添加 access token）
http.interceptors.request.use(
    config => {
        const authStore = useAuthStore()
        if (authStore.accessToken) {
            config.headers = config.headers || {}
            config.headers.Authorization = `Bearer ${authStore.accessToken}`
        }
        return config
    },
    error => Promise.reject(error)
)

// 响应拦截器
http.interceptors.response.use(
    response => response,
    async error => {
        const status = error.response?.status
        const errorData = error.response?.data || {}
        const originalRequest = error.config || {}
        const requestUrl = originalRequest.url || ''
        const authStore = useAuthStore()

        if (status === 403 && errorData.code === 'must_change_password') {
            authStore.setAuthData({
                user: {
                    ...(authStore.user || {}),
                    must_change_password: true
                }
            })
            redirectToAccountIfNeeded()
            return Promise.reject(error)
        }

        if (status !== 401) {
            return Promise.reject(error)
        }

        // 登录失败本身不触发刷新
        if (requestUrl.includes('/auth/login')) {
            return Promise.reject(error)
        }

        if (isBusinessUnauthorized(status, requestUrl, errorData)) {
            return Promise.reject(error)
        }

        // refresh 接口自身失败或重试后仍失败，直接清理登录态
        if (shouldSkipRefresh(requestUrl) || originalRequest._retry) {
            authStore.clearAuthState()
            redirectToLoginIfNeeded()
            return Promise.reject(error)
        }

        if (!authStore.refreshToken) {
            authStore.clearAuthState()
            redirectToLoginIfNeeded()
            return Promise.reject(error)
        }

        originalRequest._retry = true

        try {
            if (!refreshPromise) {
                refreshPromise = refreshClient
                    .post('/auth/refresh', { refresh_token: authStore.refreshToken })
                    .then(response => {
                        const data = response.data || {}
                        authStore.setAuthData({
                            user: data.user || authStore.user,
                            accessToken: data.access_token,
                            refreshToken: data.refresh_token
                        })
                        return data.access_token
                    })
                    .finally(() => {
                        refreshPromise = null
                    })
            }

            const newAccessToken = await refreshPromise
            originalRequest.headers = originalRequest.headers || {}
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
            return http(originalRequest)
        } catch (refreshError) {
            authStore.clearAuthState()
            redirectToLoginIfNeeded()
            return Promise.reject(refreshError)
        }
    }
)

// API 模块
const api = {
    // 认证
    auth: {
        login: (username, password) => http.post('/auth/login', { username, password }),
        logout: (refreshToken) => http.post('/auth/logout', { refresh_token: refreshToken }),
        refresh: (refreshToken) => http.post('/auth/refresh', { refresh_token: refreshToken }),
        me: () => http.get('/auth/me'),
        resetToken: () => http.post('/auth/reset-token'),
        changePassword: (oldPassword, newPassword) =>
            http.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
        changeUsername: (username) => http.post('/auth/change-username', { username })
    },

    // 仪表盘
    dashboard: {
        get: () => http.get('/dashboard'),
        getWatchStats: (days = 7) => http.get(`/dashboard/watch-stats?days=${days}`),
        getChannelRanking: (days = 7, limit = 10) => http.get(`/dashboard/channel-ranking?days=${days}&limit=${limit}`)
    },

    // 频道
    channels: {
        list: (params) => http.get('/channels', { params }),
        get: (id) => http.get(`/channels/${id}`),
        create: (data) => http.post('/channels', data),
        update: (id, data) => http.put(`/channels/${id}`, data),
        delete: (id) => http.delete(`/channels/${id}`),
        batchDelete: (ids) => http.post('/channels/batch-delete', { ids }),
        updateSort: (orders) => http.post('/channels/sort', { orders })
    },

    // 分组
    groups: {
        list: (includeChannels = false) => http.get('/groups', { params: { include_channels: includeChannels } }),
        get: (id, includeChannels = false) => http.get(`/groups/${id}`, { params: { include_channels: includeChannels } }),
        create: (data) => http.post('/groups', data),
        update: (id, data) => http.put(`/groups/${id}`, data),
        delete: (id) => http.delete(`/groups/${id}`),
        deleteEmpty: () => http.delete('/groups/empty'),
        updateSort: (orders) => http.post('/groups/sort', { orders })
    },

    // 设置
    settings: {
        getAll: () => http.get('/settings'),
        get: (key) => http.get(`/settings/${key}`),
        update: (settings) => http.post('/settings', settings),
        updateOne: (key, value) => http.put(`/settings/${key}`, { value }),
        reload: () => http.post('/settings/reload'),
        testUdpxy: (url) => http.post('/settings/test-udpxy', { url })
    },

    // 订阅
    subscription: {
        getUrls: () => http.get('/subscription/urls')
    },

    // 代理状态
    proxy: {
        getStatus: () => http.get('/proxy/status')
    },

    // 健康检测
    health: {
        checkOne: (channelId) => http.post(`/health/check/${channelId}`),
        checkAll: () => http.post('/health/check-all'),
        getStatus: () => http.get('/health/status')
    },

    // 导入导出
    importExport: {
        import: (formData) => http.post('/import-export/import', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        }),
        importContent: (content, format, overwrite = false, autoCreateGroup = true, includeRegex = '', excludeRegex = '') =>
            http.post('/import-export/import', {
                content, format, overwrite,
                auto_create_group: autoCreateGroup,
                include_regex: includeRegex,
                exclude_regex: excludeRegex
            }),
        importFromUrl: (url, overwrite = false, autoCreateGroup = true, format = 'auto', includeRegex = '', excludeRegex = '') =>
            http.post('/import-export/import-url', {
                url, overwrite,
                auto_create_group: autoCreateGroup,
                format,
                include_regex: includeRegex,
                exclude_regex: excludeRegex
            }),
        export: (format) => http.get(`/import-export/export?format=${format}`, { responseType: 'blob' })
    },

    // 观看历史
    history: {
        cleanup: () => http.post('/history/cleanup'),
        getStats: () => http.get('/history/stats'),
        getList: (page = 1, perPage = 20) => http.get('/history/list', { params: { page, per_page: perPage } })
    }
}

export default api
