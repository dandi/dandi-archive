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
    setPage(state, { page }) {
      state.page = page;
    },
    setSort(state, { sort }) {
      state.sort = sort;
      state.page = 1;
    },
    setDandisets(state, { dandisets, total }) {
      state.dandisets = dandisets;
      state.pages = Math.ceil(total / DANDISETS_PER_PAGE);
    },
  },
  actions: {
    async reload({ commit, state }, { user } = { user: false }) {
      const listingUrl = user ? 'dandi/user' : 'dandi';
      const { data: dandisets, headers } = await girderRest.get(listingUrl, {
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
    async changeSort({ commit, dispatch }, { sort }) {
      commit('setSort', { sort });
      dispatch('reload');
    },
    async changePage({ commit, dispatch }, { page }) {
      commit('setPage', { page });
      dispatch('reload');
    },
  },
};
