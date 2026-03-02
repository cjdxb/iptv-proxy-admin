import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { setupElementPlus } from './plugins/element-plus'
import './styles/index.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
setupElementPlus(app)

app.mount('#app')
