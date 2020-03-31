import Vue from 'vue';

import girderRest from '@/rest';

export default {
  namespaced: true,
  state: {
    apiKey: null,
    browseLocation: null,
    selected: [],
  },
  mutations: {
    setApiKey(state, apiKey) {
      state.apiKey = apiKey;
    },
    setSelected(state, selected) {
      state.selected = selected;
    },
  },
  actions: {
    async reloadApiKey({ commit }) {
      const { user } = girderRest;
      const { status, data } = await girderRest.get(
        'api_key', {
          params: {
            userId: user._id,
            limit: 50,
            sort: 'name',
            sortdir: 1,
          },
        },
      );

      const [dandiKey] = data.filter((key) => key.name === 'dandicli');
      if (status === 200 && dandiKey) {
        // send the key id to "PUT" endpoint for updating
        const { data: { key } } = await girderRest.put(`api_key/${dandiKey._id}`);
        commit('setApiKey', key);
      }
    },
    async fetchApiKey({ commit }) {
      const { user } = girderRest;
      const { status, data } = await girderRest.get(
        'api_key', {
          params: {
            userId: user._id,
            limit: 50,
            sort: 'name',
            sortdir: 1,
          },
        },
      );

      const [dandiKey] = data.filter((key) => key.name === 'dandicli');
      if (status === 200 && dandiKey) {
        // if there is an existing api key

        // set the user key
        commit('setApiKey', dandiKey.key);
      } else {
        // create a key using "POST" endpoint
        const { status: createStatus, data: { key } } = await girderRest.post('api_key', null, {
          params: {
            name: 'dandicli',
            scope: null,
            tokenDuration: 30,
            active: true,
          },
        });

        if (createStatus === 200) {
          commit('setApiKey', key);
        }
      }
    },
    async selectSearchResult({ commit }, result) {
      commit('setSelected', []);

      if (result._modelType === 'item') {
        const resp = await girderRest.get(`folder/${result.folderId}`);
        commit('setBrowseLocation', resp.data);
        // Because setting the location is going to trigger the DataBrowser to
        // set its selected value to [], which due to two-way binding also propagates back
        // up to this component, we must defer this to the next tick so that this runs after that,
        // as we have no way to update the DataBrowser location without having it also reset the
        // selection internally.
        Vue.nextTick(() => { commit('setSelected', [result]); });
      } else {
        commit('setBrowseLocation', result);
      }
    },
    async logout() {
      await girderRest.logout();
    },
  },
};
