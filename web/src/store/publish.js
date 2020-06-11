import { publishRest } from '@/rest';

export default {
  namespaced: true,
  state: {
    publishDandiset: null,
  },
  mutations: {
    setPublishDandiset(state, dandiset) {
      state.publishDandiset = dandiset;
    },
  },
  actions: {
    async fetchPublishDandiset({ commit }, { identifier, version, girderId }) {
      const data = await publishRest.specificVersion(identifier, version, girderId);
      commit('setPublishDandiset', data);
    },
  },
};
