import axios from 'axios';
import Vue from 'vue';
import toggles from '@/featureToggle';

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

const publishRest = new Vue({
  data() {
    return {
      client,
      token: null,
      user: null,
    };
  },
  methods: {
    // TODO proper OAuth login
    async logout() {
      // TODO proper session logout
      this.token = null;
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
    assetDownloadURI(asset) {
      const { uuid, version: { version, dandiset: { identifier } } } = asset;
      return `${publishApiRoot}dandisets/${identifier}/versions/${version}/assets/${uuid}/download`;
    },
  },
});

// This has to be done with an interceptor because
// the value of publishRest.token changes over time.
// Using client.defaults.headers.common.Authorization = ...
// would not update when the token does.
client.interceptors.request.use((config) => {
  if (!publishRest.token) {
    return config;
  }
  return {
    ...config,
    headers: {
      Authorization: `Token ${publishRest.token}`,
      ...config.headers,
    },
  };
});

export default publishRest;

// This is a hack to allow username/password logins to django
window.setTokenHack = (token) => {
  if (toggles.DJANGO_API) {
    publishRest.token = token;
    publishRest.user = {};
    console.log(`Token set to ${token}`);
  } else {
    console.log('DJANGO_API is not enabled');
  }
};
