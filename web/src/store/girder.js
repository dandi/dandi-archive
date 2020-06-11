import { girderRest, loggedIn } from '@/rest';

export default {
  namespaced: true,
  state: {
    browseLocation: null,
    girderDandiset: null,
    selected: [],
  },
  getters: {
    loggedIn,
  },
  mutations: {
    setSelected(state, selected) {
      state.selected = selected;
    },
    setGirderDandiset(state, dandiset) {
      state.girderDandiset = dandiset;
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
    async fetchGirderDandiset({ commit }, { girderId }) {
      const { data } = await girderRest.get(`folder/${girderId}`);
      commit('setGirderDandiset', data);
    },
    async logout() {
      await girderRest.logout();
    },
  },
};
