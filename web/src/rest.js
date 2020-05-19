
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
      const response = await publishRest.get(`dandisets/${identifier}/versions/`);
      return response.data;
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return [];
      }
      throw error;
    }
  },
  async mostRecentVersion(identifier, girderId) {
    try {
      const response = await publishRest.get(`dandisets/${identifier}/`);
      return girderize(response.data, girderId);
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return null;
      }
      throw error;
    }
  },
  async specificVersion(identifier, version, girderId) {
    try {
      const response = await publishRest.get(`dandisets/${identifier}/${version}/`);
      return girderize(response.data, girderId);
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return null;
      }
      throw error;
    }
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
