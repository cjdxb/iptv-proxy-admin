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
      // The full HLS distribution is ~595 kB and is loaded only for previews.
      chunkSizeWarningLimit: 650,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return
            }

            // Keep the preview engines out of the shared application vendor chunk.
            if (id.includes('/hls.js/')) {
              return 'hls'
            }

            if (id.includes('/mpegts.js/')) {
              return 'mpegts'
            }

            if (id.includes('/@element-plus/icons-vue/')) {
              return 'el-icons'
            }

            if (id.includes('/element-plus/')) {
              return 'element-plus'
            }

            if (id.includes('/vue-echarts/')) {
              return 'vue-echarts'
            }

            if (id.includes('/zrender/')) {
              return 'zrender'
            }

            if (id.includes('/echarts/')) {
              return 'echarts'
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
