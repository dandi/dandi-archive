
import axios from 'axios';
import { RestClient } from '@girder/components/src';

const apiRoot = process.env.VUE_APP_API_ROOT || 'http://localhost:8080/api/v1';
const publishApiRoot = process.env.VUE_APP_PUBLISH_API_ROOT;

const girderRest = new RestClient({ apiRoot, setLocalCookie: true });
const publishRest = axios.create({ baseURL: publishApiRoot });

const loggedIn = () => !!girderRest.user;
const user = () => girderRest.user;

export {
  girderRest,
  publishRest,
  loggedIn,
  user,
};
