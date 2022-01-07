// Import external packages
import Vue from 'vue';
import { provide } from '@vue/composition-api';
import { sync } from 'vuex-router-sync';
import VueGtag from 'vue-gtag';
import VueSocialSharing from 'vue-social-sharing';

// @ts-ignore missing definitions
import * as Sentry from '@sentry/browser';
import * as Integrations from '@sentry/integrations';

// Import plugins first (order may matter)
import '@/plugins/composition';
import '@/plugins/asyncComputed';
import vuetify from '@/plugins/vuetify';

// Import custom behavior
import '@/title';

// Import internal items
import App from '@/App.vue';
import router from '@/router';
import store from '@/store';
import { dandiRest } from '@/rest';

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

async function loadUser() {
  return dandiRest.restoreLogin();
}

async function loadSchema() {
  await store.dispatch.dandiset.fetchSchema();
}

Promise.all([loadUser(), loadSchema()]).then(() => {
  new Vue({
    setup() {
      provide('store', store);
    },
    router,
    render: (h) => h(App),
    store: store.original,
    // @ts-ignore: missing definitions because Vue.use(Vuetify) is in a .js file
    vuetify,
  }).$mount('#app');
});
