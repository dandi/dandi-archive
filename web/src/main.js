import Vue from 'vue';
import Girder, { RestClient } from '@girder/components/src';

import App from './App.vue';
import router from './router';

Vue.use(Girder);

const apiRoot = process.env.VUE_APP_API_ROOT || 'http://localhost:8080/api/v1';
const girderRest = new RestClient({ apiRoot });

new Vue({
  provide: { girderRest },
  router,
  render: h => h(App),
}).$mount('#app');
