import girderRest, { loggedIn } from '@/rest';

export default {
  namespaced: true,
  state: {
    browseLocation: null,
    selected: [],
    currentDandiset: null,
    currentDandisetOwners: null,
  },
  getters: {
    loggedIn,
  },
  mutations: {
    setSelected(state, selected) {
      state.selected = selected;
    },
    setCurrentDandiset(state, dandiset) {
      state.currentDandiset = dandiset;
    },
    setCurrentDandisetOwners(state, owners) {
      state.currentDandisetOwners = owners;
    },
    setBrowseLocation(state, location) {
      state.browseLocation = location;
    },
  },
  actions: {
    async fetchFullLocation({ commit }, location) {
      if (location && location._id && location._modelType) {
        const { _id: id, _modelType: modelType } = location;

        const { status, data } = await girderRest.get(`${modelType}/${id}`);
        if (status === 200) {
          commit('setBrowseLocation', data);
        }
      }
    },
    async fetchDandisetOwners({ commit }, identifier) {
      const { data } = await girderRest.get(`/dandi/${identifier}/owners`);
      commit('setCurrentDandisetOwners', data);
    },
    async logout() {
      await girderRest.logout();
    },
  },
};
