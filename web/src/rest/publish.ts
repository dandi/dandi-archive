import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import Vue from 'vue';
import OAuthClient from '@girder/oauth-client';
import {
  Asset, Dandiset, Paginated, User, Version, Info,
} from '@/types';

// Ensure contains trailing slash
const publishApiRoot = process.env.VUE_APP_PUBLISH_API_ROOT.endsWith('/')
  ? process.env.VUE_APP_PUBLISH_API_ROOT
  : `${process.env.VUE_APP_PUBLISH_API_ROOT}/`;

const client = axios.create({ baseURL: publishApiRoot });
const oauthClient = new OAuthClient(
  process.env.VUE_APP_OAUTH_API_ROOT,
  process.env.VUE_APP_OAUTH_CLIENT_ID,
);

const publishRest = new Vue({
  data(): { client: AxiosInstance, user: User | null } {
    return {
      client,
      user: null,
    };
  },
  methods: {
    async restoreLogin() {
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
      await oauthClient.redirectToLogin();
    },
    async logout() {
      await oauthClient.logout();
      this.user = null;
    },
    async me(): Promise<User> {
      const { data } = await client.get('users/me/');
      return data;
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
    async assetPaths(identifier: string, version: string, location: string): Promise<string[]> {
      const {
        data,
      } = await client.get(`dandisets/${identifier}/versions/${version}/assets/paths/`, {
        params: {
          path_prefix: location,
        },
      });
      return data;
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
    async specificVersion(identifier: string, version: string) {
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
    async createDandiset(name: string, description: string): Promise<AxiosResponse<Dandiset>> {
      const { schema_version } = await this.info();
      const metadata = { name, description, schemaVersion: schema_version };
      return client.post('dandisets/', { name, metadata });
    },
    async saveDandiset(
      identifier: string, version: string, metadata: any,
    ): Promise<AxiosResponse<Dandiset>> {
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
    async info(): Promise<Info> {
      const { data } = await client.get('info/');
      return data;
    },
    async stats() {
      const { data } = await client.get('stats/');
      return data;
    },
    assetDownloadURI(identifier: string, version: string, uuid: string) {
      return `${publishApiRoot}dandisets/${identifier}/versions/${version}/assets/${uuid}/download/`;
    },
    async deleteAsset(identifier: string, version: string, uuid: string): Promise<AxiosResponse> {
      return client.delete(`${publishApiRoot}dandisets/${identifier}/versions/${version}/assets/${uuid}/`);
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
    ...oauthClient.authHeaders,
    ...config.headers,
  },
}));

export default publishRest;
