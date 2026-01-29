import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// 创建 axios 实例
const http = axios.create({
    baseURL: '/api',
    timeout: 30000,
    withCredentials: true,  // 启用 cookie 发送
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器（不再需要手动添加 token）
http.interceptors.request.use(
    config => config,
    error => Promise.reject(error)
)

// 响应拦截器
http.interceptors.response.use(
    response => response,
    error => {
        // 401 表示未认证
        if (error.response?.status === 401) {
            const authStore = useAuthStore()
            authStore.logout()
            router.push('/login')
        }
        return Promise.reject(error)
    }
)

// API 模块
const api = {
    // 认证
    auth: {
        login: (username, password) => http.post('/auth/login', { username, password }),
        logout: () => http.post('/auth/logout'),
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
        updateOne: (key, value) => http.put(`/settings/${key}`, { value })
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
