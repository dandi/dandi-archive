const MomentLocalesPlugin = require('moment-locales-webpack-plugin');
const child_process = require('child_process');

function getVersion() {
  // Try to get the version via `git` if available; otherwise fall back on
  // the COMMIT_REF environment variable provided by Netlify's build
  // environment; if that is missing, report "unknown" as the version.

  try {
    return child_process.execSync('git describe --tags').toString();
  } catch (err) {
    return process.env.COMMIT_REF ? process.env.COMMIT_REF : 'unknown';
  }
}

function getGitRevision() {
  try {
    return child_process.execSync('git rev-parse HEAD').toString();
  } catch (err) {
    return '';
  }
}

process.env.VUE_APP_VERSION = getVersion();
process.env.VUE_APP_GIT_REVISION = getGitRevision();

module.exports = {
  lintOnSave: false,
  transpileDependencies: [
    'vuetify',
    '@koumoul/vjsf',
    '@girder/oauth-client',
  ],
  devServer: {
    // The default port 8080 conflicts with Girder
    port: 8085,
  },
  chainWebpack: (config) => {
    config
      .plugin('moment-locales')
      .use(MomentLocalesPlugin);
  },
};
