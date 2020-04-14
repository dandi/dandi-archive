process.env.VUE_APP_VERSION = process.env.COMMIT_REF;

module.exports = {
  lintOnSave: false,
  transpileDependencies: [
    'vuetify',
  ],
};
