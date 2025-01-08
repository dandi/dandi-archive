import Vue from 'vue';
import Vuetify from 'vuetify/lib/framework';

import colors from 'vuetify/lib/util/colors';

Vue.use(Vuetify);

export default new Vuetify({
  // Use Girder web components theme
  // https://github.com/girder/girder_web_components/blob/master/src/utils/vuetifyConfig.js
  theme: {
    dark: false,
    options: {
      customProperties: true,
    },
    themes: {
      light: {
        primary: '#950f1a', // colors.lightBlue.darken1,
        secondary: '#f18029', // colors.blueGrey.base,
        accent: '#f5e031', // colors.lightBlue.darken1,
        error: colors.red.base,
        info: colors.lightBlue.lighten1,
        dropzone: colors.grey.lighten3,
        highlight: colors.yellow.lighten4,
      },
      dark: {
        primary: colors.lightBlue.darken3, // TODO - dark theme?
        secondary: colors.grey.base, // TODO - dark theme?
        accent: colors.lightBlue.lighten1, // TODO - dark theme?
        dropzone: colors.grey.darken2,
        highlight: colors.grey.darken2,
      },
    },
  },
  icons: {
    iconfont: 'mdi',
    values: {
      alert: 'mdi-alert-circle',
      bitbucket: 'mdi-bitbucket',
      box_com: 'mdi-package',
      chevron: 'mdi-chevron-right',
      circle: 'mdi-checkbox-blank-circle',
      collection: 'mdi-file-tree',
      download: 'mdi-download',
      edit: 'mdi-pencil',
      externalLink: 'mdi-open-in-new',
      file: 'mdi-file',
      fileMultiple: 'mdi-file-multiple',
      fileNew: 'mdi-file-plus',
      fileUpload: 'mdi-file-upload',
      folder: 'mdi-folder',
      folderNonPublic: 'mdi-folder-key',
      folderNew: 'mdi-folder-plus',
      github: 'mdi-github-circle',
      globe: 'mdi-earth',
      globus: 'mdi-earth',
      google: 'mdi-google',
      group: 'mdi-account-multiple',
      item: 'mdi-file',
      linkedin: 'mdi-linkedin',
      lock: 'mdi-lock',
      login: 'mdi-login',
      logout: 'mdi-logout',
      more: 'mdi-dots-horizontal',
      otp: 'mdi-shield-key',
      preview: 'mdi-file-find',
      search: 'mdi-magnify',
      settings: 'mdi-tune',
      user: 'mdi-account',
      userHome: 'mdi-home-account',
      view: 'mdi-eye',
    },
  },
});
