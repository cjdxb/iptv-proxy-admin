import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useSiteStore = defineStore('site', () => {
    const siteName = ref('IPTV Proxy Admin')

    async function fetchSettings() {
        try {
            const response = await api.settings.getAll()
            if (response.data.site_name) {
                siteName.value = response.data.site_name
            }
            document.title = siteName.value
        } catch (error) {
            console.error('获取站点设置失败', error)
        }
    }

    async function updateSiteName(name) {
        try {
            await api.settings.updateOne('site_name', name)
            siteName.value = name
            document.title = name
            return true
        } catch (error) {
            console.error('更新站点名称失败', error)
            throw error
        }
    }

    return {
        siteName,
        fetchSettings,
        updateSiteName
    }
})
