const MomentLocalesPlugin = require('moment-locales-webpack-plugin');
const child_process = require('child_process');

process.env.VUE_APP_VERSION = child_process.execSync("git describe").toString();

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
