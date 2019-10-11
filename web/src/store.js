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
        // Because setting the location is going to trigger the DataBrowser to
        // set its selected value to [], which due to two-way binding also propagates back
        // up to this component, we must defer this to the next tick so that this runs after that,
        // as we have no way to update the DataBrowser location without having it also reset the
        // selection internally.
        Vue.nextTick(() => { commit('setSelected', [result]); });
      } else {
        commit('setBrowseLocation', result);
      }
    },
    async logout({ state }) {
      await state.girderRest.logout();
    },
  },
});
