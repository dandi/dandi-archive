import girderRest from '@/rest/girder';
import publishRest from '@/rest/publish';

const user = () => publishRest.user;
const loggedIn = () => !!user();
const insideIFrame = () => window.self !== window.top;

export {
  girderRest,
  publishRest,
  loggedIn,
  user,
  insideIFrame,
};
