import axios from 'axios';
import Vue from 'vue';
import OAuthClient from '@girder/oauth-client';

// Ensure contains trailing slash
const publishApiRoot = process.env.VUE_APP_PUBLISH_API_ROOT.endsWith('/')
  ? process.env.VUE_APP_PUBLISH_API_ROOT
  : `${process.env.VUE_APP_PUBLISH_API_ROOT}/`;

function girderize(publishedDandiset) {
  const { // eslint-disable-next-line camelcase
    created, modified, dandiset, version, metadata, name, size, asset_count,
  } = publishedDandiset;
  return {
    created,
    updated: modified,
    version,
    name,
    lowerName: name,
    bytes: size,
    items: asset_count,
    meta: {
      dandiset: {
        ...metadata,
        name,
        identifier: dandiset.identifier,
      },
    },
  };
}

const client = axios.create({ baseURL: publishApiRoot });
const oauthClient = new OAuthClient(
  process.env.VUE_APP_OAUTH_API_ROOT,
  process.env.VUE_APP_OAUTH_CLIENT_ID,
);

const publishRest = new Vue({
  data() {
    return {
      client,
      user: null,
    };
  },
  methods: {
    async restoreLogin() {
      await oauthClient.maybeRestoreLogin();
      if (oauthClient.isLoggedIn) {
        this.user = {};
      }
    },
    async login() {
      await oauthClient.redirectToLogin();
    },
    async logout() {
      await oauthClient.logout();
      this.user = null;
    },
    async assets(identifier, version, config = {}) {
      try {
        const {
          data,
        } = await client.get(`api/dandisets/${identifier}/versions/${version}/assets`, config);
        return data;
      } catch (error) {
        if (error.response && error.response.status === 404) {
          return null;
        }
        throw error;
      }
    },
    async assetPaths(identifier, version, location) {
      const {
        data,
      } = await client.get(`dandisets/${identifier}/versions/${version}/assets/paths/`, {
        params: {
          path_prefix: location,
        },
      });
      return data;
    },
    async versions(identifier, params) {
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
    async specificVersion(identifier, version) {
      try {
        const { data } = await client.get(`dandisets/${identifier}/versions/${version}/`);
        return girderize(data);
      } catch (error) {
        if (error.response && error.response.status === 404) {
          return null;
        }
        throw error;
      }
    },
    async mostRecentVersion(identifier) {
      // TODO: find a way to do this with fewer requests
      const count = (await this.versions(identifier))?.count;
      if (!count) {
        return null;
      }
      // Look up the last version using page filters
      const version = (await this.versions(identifier, { page: count, page_size: 1 })).results[0];
      return girderize(version);
    },
    async dandisets(params) {
      return client.get('dandisets/', { params });
    },
    async createDandiset(name, description) {
      const metadata = { name, description };
      return client.post('dandisets/', { name, metadata });
    },
    async owners(identifier) {
      return client.get(`dandisets/${identifier}/users/`);
    },
    async setOwners(identifier, owners) {
      return client.put(`dandisets/${identifier}/users/`, owners);
    },
    async searchUsers(username) {
      const { data } = await client.get('users/search/?', { params: { username } });
      return data;
    },
    async stats() {
      const { data } = await client.get('api/stats/');
      return data;
    },
    assetDownloadURI(asset) {
      const { uuid, version: { version, dandiset: { identifier } } } = asset;
      return `${publishApiRoot}dandisets/${identifier}/versions/${version}/assets/${uuid}/download`;
    },
  },
});

// This is done with an interceptor because the value of
// oauthClient.authHeaders is initialized asynchronously,
// and doesn't exist at all if the user isn't logged in.
// Using client.defaults.headers.common.Authorization = ...
// would not update when the headers do.
client.interceptors.request.use((config) => {
  return {
    ...config,
    headers: {
      ...oauthClient.authHeaders,
      ...config.headers,
    },
  };
});

export default publishRest;
