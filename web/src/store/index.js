import Vue from 'vue';
import Vuex from 'vuex';

import girder from '@/store/girder';
import stats from '@/store/stats';
import publish from '@/store/publish';

Vue.use(Vuex);


export default new Vuex.Store({
  modules: {
    girder,
    stats,
    publish,
  },
});
