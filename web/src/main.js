import Vue from 'vue';
import { sync } from 'vuex-router-sync';
import Girder, { RestClient, vuetify } from '@girder/components/src';

import App from './App.vue';
import router from './router';
import store from './store';

Vue.use(Girder);

const apiRoot = process.env.VUE_APP_API_ROOT || 'http://localhost:8080/api/v1';
const girderRest = new RestClient({ apiRoot, setLocalCookie: true });
store.commit('setGirderRest', girderRest);
sync(store, router);

girderRest.fetchUser().then(() => {
  new Vue({
    provide: { girderRest },
    router,
    render: h => h(App),
    store,
    vuetify,
  }).$mount('#app');
});
