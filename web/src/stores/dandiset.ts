import { defineStore } from 'pinia';

import axios from 'axios';
import RefParser from '@apidevtools/json-schema-ref-parser';

// eslint-disable-next-line import/no-cycle
import { dandiRest } from '@/rest';
import { User, Version } from '@/types';
import { draftVersion } from '@/utils/constants';

interface State {
  dandiset: Version | null;
  versions: Version[] | null,
  loading: boolean,
  owners: User[] | null,
  schema: any,
}

export const useDandisetStore = defineStore('dandiset', {
  state: (): State => ({
    dandiset: null,
    versions: null,
    loading: false,
    owners: null,
    schema: null,
  }),
  getters: {
    version: (state) => (state.dandiset ? state.dandiset.version : draftVersion),
    schemaVersion: (state) => state.schema?.properties.schemaVersion.default,
    userCanModifyDandiset: (state) => {
      const user = dandiRest?.user as User | null;

      // published versions are never editable, and logged out users can never edit a dandiset
      if (state.dandiset?.metadata?.version !== draftVersion || !user) {
        return false;
      }
      // if they're an admin, they can edit any dandiset
      if (user.admin) {
        return true;
      }
      // otherwise check if they are an owner
      return !!(state.owners?.find((owner) => owner.username === user.username));
    },
  },
  actions: {
    async uninitializeDandisets() {
      this.dandiset = null;
      this.versions = null;
      this.owners = null;
      this.loading = false;
    },
    async initializeDandisets({ identifier, version }: Record<string, string>) {
      this.uninitializeDandisets();

      // this can be done concurrently, don't await
      this.fetchDandisetVersions({ identifier });
      await this.fetchDandiset({ identifier, version });
      await this.fetchOwners(identifier);
    },
    async fetchDandisetVersions({ identifier }: Record<string, string>) {
      this.loading = true;
      const res = await dandiRest.versions(identifier);
      if (res) {
        const { results } = res;
        this.versions = results || [];
      }

      this.loading = false;
    },
    async fetchDandiset({ identifier, version }: Record<string, string>) {
      this.loading = true;
      const sanitizedVersion = version || (await dandiRest.mostRecentVersion(identifier))?.version;

      if (!sanitizedVersion) {
        this.dandiset = null;
        this.loading = false;
        return;
      }

      try {
        const data = await dandiRest.specificVersion(identifier, sanitizedVersion);
        this.dandiset = data;
      } catch (err) {
        this.dandiset = null;
      }

      this.loading = false;
    },
    async fetchSchema() {
      const { schema_url: schemaUrl } = await dandiRest.info();
      const res = await axios.get(schemaUrl);

      if (res.status !== 200) {
        throw new Error('Could not retrieve Dandiset Schema!');
      }

      const schema = await RefParser.dereference(res.data);

      this.schema = schema;
    },
    async fetchOwners(identifier: string) {
      this.loading = true;

      const { data } = await dandiRest.owners(identifier);
      this.owners = data;

      this.loading = false;
    },
  },
});
