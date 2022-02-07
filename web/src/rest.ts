import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import Vue from 'vue';
import OAuthClient from '@girder/oauth-client';
import {
  Asset, Dandiset, Paginated, User, Version, Info, AssetFile, AssetFolder,
} from '@/types';
import { Dandiset as DandisetMetadata, DandisetContributors, Organization } from '@/types/schema';

if (!process.env.VUE_APP_DANDI_API_ROOT) {
  throw new Error('Environment variable "VUE_APP_DANDI_API_ROOT" must be set.');
}

// Ensure contains trailing slash
const dandiApiRoot = process.env.VUE_APP_DANDI_API_ROOT.endsWith('/')
  ? process.env.VUE_APP_DANDI_API_ROOT
  : `${process.env.VUE_APP_DANDI_API_ROOT}/`;

const client = axios.create({ baseURL: dandiApiRoot });

let oauthClient: OAuthClient|null = null;
try {
  if (process.env.VUE_APP_OAUTH_API_ROOT && process.env.VUE_APP_OAUTH_CLIENT_ID) {
    oauthClient = new OAuthClient(
      process.env.VUE_APP_OAUTH_API_ROOT,
      process.env.VUE_APP_OAUTH_CLIENT_ID,
    );
  }
} catch (e) {
  oauthClient = null;
}

