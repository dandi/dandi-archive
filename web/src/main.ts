import Vue from 'vue';
import VueCompositionAPI from '@vue/composition-api';
import { sync } from 'vuex-router-sync';

// @ts-ignore missing definitions
import Girder, { vuetify } from '@girder/components/src';
import * as Sentry from '@sentry/browser';
import * as Integrations from '@sentry/integrations';

import App from '@/App.vue';
import '@/featureToggle';
import router from '@/router';
import store from '@/store';
import { girderRest } from '@/rest';
import '@/title';

Vue.use(Girder);
Vue.use(VueCompositionAPI);

Sentry.init({
  dsn: process.env.VUE_APP_SENTRY_DSN,
  integrations: [new Integrations.Vue({ Vue, logErrors: true })],
});

sync(store, router);

girderRest.fetchUser().then(() => {
  new Vue({
    provide: { girderRest },
    router,
    render: (h) => h(App),
    store,
    // @ts-ignore: missing definitions because Vue.use(Vuetify) is in a .js file
    vuetify,
  }).$mount('#app');
});
