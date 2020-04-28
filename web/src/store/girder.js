import Vue from 'vue';

import girderRest, { loggedIn } from '@/rest';

export default {
  namespaced: true,
  state: {
    browseLocation: null,
    selected: [],
  },
  getters: {
    loggedIn,
  },
  mutations: {
    setSelected(state, selected) {
      state.selected = selected;
    },
    setBrowseLocation(state, location) {
      state.browseLocation = location;
    },
  },
  actions: {
    async selectSearchResult({ commit }, result) {
      commit('setSelected', []);

      if (result._modelType === 'item') {
        const resp = await girderRest.get(`folder/${result.folderId}`);
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
    async fetchFullLocation({ commit }, location) {
      if (location && location._id && location._modelType) {
        const { _id: id, _modelType: modelType } = location;

        const { status, data } = await girderRest.get(`${modelType}/${id}`);
        if (status === 200) {
          commit('setBrowseLocation', data);
        }
      }
    },
    async logout() {
      await girderRest.logout();
    },
  },
};
