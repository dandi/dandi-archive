// Import external packages
import Vue from 'vue';
import { provide } from '@vue/composition-api';
import { sync } from 'vuex-router-sync';
import VueGtag from 'vue-gtag';

// @ts-ignore missing definitions
import { vuetify } from '@girder/components/src';
import * as Sentry from '@sentry/browser';
import * as Integrations from '@sentry/integrations';

// Import plugins first (order may matter)
import '@/plugins/composition';
import '@/plugins/girder';

// Import custom behavior
import toggles from '@/featureToggle';
import '@/title';

// Import internal items
import App from '@/App.vue';
import router from '@/router';
import store from '@/store';
import { girderRest, publishRest } from '@/rest';

Sentry.init({
  dsn: process.env.VUE_APP_SENTRY_DSN,
  integrations: [new Integrations.Vue({ Vue, logErrors: true })],
});

sync(store, router);

Vue.use(VueGtag, {
  config: { id: "UA-146135810-2" }
}, router);

function loadUser() {
  if (toggles.DJANGO_API) {
    return publishRest.restoreLogin();
  }
  return girderRest.fetchUser();
}

loadUser().then(() => {
  new Vue({
    setup() {
      provide('store', store);
      provide('girderRest', girderRest);
    },
    router,
    render: (h) => h(App),
    store,
    // @ts-ignore: missing definitions because Vue.use(Vuetify) is in a .js file
    vuetify,
  }).$mount('#app');
});
