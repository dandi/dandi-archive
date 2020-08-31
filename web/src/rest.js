import axios from 'axios';
import { RestClient } from '@girder/components/src';

// Ensure doesn't contain trailing slash
const apiRoot = process.env.VUE_APP_API_ROOT.endsWith('/')
  ? process.env.VUE_APP_API_ROOT.slice(0, -1)
  : process.env.VUE_APP_API_ROOT;

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

const girderRest = new RestClient({ apiRoot, setLocalCookie: true });
const publishRest = axios.create({ baseURL: publishApiRoot });

Object.assign(publishRest, {
  assetDownloadURI(asset) {
    const { uuid, version: { version, dandiset: { identifier } } } = asset;
    const { baseURL } = publishRest.defaults;

    return `${baseURL}dandisets/${identifier}/versions/${version}/assets/${uuid}/download`;
  },
  async assets(identifier, version, config = {}) {
    try {
      const { data } = await publishRest.get(`dandisets/${identifier}/versions/${version}/assets`, config);
      return data;
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return null;
      }
      throw error;
    }
  },
  async versions(identifier) {
    try {
      const { data } = await publishRest.get(`dandisets/${identifier}/versions/`);
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
      const { data } = await publishRest.get(`dandisets/${identifier}/versions/${version}/`);
      return girderize(data);
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return null;
      }
      throw error;
    }
  },
  async mostRecentVersion(identifier) {
    const versions = await publishRest.versions(identifier);
    if (versions === null) {
      return null;
    }
    const { count, results } = versions;
    if (count === 0) {
      return null;
    }
    const { version } = results[0];
    return publishRest.specificVersion(identifier, version);
  },
});

const loggedIn = () => !!girderRest.user;
const user = () => girderRest.user;

export {
  girderRest,
  publishRest,
  loggedIn,
  user,
};
