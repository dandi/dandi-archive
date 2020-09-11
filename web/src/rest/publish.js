import axios from 'axios';
import Vue from 'vue';
import toggles from '@/featureToggle';

// Ensure contains trailing slash
const publishApiRoot = process.env.VUE_APP_PUBLISH_API_ROOT.endsWith('/')
  ? process.env.VUE_APP_PUBLISH_API_ROOT
  : `${process.env.VUE_APP_PUBLISH_API_ROOT}/`;

function girderize(publishedDandiset) {
  const { // eslint-disable-next-line camelcase
    created, modified, dandi_id, version, metadata, name,
  } = publishedDandiset;
  return {
    created,
    updated: modified,
    version,
    name,
    lowerName: dandi_id,
    meta: {
      dandiset: metadata,
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
        const { data } = await client.get(`api/dandisets/${identifier}/versions/${version}/assets`, config);
        return data;
      } catch (error) {
        if (error.response && error.response.status === 404) {
          return null;
        }
        throw error;
      }
    },
    async assetPaths(identifier, version, location) {
      const { data } = await client.get(`api/dandisets/${identifier}/versions/${version}/assets/paths/`, {
        params: {
          path_prefix: location,
        },
      });
      return data;
    },
    async versions(identifier) {
      try {
        const { data } = await client.get(`api/dandisets/${identifier}/versions/`);
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
        const { data } = await client.get(`api/dandisets/${identifier}/versions/${version}/`);
        return girderize(data);
      } catch (error) {
        if (error.response && error.response.status === 404) {
          return null;
        }
        throw error;
      }
    },
    async mostRecentVersion(identifier) {
      const versions = await this.versions(identifier);
      if (versions === null) {
        return null;
      }
      const { count, results } = versions;
      if (count === 0) {
        return null;
      }
      const { version } = results[0];
      return this.specificVersion(identifier, version);
    },
    assetDownloadURI(asset) {
      const { uuid, version: { version, dandiset: { identifier } } } = asset;
      return `${publishApiRoot}api/dandisets/${identifier}/versions/${version}/assets/${uuid}/download`;
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
  if (toggles.UNIFIED_API) {
    publishRest.token = token;
    publishRest.user = {};
    console.log(`Token set to ${token}`);
  } else {
    console.log('UNIFIED_API is not enabled');
  }
};
