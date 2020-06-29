import { girderRest, publishRest } from '@/rest';
import { draftVersion, dandisetHasVersion } from '@/utils';

export default {
  namespaced: true,
  state: {
    publishDandiset: null,
    girderDandiset: null,
    versions: null,
    loading: false, // No mutation, as we don't want this mutated by the user
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
    setVersions(state, versions) {
      state.versions = versions;
    },
    setOwners(state, owners) {
      state.owners = owners;
    },
  },
  actions: {
    async uninitializeDandisets({ state, commit }) {
      commit('setPublishDandiset', null);
      commit('setGirderDandiset', null);
      commit('setVersions', null);
      commit('setOwners', null);
      state.loading = false;
    },
    async initializeDandisets({ state, dispatch }, { identifier, version }) {
      await dispatch('uninitializeDandisets');

      dispatch('fetchGirderDandiset', { identifier });
      dispatch('fetchOwners', identifier);

      // Required below
      await dispatch('fetchDandisetVersions', { identifier });

      if (dandisetHasVersion(state.versions, version)) {
        // Version is a valid dandiset version, load that version
        dispatch('fetchPublishDandiset', { identifier, version });
      }
    },
    async fetchDandisetVersions({ state, commit }, { identifier }) {
      state.loading = true;

      try {
        const { results } = await publishRest.versions(identifier);
        commit('setVersions', results);
      } catch (err) {
        commit('setVersions', []);
      }

      state.loading = false;
    },
    async fetchPublishDandiset({ state, commit }, { identifier, version }) {
      state.loading = true;

      try {
        const data = await publishRest.specificVersion(identifier, version);
        commit('setPublishDandiset', data);
      } catch (err) {
        commit('setPublishDandiset', null);
      }

      state.loading = false;
    },
    async fetchGirderDandiset({ state, commit }, { identifier }) {
      state.loading = true;

      const { data } = await girderRest.get(`dandi/${identifier}`);
      commit('setGirderDandiset', data);

      state.loading = false;
    },
    async fetchOwners({ state, commit }, identifier) {
      state.loading = true;

      const { data } = await girderRest.get(`/dandi/${identifier}/owners`);
      commit('setOwners', data);

      state.loading = false;
    },
  },
};
