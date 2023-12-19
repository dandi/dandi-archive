// Import external packages
import Vue from 'vue';
import VueGtag from 'vue-gtag';
import VueSocialSharing from 'vue-social-sharing';

// @ts-ignore missing definitions
import * as Sentry from '@sentry/vue';
import { CaptureConsole } from '@sentry/integrations';

// Import plugins first (order may matter)
import pinia from '@/plugins/pinia';
import vuetify from '@/plugins/vuetify';

// Import custom behavior
import '@/title';

// Import internal items
import App from '@/App.vue';
import router from '@/router';

Sentry.init({
  dsn: import.meta.env.VITE_APP_SENTRY_DSN,
  environment: import.meta.env.VITE_APP_SENTRY_ENVIRONMENT,
  integrations: [
    new Sentry.BrowserTracing({
      routingInstrumentation: Sentry.vueRouterInstrumentation(router),
    }),
    new CaptureConsole({
      levels: ['error'],
    }),
  ],
  tracePropagationTargets: [import.meta.env.VITE_APP_DANDI_API_ROOT || ''],
  tracesSampleRate: 0.01,
  trackComponents: true,
});

Vue.use(VueGtag, {
  config: { id: 'UA-146135810-2' },
}, router);

Vue.use(VueSocialSharing);

new Vue({
  router,
  render: (h) => h(App),
  pinia,
  vuetify,
}).$mount('#app');
