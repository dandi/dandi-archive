import { publishRest } from '@/rest';

export default {
  namespaced: true,
  state: {
    versions: null,
  },
  mutations: {
    setVersions(state, versions) {
      state.versions = versions;
    },
  },
  actions: {
    async fetchPublishedVersions({ commit }, identifier) {
      if (identifier) {
        const response = await publishRest.get(`dandisets/${identifier}/versions/`)
          .catch((error) => {
            if (error.response.status === 404) {
              return { data: [] };
            }
            throw error;
          });
        const versions = response.data;
        commit('setVersions', versions);
      }
    },
  },
};
