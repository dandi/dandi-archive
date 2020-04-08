import girderRest from '@/rest';

const DANDISETS_PER_PAGE = 8;

export default {
  namespaced: true,
  state: {
    sort: {
      field: 'created',
      direction: 1,
    },
    page: 1,

    // retrieved from server
    dandisets: [],
    pages: 0,
  },
  mutations: {
    setSearchSettings(state, { sort }) {
      state.sort = sort;
      state.page = 1;
    },
    setDandisets(state, { dandisets, total }) {
      state.dandisets = dandisets;
      state.pages = Math.ceil(total / DANDISETS_PER_PAGE);
    },
  },
  actions: {
    async reload({ commit, state }) {
      const { data: dandisets, headers } = await girderRest.get('dandi/user', {
        params: {
          limit: DANDISETS_PER_PAGE,
          offset: (state.page - 1) * DANDISETS_PER_PAGE,
          sort: state.sort.field,
          sortdir: state.sort.direction,
        },
      });
      const total = headers['girder-total-count'];
      commit('setDandisets', { dandisets, total });
    },
    async changeSearchSettings({ commit, dispatch }, { sort }) {
      commit('setSearchSettings', { sort });
      dispatch('reload');
    },
  },
};
