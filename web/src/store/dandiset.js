import { girderRest, publishRest } from '@/rest';

export default {
  namespaced: true,
  state: {
    publishDandiset: null,
    girderDandiset: null,
  },
  mutations: {
    setGirderDandiset(state, dandiset) {
      state.girderDandiset = dandiset;
    },
    setPublishDandiset(state, dandiset) {
      state.publishDandiset = dandiset;
    },
  },
  actions: {
    async fetchPublishDandiset({ commit }, { identifier, version, girderId }) {
      const data = await publishRest.specificVersion(identifier, version, girderId);
      commit('setPublishDandiset', data);
    },
    async fetchGirderDandiset({ commit }, { girderId }) {
      const { data } = await girderRest.get(`folder/${girderId}`);
      commit('setGirderDandiset', data);
    },
  },
};
