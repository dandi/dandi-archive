import Vue from 'vue';
import Vuex from 'vuex';

import girder from '@/store/girder';

Vue.use(Vuex);


export default new Vuex.Store({
  modules: {
    girder,
  },
});
