import Vue from 'vue';
import Vuex from 'vuex';

import dandiset from '@/store/dandiset';

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    dandiset,
  },
});
