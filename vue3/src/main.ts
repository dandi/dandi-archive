import { createApp } from 'vue'

import App from './App.vue'

// plugins
import router from '@/router'
import pinia from '@/plugins/pinia'
import vuetify from '@/plugins/vuetify'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(vuetify)

app.mount('#app')
