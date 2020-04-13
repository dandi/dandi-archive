import Vue from 'vue';
import Vuex from 'vuex';

import girder from '@/store/girder';
import dandisetListing from '@/store/dandisetListing';
import stats from '@/store/stats';

Vue.use(Vuex);


export default new Vuex.Store({
  modules: {
    girder,
    publicDandisets: dandisetListing(),
    myDandisets: dandisetListing({ user: true }),
    stats,
  },
});
