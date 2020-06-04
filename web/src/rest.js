
import axios from 'axios';
import { RestClient } from '@girder/components/src';

const apiRoot = process.env.VUE_APP_API_ROOT;
const publishApiRoot = process.env.VUE_APP_PUBLISH_API_ROOT;

// TODO remove the girderId if we can eliminate the girder ID from the URL
function girderize(publishedDandiset, girderId) {
  const { // eslint-disable-next-line camelcase
    created, updated, dandi_id, version, metadata,
  } = publishedDandiset;
  return {
    _id: girderId,
    created,
    updated,
    version,
    name: dandi_id,
    lowerName: dandi_id,
    meta: metadata,
  };
}

const girderRest = new RestClient({ apiRoot, setLocalCookie: true });
const publishRest = axios.create({ baseURL: publishApiRoot });

Object.assign(publishRest, {
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
  async specificVersion(identifier, version, girderId) {
    try {
      const { data } = await publishRest.get(`dandisets/${identifier}/versions/${version}/`);
      return girderize(data, girderId);
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return null;
      }
      throw error;
    }
  },
  async mostRecentVersion(identifier, girderId) {
    const versions = await publishRest.versions(identifier);
    if (versions === null) {
      return null;
    }
    const { count, results } = versions;
    if (count === 0) {
      return null;
    }
    const { version } = results[0];
    return publishRest.specificVersion(identifier, version, girderId);
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
