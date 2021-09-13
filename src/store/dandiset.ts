import { defineModule, localActionContext, localGetterContext } from 'direct-vuex';

import axios from 'axios';
import RefParser from '@apidevtools/json-schema-ref-parser';

import { publishRest, user } from '@/rest';
import { User, Version } from '@/types';
import { draftVersion } from '@/utils/constants';

interface DandisetState {
  publishDandiset: Version|null;
  versions: Version[]|null,
  loading: boolean,
  owners: User[]|null,
  schema: any,
}

const dandisetModule = defineModule({
  state: {
    publishDandiset: null,
    versions: null,
    loading: false, // No mutation, as we don't want this mutated by the user
    owners: null,
    schema: null,
  } as DandisetState,
  getters: {
    version(state: DandisetState): string {
      if (state.publishDandiset) {
        return state.publishDandiset.version;
      }
      return draftVersion;
    },
    userCanModifyDandiset(state: DandisetState): boolean {
      // published versions are never editable, and logged out users can never edit a dandiset
      if (state.publishDandiset?.metadata?.version !== draftVersion || !user()) {
        return false;
      }
      // if they're an admin, they can edit any dandiset
      if (user()?.admin) {
        return true;
      }
      // otherwise check if they are an owner
      const userExists = state.owners?.find((owner) => owner.username === user()?.username);
      return !!userExists;
    },
  },
  mutations: {
    setPublishDandiset(state: DandisetState, dandiset: Version) {
      state.publishDandiset = dandiset;
    },
    setVersions(state: DandisetState, versions: Version[]) {
      state.versions = versions;
    },
    setOwners(state: DandisetState, owners: User[]) {
      state.owners = owners;
    },
    setSchema(state: DandisetState, schema: any) {
      state.schema = schema;
    },
  },
  actions: {
    async uninitializeDandisets({ state, commit }) {
      commit('setPublishDandiset', null);
      commit('setVersions', null);
      commit('setOwners', null);
      state.loading = false;
    },
    async initializeDandisets({ dispatch }, { identifier, version }) {
      await dispatch('uninitializeDandisets');

      // this can be done concurrently, don't await
      dispatch('fetchDandisetVersions', { identifier });
      await dispatch('fetchPublishDandiset', { identifier, version });
      await dispatch('fetchOwners', identifier);
    },
    async fetchDandisetVersions({ state, commit }, { identifier }) {
      state.loading = true;

      const res = await publishRest.versions(identifier);
      if (res) {
        const { results } = res;
        commit('setVersions', results || []);
      }

      state.loading = false;
    },
    async fetchPublishDandiset({ state, commit }, { identifier, version }) {
      state.loading = true;

      const sanitizedVersion = version
      || (await publishRest.mostRecentVersion(identifier))?.version;

      try {
        const data = await publishRest.specificVersion(identifier, sanitizedVersion);
        commit('setPublishDandiset', data);
      } catch (err) {
        commit('setPublishDandiset', null);
      }

      state.loading = false;
    },
    async fetchSchema({ commit }) {
      const { schema_url: schemaUrl } = await publishRest.info();
      const res = await axios.get(schemaUrl);

      if (res.status !== 200) {
        throw new Error('Could not retrieve Dandiset Schema!');
      }

      const schema = await RefParser.dereference(res.data);

      commit('setSchema', schema);
    },
    async fetchOwners({ state, commit }, identifier) {
      state.loading = true;

      const { data } = await publishRest.owners(identifier);
      commit('setOwners', data);

      state.loading = false;
    },
  },
});

export default dandisetModule;

export const dandisetGetterContext = (
  args: [any, any, any, any],
) => localGetterContext(args, dandisetModule);
export const dandisetActionContext = (context: any) => localActionContext(context, dandisetModule);
