import girderRest from '@/rest/girder';
import publishRest from '@/rest/publish';
import toggles from '@/featureToggle';

const user = () => ((toggles.DJANGO_API) ? publishRest.user : girderRest.user);
const loggedIn = () => !!user();
const insideIFrame = () => window.self !== window.top;

export {
  girderRest,
  publishRest,
  loggedIn,
  user,
  insideIFrame,
};