const dandiRest = new Vue({
  data(): { client: AxiosInstance, user: User | null } {
    return {
      client,
      user: null,
    };
  },
  computed: {
    schemaVersion(): string {
      // Use injected $store instead of importing to
      // avoid dependency cycle
      return this.$store?.direct.getters.dandiset.schemaVersion;
    },
  },
  methods: {
    async restoreLogin() {
      if (!oauthClient) {
        return;
      }
      await oauthClient.maybeRestoreLogin();
      if (!oauthClient.isLoggedIn) {
        return;
      }

      try {
        // Fetch user
        this.user = await this.me();
      } catch (e) {
        // A status of 401 indicates login failed, so the exception should be supressed.
        if (e.response.status === 401) {
          await oauthClient.logout();
        } else {
          // Any other kind of exception indicates an error that shouldn't occur
          throw e;
        }
      }
    },
    async login() {
      if (oauthClient) {
        await oauthClient.redirectToLogin();
      }
    },
    async logout() {
      if (oauthClient) {
        await oauthClient.logout();
        this.user = null;
      }
    },
    async me(): Promise<User> {
      const { data: user } = await client.get('users/me/');
      user.approved = user.status === 'APPROVED';
      return user;
    },
    async newApiKey(): Promise<string> {
      const { data } = await client.post('auth/token/');
      return data;
    },
    async getApiKey(): Promise<string> {
      try {
        const { data } = await client.get('auth/token/');
        return data;
      } catch (e) {
        // If the request returned 404, the user doesn't have an API key yet
        if (e.response.status === 404) {
          // Create a new API key
          const data = await this.newApiKey();
          return data;
        }
        throw e;
      }
    },
    async assets(identifier: string, version: string, config?: AxiosRequestConfig)
      : Promise<Paginated<Asset> | null> {
      try {
        const {
          data,
        } = await client.get(`dandisets/${identifier}/versions/${version}/assets`, config);
        return data;
      } catch (error) {
        if (error.response && error.response.status === 404) {
          return null;
        }
        throw error;
      }
    },
    // eslint-disable-next-line max-len
    async assetPaths(identifier: string, version: string, location: string, page: number, page_size: number):
    Promise<{
      folders: Record<string, AssetFolder>,
      files: Record<string, AssetFile>,
      count: number}
    > {
      const {
        data,
      } = await client.get(`dandisets/${identifier}/versions/${version}/assets/paths/`, {
        params: {
          path_prefix: location,
          page,
          page_size,
        },
      });
      const { count, results } = data;
      const { files, folders } = results;
      return { folders, files, count };
    },
    async versions(identifier: string, params?: any): Promise<Paginated<Version> | null> {
      try {
        const { data } = await client.get(`dandisets/${identifier}/versions/`, { params });
        return data;
      } catch (error) {
        if (error.response && error.response.status === 404) {
          return null;
        }
        if (error.message === 'Network Error') {
          return null;
        }
        throw error;
      }
    },
    async specificVersion(identifier: string, version: string): Promise<Version | null> {
      try {
        const { data } = await client.get(`dandisets/${identifier}/versions/${version}/info/`);
        return data;
      } catch (error) {
        if (error.response && error.response.status === 404) {
          return null;
        }
        throw error;
      }
    },
    async mostRecentVersion(identifier: string) {
      // TODO: find a way to do this with fewer requests
      const count = (await this.versions(identifier))?.count;
      if (!count) {
        return null;
      }
      // Look up the last version using page filters
      const versions = await this.versions(identifier, { page: count, page_size: 1 });
      if (versions === null) {
        return null;
      }
      return versions.results[0];
    },
    async dandisets(params?: any): Promise<AxiosResponse<Paginated<Dandiset>>> {
      const response = await client.get('dandisets/', { params });
      return response;
    },
    async createDandiset(
      name: string, metadata: Partial<DandisetMetadata>, config: AxiosRequestConfig = {},
    ): Promise<AxiosResponse<Dandiset>> {
      const { schemaVersion } = this;
      return client.post('dandisets/', { name, metadata: { name, schemaVersion, ...metadata } }, config);
    },
    async createEmbargoedDandiset(name: string, metadata: Partial<DandisetMetadata>, awardNumber: Organization['awardNumber']) {
      // add NIH award number as a contributor in the new dandiset's metadata
      const award: Organization = {
        name: 'National Institutes of Health (NIH)',
        schemaKey: 'Organization',
        awardNumber,
        roleName: ['dcite:Funder'],
      };
      const contributor: DandisetContributors = [...(metadata.contributor || []), award];

      const params = { embargo: true };

      return this.createDandiset(name, { ...metadata, contributor }, { params });
    },
    async saveDandiset(
      identifier: string, version: string, metadata: any,
    ): Promise<AxiosResponse<Version>> {
      return client.put(`dandisets/${identifier}/versions/${version}/`, {
        name: metadata.name,
        metadata,
      });
    },
    async owners(identifier: string): Promise<AxiosResponse<User[]>> {
      return client.get(`dandisets/${identifier}/users/`);
    },
    async setOwners(identifier: string, owners: User[]) {
      return client.put(`dandisets/${identifier}/users/`, owners);
    },
    async searchUsers(username: string): Promise<User[]> {
      const { data } = await client.get('users/search/', { params: { username } });
      return data;
    },
    async publish(identifier: string): Promise<Version> {
      const { data } = await client.post(`dandisets/${identifier}/versions/draft/publish/`);
      return data;
    },
    async unembargo(identifier: string) {
      // TODO: implement this once the server endpoint is available
      return identifier;
    },
    async info(): Promise<Info> {
      const { data } = await client.get('info/');
      return data;
    },
    async stats() {
      const { data } = await client.get('stats/');
      return data;
    },
    assetManifestURI(identifier: string, version: string) {
      return `${dandiApiRoot}dandisets/${identifier}/versions/${version}/assets/`;
    },
    assetDownloadURI(identifier: string, version: string, uuid: string) {
      return `${dandiApiRoot}assets/${uuid}/download/`;
    },
    assetMetadataURI(identifier: string, version: string, uuid: string) {
      return `${dandiApiRoot}dandisets/${identifier}/versions/${version}/assets/${uuid}`;
    },
    async deleteAsset(identifier: string, version: string, uuid: string): Promise<AxiosResponse> {
      return client.delete(`${dandiApiRoot}dandisets/${identifier}/versions/${version}/assets/${uuid}/`);
    },
  },
});

// This is done with an interceptor because the value of
// oauthClient.authHeaders is initialized asynchronously,
// and doesn't exist at all if the user isn't logged in.
// Using client.defaults.headers.common.Authorization = ...
// would not update when the headers do.
client.interceptors.request.use((config) => ({
  ...config,
  headers: {
    ...oauthClient?.authHeaders,
    ...config.headers,
  },
}));

const user = () => dandiRest.user;
const loggedIn = () => !!user();
const insideIFrame = (): boolean => window.self !== window.top;
const cookiesEnabled = (): boolean => navigator.cookieEnabled;

export {
  dandiRest,
  loggedIn,
  user,
  insideIFrame,
  cookiesEnabled,
};
