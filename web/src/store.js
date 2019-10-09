import Vue from 'vue';
import Vuex from 'vuex';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    girderRest: null,
    browseLocation: null,
    selected: [],
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
    setSelected(state, selected) {
      state.selected = selected;
    },
  },
  actions: {
    async selectSearchResult({ state, commit }, result) {
      commit('setSelected', []);

      if (result._modelType === 'item') {
        const resp = await state.girderRest.get(`folder/${result.folderId}`);
        commit('setBrowseLocation', resp.data);
        commit('setSelected', [result]);
      } else {
        commit('setBrowseLocation', result);
      }
    },
    async logout({ state }) {
      await state.girderRest.logout();
    },
  },
});
