/* eslint-disable no-use-before-define */

import { defineModule, localActionContext, localGetterContext } from 'direct-vuex';

import axios from 'axios';
import RefParser from '@apidevtools/json-schema-ref-parser';

import { dandiRest, user } from '@/rest';
import { User, Version } from '@/types';
import { draftVersion } from '@/utils/constants';

interface DandisetState {
  dandiset: Version|null;
  versions: Version[]|null,
  loading: boolean,
  owners: User[]|null,
  schema: any,
}

const dandisetGetterContext = (
  args: [any, any, any, any],
) => localGetterContext(args, dandisetModule);
const dandisetActionContext = (context: any) => localActionContext(context, dandisetModule);

const dandisetModule = defineModule({
  namespaced: true,
  state: {
    dandiset: null,
    versions: null,
    loading: false, // No mutation, as we don't want this mutated by the user
    owners: null,
    schema: null,
  } as DandisetState,
  getters: {
    version(...args): string {
      const { state } = dandisetGetterContext(args);
      if (state.dandiset) {
        return state.dandiset.version;
      }
      return draftVersion;
    },
    schemaVersion(...args): string {
      const { state } = dandisetGetterContext(args);
      return state.schema?.properties.schemaVersion.default;
    },
    userCanModifyDandiset(...args): boolean {
      const { state } = dandisetGetterContext(args);

      // published versions are never editable, and logged out users can never edit a dandiset
      if (state.dandiset?.metadata?.version !== draftVersion || !user()) {
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
    setDandiset(state: DandisetState, dandiset: Version|null) {
      state.dandiset = dandiset;
    },
    setVersions(state: DandisetState, versions: Version[]|null) {
      state.versions = versions;
    },
    setOwners(state: DandisetState, owners: User[]|null) {
      state.owners = owners;
    },
    setSchema(state: DandisetState, schema: any) {
      state.schema = schema;
    },
    setLoading(state: DandisetState, loading: boolean) {
      state.loading = loading;
    },
  },
  actions: {
    async uninitializeDandisets(context: any) {
      const { commit } = dandisetActionContext(context);

      commit.setDandiset(null);
      commit.setVersions(null);
      commit.setOwners(null);
      commit.setLoading(false);
    },
    async initializeDandisets(context: any, { identifier, version }) {
      const { dispatch } = dandisetActionContext(context);
      await dispatch.uninitializeDandisets();

      // this can be done concurrently, don't await
      dispatch.fetchDandisetVersions({ identifier });
      await dispatch.fetchDandiset({ identifier, version });
      await dispatch.fetchOwners(identifier);
    },
    async fetchDandisetVersions(context: any, { identifier }) {
      const { commit } = dandisetActionContext(context);
      commit.setLoading(true);

      const res = await dandiRest.versions(identifier);
      if (res) {
        const { results } = res;
        commit.setVersions(results || []);
      }

      commit.setLoading(false);
    },
    async fetchDandiset(context: any, { identifier, version }) {
      const { commit } = dandisetActionContext(context);
      commit.setLoading(true);

      const sanitizedVersion = version
      || (await dandiRest.mostRecentVersion(identifier))?.version;

      try {
        const data = await dandiRest.specificVersion(identifier, sanitizedVersion);
        commit.setDandiset(data);
      } catch (err) {
        commit.setDandiset(null);
      }

      commit.setLoading(false);
    },
    async fetchSchema(context: any) {
      const { commit } = dandisetActionContext(context);

      const { schema_url: schemaUrl } = await dandiRest.info();
      const res = await axios.get(schemaUrl);

      if (res.status !== 200) {
        throw new Error('Could not retrieve Dandiset Schema!');
      }

      const schema = await RefParser.dereference(res.data);

      commit.setSchema(schema);
    },
    async fetchOwners(context: any, identifier) {
      const { commit } = dandisetActionContext(context);

      commit.setLoading(true);

      const { data } = await dandiRest.owners(identifier);
      commit.setOwners(data);

      commit.setLoading(false);
    },
  },
});

export default dandisetModule;
