import { RestClient } from '@girder/components/src';

// Ensure doesn't contain trailing slash
const apiRoot = process.env.VUE_APP_API_ROOT.endsWith('/')
  ? process.env.VUE_APP_API_ROOT.slice(0, -1)
  : process.env.VUE_APP_API_ROOT;

const girderRest = new RestClient({ apiRoot, setLocalCookie: true });

export default girderRest;
