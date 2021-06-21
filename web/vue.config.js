const MomentLocalesPlugin = require('moment-locales-webpack-plugin');
const child_process = require('child_process');

function getVersion() {
  try {
    return child_process.execSync("git describe").toString();
  } catch (err) {
    return process.env.COMMIT_REF;
  }
}

function getGitRevision() {
  try {
    return child_process.execSync("git rev-parse HEAD").toString();
  } catch (err) {
    return "";
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
