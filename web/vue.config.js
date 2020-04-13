process.env.VUE_APP_VERSION = process.env.COMMIT_REF;

module.exports = {
  lintOnSave: false,
  configureWebpack: {
    devtool: 'source-map',
  },
  transpileDependencies: [
    'vuetify',
  ],
  devServer: {
    port: 8085,
  }
};
