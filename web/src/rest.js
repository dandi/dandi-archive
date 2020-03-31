
import { RestClient } from '@girder/components/src';

const apiRoot = process.env.VUE_APP_API_ROOT || 'http://localhost:8080/api/v1';
const girderRest = new RestClient({ apiRoot, setLocalCookie: true });

const loggedIn = () => !!girderRest.user;
const user = () => girderRest.user;

export {
  loggedIn,
  user,
};
export default girderRest;
