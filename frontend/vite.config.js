import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'fs'

// 读取 package.json 获取版本号
const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  return {
    plugins: [vue()],
    define: {
      __APP_VERSION__: JSON.stringify(pkg.version)
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return
            }

            if (
              id.includes('/echarts/') ||
              id.includes('/zrender/') ||
              id.includes('/vue-echarts/')
            ) {
              return 'echarts'
            }

            if (
              id.includes('/element-plus/') ||
              id.includes('/@element-plus/icons-vue/')
            ) {
              return 'element-plus'
            }

            if (
              id.includes('/vue/') ||
              id.includes('/vue-router/') ||
              id.includes('/pinia/')
            ) {
              return 'vue-vendor'
            }

            return 'vendor'
          }
        }
      }
    },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET,
          changeOrigin: true
        }
      }
    },
    resolve: {
      alias: {
        '@': '/src'
      }
    }
  }
})
