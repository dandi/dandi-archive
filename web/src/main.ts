// Import external packages
import Vue from 'vue';
import VueGtag from 'vue-gtag';
import VueSocialSharing from 'vue-social-sharing';

// @ts-ignore missing definitions
import * as Sentry from '@sentry/browser';
import * as Integrations from '@sentry/integrations';

// Import plugins first (order may matter)
import pinia from '@/plugins/pinia';
import vuetify from '@/plugins/vuetify';

// Import custom behavior
import '@/title';

// Import internal items
import App from '@/App.vue';
import router from '@/router';

Sentry.init({
  dsn: process.env.VUE_APP_SENTRY_DSN,
  environment: process.env.VUE_APP_SENTRY_ENVIRONMENT,
  integrations: [new Integrations.Vue({ Vue, logErrors: true })],
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
