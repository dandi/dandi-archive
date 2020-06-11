import { girderRest, publishRest } from '@/rest';

export default {
  namespaced: true,
  state: {
    publishDandiset: null,
    girderDandiset: null,
    loading: false,
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
    async fetchPublishDandiset({ state, commit }, { identifier, version, girderId }) {
      state.loading = true;

      const data = await publishRest.specificVersion(identifier, version, girderId);
      commit('setPublishDandiset', data);

      state.loading = false;
    },
    async fetchGirderDandiset({ state, commit }, { girderId }) {
      state.loading = true;

      const { data } = await girderRest.get(`folder/${girderId}`);
      commit('setGirderDandiset', data);

      state.loading = false;
    },
  },
};
