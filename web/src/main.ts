/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Plugins
import { registerPlugins } from '@/plugins'

// Directives
import { registerDirectives } from '@/directives'

// Components
import App from './App.vue'

// Composables
import { createApp } from 'vue'

import { useInstanceStore } from '@/stores/instance'

const app = createApp(App)

registerPlugins(app)
registerDirectives(app)

// Fetch instance config early so page titles and identifiers are available
useInstanceStore().fetchInstanceInfo();

app.mount('#app')
