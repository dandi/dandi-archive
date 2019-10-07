import Vue from 'vue';
import Vuex from 'vuex';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    girderRest: null,
    browseLocation: null,
  },
  getters: {
    loggedIn: state => !!state.girderRest.user,
  },
  mutations: {
    setBrowseLocation(state, location) {
      state.browseLocation = location;
    },
    setGirderRest(state, gr) {
      state.girderRest = gr;
    },
  },
  actions: {
    selectSearchResult(r) {
      console.log(r);
    },
    async logout({ state }) {
      await state.girderRest.logout();
    },
  },
});
