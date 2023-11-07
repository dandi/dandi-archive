module.exports = {
  launch: {
    // only use headless when not debugging
    headless: process.env.DEBUG !== 'true',
  },
  // we don't want the browser to retain any session tokens after reset
  browserContext: 'incognito',
};
