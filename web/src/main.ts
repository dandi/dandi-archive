// Import external packages
import Vue, { provide } from 'vue';
import { sync } from 'vuex-router-sync';
import VueGtag from 'vue-gtag';
import VueSocialSharing from 'vue-social-sharing';

// @ts-ignore missing definitions
import * as Sentry from '@sentry/browser';
import * as Integrations from '@sentry/integrations';

// Import plugins first (order may matter)
import vuetify from '@/plugins/vuetify';

// Import custom behavior
import '@/title';

// Import internal items
import App from '@/App.vue';
import router from '@/router';
import store from '@/store';

Sentry.init({
  dsn: process.env.VUE_APP_SENTRY_DSN,
  environment: process.env.VUE_APP_SENTRY_ENVIRONMENT,
  integrations: [new Integrations.Vue({ Vue, logErrors: true })],
});

sync(store.original, router);

Vue.use(VueGtag, {
  config: { id: 'UA-146135810-2' },
}, router);

Vue.use(VueSocialSharing);

new Vue({
  setup() {
    provide('store', store);
  },
  router,
  render: (h) => h(App),
  store: store.original,
  vuetify,
}).$mount('#app');
