import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/Login.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/',
        component: () => import('@/layouts/MainLayout.vue'),
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                name: 'Dashboard',
                component: () => import('@/views/Dashboard.vue')
            },
            {
                path: 'channels',
                name: 'Channels',
                component: () => import('@/views/Channels.vue')
            },
            {
                path: 'groups',
                name: 'Groups',
                component: () => import('@/views/Groups.vue')
            },
            {
                path: 'settings',
                name: 'Settings',
                component: () => import('@/views/Settings.vue')
            },
            {
                path: 'subscription',
                name: 'Subscription',
                component: () => import('@/views/Subscription.vue')
            },
            {
                path: 'proxy-status',
                name: 'ProxyStatus',
                component: () => import('@/views/ProxyStatus.vue')
            }
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
    const authStore = useAuthStore()

    if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
        next('/login')
    } else if (to.path === '/login' && authStore.isAuthenticated) {
        next('/')
    } else {
        next()
    }
})

export default router
