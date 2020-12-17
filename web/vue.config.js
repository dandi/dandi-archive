const MomentLocalesPlugin = require('moment-locales-webpack-plugin');

process.env.VUE_APP_VERSION = process.env.COMMIT_REF;

module.exports = {
  lintOnSave: false,
  transpileDependencies: [
    'vuetify',
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
