import { girderRest, publishRest } from '@/rest';
import { draftVersion } from '@/utils';

export default {
  namespaced: true,
  state: {
    publishDandiset: null,
    girderDandiset: null,
    loading: false,
    owners: null,
  },
  getters: {
    version(state) {
      return state.publishDandiset ? state.publishDandiset.version : draftVersion;
    },
  },
  mutations: {
    setGirderDandiset(state, dandiset) {
      state.girderDandiset = dandiset;
    },
    setPublishDandiset(state, dandiset) {
      state.publishDandiset = dandiset;
    },
    setOwners(state, owners) {
      state.owners = owners;
    },
  },
  actions: {
    async fetchPublishDandiset({ state, commit }, { identifier, version, girderId }) {
      state.loading = true;

      const data = await publishRest.specificVersion(identifier, version, girderId);
      commit('setPublishDandiset', data);

      state.loading = false;
    },
    async fetchGirderDandiset({ state, commit }, { identifier }) {
      state.loading = true;

      const { data } = await girderRest.get(`dandi/${identifier}`);
      commit('setGirderDandiset', data);

      state.loading = false;
    },
    async fetchOwners({ commit }, identifier) {
      const { data } = await girderRest.get(`/dandi/${identifier}/owners`);
      commit('setOwners', data);
    },
  },
};
