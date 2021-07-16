import publishRest from '@/rest/publish';

const user = () => publishRest.user;
const loggedIn = () => !!user();
const insideIFrame = () => window.self !== window.top;

export {
  publishRest,
  loggedIn,
  user,
  insideIFrame,
};
