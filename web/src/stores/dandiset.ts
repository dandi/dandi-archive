import { defineStore } from 'pinia';

import axios from 'axios';
import RefParser from '@apidevtools/json-schema-ref-parser';

import { dandiRest, user } from '@/rest';
import type { User, Version } from '@/types';
import { draftVersion } from '@/utils/constants';
import { fixSchema } from '@/utils/schema';


function isUnauthenticatedOrForbidden(err: unknown) {
  return axios.isAxiosError(err) && err.response && [401, 403].includes(err.response.status);
}

interface State {
  meta: {
    dandisetExistsAndEmbargoed: boolean,
  };
  dandiset: Version | null;
  versions: Version[] | null,
  owners: User[] | null,
  schema: any,
}

export const useDandisetStore = defineStore('dandiset', {
  state: (): State => ({
    meta: { dandisetExistsAndEmbargoed: false },
    dandiset: null,
    versions: null,
    owners: null,
    schema: null,
  }),
  getters: {
    version: (state) => (state.dandiset ? state.dandiset.version : draftVersion),
    draftVersion: (state) => state.versions?.find((v) => v.version === draftVersion),
    publishedVersions: (state) => state.versions?.filter((v) => v.version !== draftVersion),
    schemaVersion: (state) => state.schema?.properties.schemaVersion.default,
    userCanModifyDandiset: (state) => {
      // published versions are never editable, and logged out users can never edit a dandiset
      if (state.dandiset?.metadata?.version !== draftVersion || !user) {
        return false;
      }
      // if they're an admin, they can edit any dandiset
      if (user.value?.admin) {
        return true;
      }
      // otherwise check if they are an owner
      return !!(state.owners?.find((owner) => owner.username === user.value?.username));
    },
  },
  actions: {
    async uninitializeDandisets() {
      this.meta.dandisetExistsAndEmbargoed = false;
      this.dandiset = null;
      this.versions = null;
      this.owners = null;
    },
    async initializeDandisets({ identifier, version }: Record<string, string>) {
      this.uninitializeDandisets();

      // this can be done concurrently, don't await
      this.fetchDandisetVersions({ identifier });
      await this.fetchDandiset({ identifier, version });

      if (this.dandiset) {
        await this.fetchOwners(identifier);
      }
    },
    async fetchDandisetVersions({ identifier }: Record<string, string>) {
      let res;
      try {
        res = await dandiRest.versions(identifier);
      } catch (err) {
        // 401/403 errors are normal, and indicate that this dandiset is embargoed
        // and the user doesn't have permission to view it.
        if (isUnauthenticatedOrForbidden(err)) {
          res = null;
          this.meta.dandisetExistsAndEmbargoed = true;
        } else {
          throw err;
        }
      }
      if (res) {
        const { results } = res;
        this.versions = results || [];
      }
    },
    async fetchDandiset({ identifier, version }: Record<string, string>) {
      try {
        const sanitizedVersion = version || (await dandiRest.mostRecentVersion(identifier))?.version;
        if (!sanitizedVersion) {
          this.dandiset = null;
          return;
        }

        const data = await dandiRest.specificVersion(identifier, sanitizedVersion);
        this.dandiset = data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response && err.response.status < 500) {
          this.dandiset = null;

          if (isUnauthenticatedOrForbidden(err)) {
            this.meta.dandisetExistsAndEmbargoed = true;
          }

        } else {
          throw err;
        }
      }
    },
    async fetchSchema() {
      const { schema_url: schemaUrl } = await dandiRest.info();
      const res = await axios.get(schemaUrl);

      if (res.status !== 200) {
        throw new Error('Could not retrieve Dandiset Schema!');
      }

      const schema = await RefParser.dereference(res.data);

      this.schema = fixSchema(schema);
    },
    async fetchOwners(identifier: string) {
      const { data } = await dandiRest.owners(identifier);
      this.owners = data;
    },
  },
});
