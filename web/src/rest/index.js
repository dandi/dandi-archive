import { girderRest } from '@/rest/girder';
import { publishRest } from '@/rest/publish';
import toggles from '@/featureToggle';


const loggedIn = () => ((toggles.UNIFIED_API) ? !!publishRest.user : !!girderRest.user);
const user = () => ((toggles.UNIFIED_API) ? publishRest.user : girderRest.user);

export {
  girderRest,
  publishRest,
  loggedIn,
  user,
};
