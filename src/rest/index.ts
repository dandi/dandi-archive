import publishRest from '@/rest/publish';

const user = () => publishRest.user;
const loggedIn = () => !!user();
const insideIFrame = (): boolean => window.self !== window.top;
const cookiesEnabled = (): boolean => navigator.cookieEnabled;

export {
  publishRest,
  loggedIn,
  user,
  insideIFrame,
  cookiesEnabled,
};
